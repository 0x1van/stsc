import os
import discord
from discord.ext import commands

import feedparser
import time
from datetime import datetime, timedelta

# Load environment variables

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
COMBINED_RSS_FEED_PATH = 'combined_rss_feed.xml'
SENT_ENTRIES_FILE = 'sent_entries.txt'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

def write_sent_entries(file_path, entry_id):
    with open(file_path, 'a') as f:
        f.write(f'{entry_id}\n')

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
            content = f'**{title}** by {author}\n{link}'
            await channel.send(content)
            write_sent_entries(SENT_ENTRIES_FILE, entry_id)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await send_new_entries()
    await bot.close()

bot.run(TOKEN)