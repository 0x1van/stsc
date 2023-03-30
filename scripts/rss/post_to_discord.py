import os
import discord
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
    current_time = time.mktime(datetime.now().timetuple())
    entries = []

    feed = feedparser.parse(feed_path)
    
    for entry in feed.entries:
        pub_time = time.mktime(entry.published_parsed)
        if current_time - pub_time < 60 * 60 * 24:  # Check if entry is less than an hour old
            entries.append(entry)

    return entries

def read_sent_entries(file_path):
    try:
        with open(file_path, 'r') as f:
            sent_entries = f.read().splitlines()
    except FileNotFoundError:
        sent_entries = []
    return sent_entries

def write_sent_entries(file_path, sent_entries: list):
    with open(file_path, 'a') as f:
        for entry_id in sent_entries:
            f.write(f'{entry_id}\n')

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
    You are an editor of an online magazine featuring fiction and non-fiction.
    You have unique voice and use eloquent language. You write in intoxicating style. You write inebriating prose.
    Use friendly and informal tone. Refer to the author by their name.
    In one-three sentences, write an short review-summary for the following article:

    {text}


    REVIEW-SUMMARY:"""
    return summarize(content, prompt_template=blurb_prompt_template)


async def send_new_entries():
    channel = bot.get_channel(CHANNEL_ID)
    new_entries = get_new_entries(COMBINED_RSS_FEED_PATH)
    sent_entries = read_sent_entries(SENT_ENTRIES_FILE)

    for entry in new_entries:
        entry_id = entry.link

        if entry_id not in sent_entries:
            title = entry.title
            link = entry.link
            author = entry.author if hasattr(entry, 'author') else 'Unknown Author'
            
            article = parse_entry(entry)
            blurb = make_blurb(article['content'])
            
            content = f'**{title}** by {author}\n{link}\n{blurb}'
            sent_entries.append(entry_id)
            await channel.send(content)
            write_sent_entries(SENT_ENTRIES_FILE, sent_entries)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await send_new_entries()
    await bot.close()

bot.run(TOKEN)