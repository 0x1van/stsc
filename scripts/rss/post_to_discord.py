import os
import discord
import pandas as pd
from discord.ext import commands
from newspaper import Article
import feedparser
import time
from datetime import datetime, timedelta

from langchain import OpenAI, PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI

# Load environment variables

TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI = os.getenv('OPENAI')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
COMBINED_RSS_FEED_PATH = 'combined_rss_feed.xml'
SENT_ENTRIES_FILE = 'sent_entries.txt'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
llm = ChatOpenAI(
  openai_api_key=OPENAI, model_name='gpt-3.5-turbo'
)

# Parse the combined RSS feed
def get_new_entries(feed_path):
    """Get new entries from RSS feed. Returns a list of feedparser entries."""
    current_time = time.mktime(datetime.now().timetuple())
    entries = []

    feed = feedparser.parse(feed_path)
    
    for entry in feed.entries:
        pub_time = time.mktime(entry.published_parsed)
        if current_time - pub_time < 60 * 60 * 24:  # Check if entry is less than an hour old
            entries.append(entry)

    return entries

def read_sent_entries(file_path):
    """"""
    try:
        sent_entries = pd.read_csv(file_path).drop_duplicates(['link'])
    except FileNotFoundError:
        sent_entries = pd.DataFrame(columns=['link', 'sent_time', 'title', 'author'])
    return sent_entries

def write_sent_entries(file_path, sent_entries: pd.DataFrame):
    sent_entries.to_csv(file_path, index=False)

def parse_entry(entry, retries=3, delay=5):
    title = entry.title
    link = entry.link
    author = entry.author if hasattr(entry, 'author') else 'Unknown Author'

    # Use newspaper package to parse article text with retries and delay
    content = None
    for attempt in range(retries):
        try:
            article = Article(link)
            article.download()
            article.parse()
            content = article.text
            break
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                print(f"Failed to download article '{title}' after {retries} retries. Error: {e}")

    article = {
        'title': title,
        'author': author,
        'link': link,
        'content': f'Author: {author} \n\n Content: {content}'
    }

    return article

def summarize(content, prompt_template):
    text_splitter = CharacterTextSplitter()
    texts = text_splitter.split_text(content)
    docs = [Document(page_content=t) for t in texts[:3]]

    PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=PROMPT)
    summary = chain.run(docs)
    return summary


def make_blurb(content):
    blurb_prompt_template = """
    You are an editor of an online magazine called The Soaring Twenties Social Club featuring fiction and non-fiction.
    
    You have unique and eloquent voice. 
    You should sound very British. Be casual and friendly.
    Don't use marketing jargon like "must-read" or "best-selling" and others.
    Refer to the author by their name like you're friends.
    
    You are writing a blurb for an article. You want to make it sound interesting, witty and inviting.
    You have 280 characters to write a blurb. You can use the following article as a reference:

    {text}

    BLURB:"""
    return summarize(content, prompt_template=blurb_prompt_template)


async def send_new_entries():
    channel = bot.get_channel(CHANNEL_ID)
    new_entries = get_new_entries(COMBINED_RSS_FEED_PATH)
    sent_entries = read_sent_entries(SENT_ENTRIES_FILE)

    for entry in new_entries:
        entry_id = entry.link

        if entry_id not in sent_entries.link.values:
            title = entry.title
            link = entry.link
            author = entry.author if hasattr(entry, 'author') else 'Unknown Author'
            article = parse_entry(entry)
            blurb = make_blurb(article['content'])
            
            content = f'**{title}** by {author}\n{link}\n{blurb}'
            entry_dict = {'link': entry_id, 'sent_time': datetime.now(), 'title': title, 'author': author}
            sent_entries = sent_entries.append(entry_dict, ignore_index=True)
            await channel.send(content)
            write_sent_entries(SENT_ENTRIES_FILE, sent_entries)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await send_new_entries()
    await bot.close()

bot.run(TOKEN)