import json
import feedparser
import pandas as pd
import xml.etree.ElementTree as ET
import html2text
import requests 

from datetime import datetime, timedelta
from newspaper import Article
import time
import pytz



def read_rss_urls_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        rss_urls = json.load(f)
    return rss_urls


def combine_feeds(feed_urls):
    xmlns_content = 'http://purl.org/rss/1.0/modules/content/'
    combined_feed = ET.Element('rss', {'version': '2.0', f'xmlns:content': xmlns_content})
    channel = ET.SubElement(combined_feed, 'channel')
    ET.SubElement(channel, 'title').text = 'Combined RSS Feed'
    ET.SubElement(channel, 'link').text = 'https://yourwebsite.com'
    ET.SubElement(channel, 'description').text = 'A combined RSS feed from multiple sources'
    ET.SubElement(channel, 'lastBuildDate').text = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = entry.title
            ET.SubElement(item, 'link').text = entry.link
            ET.SubElement(item, 'description').text = entry.description
            ET.SubElement(item, 'pubDate').text = entry.published

            # Extract author information
            author = entry.author if hasattr(entry, 'author') else None
            if author:
                ET.SubElement(item, 'author').text = author

            # Extract content from 'content' attribute or fallback to 'summary' attribute
            content = entry.content[0].value if hasattr(entry, 'content') else entry.summary
            ET.SubElement(item, f'{{{xmlns_content}}}encoded').text = content

    return ET.tostring(combined_feed, encoding='utf-8', method='xml')


def main():
    rss_list_file = 'rss-list.json'
    combined_rss_feed_file = 'combined_rss_feed.xml'

    rss_urls = read_rss_urls_from_json(rss_list_file)
    combined_rss = combine_feeds(rss_urls)

    with open(combined_rss_feed_file, 'wb') as f:
        f.write(combined_rss)

if __name__ == '__main__':
    main()
