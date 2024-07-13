#! /usr/bin/env python3

import os
import argparse
import json
import time
import feedparser
import requests
import re
import logging

from bs4 import BeautifulSoup
from mastodon import Mastodon

dry_run = False
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="This script fetches RSS feed and pushes posts to Mastodon instance")
    parser.add_argument("feed_url", help="URL of the feed to fetch")
    parser.add_argument("--state-file", help="file to store state", default="state.json")
    parser.add_argument("--max-posts", help="maximum number of posts to push", type=int, default=10)
    parser.add_argument("--post-template", help="Template of the post", default="{title}\n\n{link}")
    parser.add_argument("--post-hashtags", help="Hashtags to add to the post", default="")
    parser.add_argument("--post-max-length", help="Maximum length of the post", type=int, default=499)
    parser.add_argument("--post-max-images", help="Maximum number of images to attach to the post", type=int, default=4)
    parser.add_argument("--post-visibility", help="Visibility of the post in Mastodon", default="public", choices=["public", "unlisted", "private", "direct"])
    parser.add_argument("--mastodon-api-base-url", help="Mastodon API base URL", default=os.environ.get('MASTODON_API_BASE_URL', 'https://mastodon.social'))
    parser.add_argument("--dry-run", help="do not push to Mastodon", action="store_true")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")

    args = parser.parse_args()

    if len(args.post_hashtags) > args.post_max_length - 2:
        logger.error("Post hashtags are longer than post max length")
        return
    
    if args.post_max_images > 4:
        logger.error("Post max images should be no more than 4")
        return
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(stream=os.sys.stdout))

    if args.dry_run:
        global dry_run
        dry_run = True
        logger.info("Dry-run mode enabled")

    # If state file exists, read it
    try:
        logger.debug("Reading state file")
        with open(args.state_file, "r") as f:
            state = json.load(f)
        state["last_date"] = time.struct_time(state["last_date"])
        logger.debug("Last date: " + time.asctime(state["last_date"]))
    except FileNotFoundError:
        logger.debug("State file not found, initializing state from scratch")
        state = {
            "last_date": time.gmtime(0)
        }
    except Exception as e:
        logger.error("Failed to read state file: " + str(e))
        raise e
    
    # Fetch feed
    logger.debug("Fetching feed from: " + args.feed_url)
    response = requests.get(args.feed_url)
    if response.status_code != 200:
        logger.error("Failed to fetch feed: " + str(response.status_code))
        return 1
    feed = feedparser.parse(response.content)["entries"]
    logger.debug("Posts in feed: " + str(len(feed)))

    # Filter posts by date
    now = time.gmtime()
    feed = [post for post in feed if post.published_parsed < now]
    feed = [post for post in feed if post.published_parsed > state["last_date"]]
    logger.debug("Posts available: " + str(len(feed)))

    # Sort posts by date
    feed.sort(key=lambda x: x.published_parsed)

    # Limit number of posts
    feed = feed[:args.max_posts]
    logger.debug("Posts to push: " + str(len(feed)))
    
    # Push to Mastodon
    try:
        for post in feed:
            post_to_mastodon(post, args)
            state["last_date"] = post.published_parsed
    except Exception as e:
        logger.error("Failed to push to Mastodon: " + str(e))
    finally:
        if not dry_run:
            save_state(state, args)

def post_to_mastodon(post, args):
    global dry_run

    # Initialize Mastodon API
    if not dry_run:
        logger.debug("Initializing Mastodon API")
        mastodon = Mastodon(
            api_base_url=args.mastodon_api_base_url,
            client_id=os.environ['MASTODON_CLIENT_ID'],
            client_secret=os.environ['MASTODON_CLIENT_SECRET'],
            access_token=os.environ['MASTODON_ACCESS_TOKEN']
        )
        logger.debug("Mastodon API initialized")
    else:
        mastodon = None
        logger.debug("Dry-run mode, skipping Mastodon API initialization")

    status = compose_status(post, args.post_template, args.post_max_length, args.post_hashtags)
    logger.debug("Posting to Mastodon: " + status)

    media_ids = []

    # Fetch images (up to 4)
    image_hrefs = [l['href'] for l in post['links']
              if (l['rel'] == 'enclosure') and ('image' in l['type'])][:args.post_max_images]
    logger.debug("Images to upload: " + str(len(image_hrefs)))

    for href in image_hrefs:
        media = upload_image_to_mastodon(href, mastodon)
        if media != None:
            media_ids.append(media['id'])
    logger.debug("Media IDs: " + str(media_ids))

    if not dry_run:
        logger.debug("Posting to Mastodon")
        status = mastodon.status_post(
            status=status,
            visibility=args.post_visibility,
            media_ids=media_ids,
            language="ru"
        )
        logger.debug("Posted to Mastodon: id={0}, url={1}".format(status['id'], status['url']))

def upload_image_to_mastodon(image_url, mastodon):
    global dry_run

    if dry_run:
        return None

    logger.debug("Uploading image: " + image_url)
    image_response = requests.get(image_url)
    media = mastodon.media_post(image_response.content, mime_type=image_response.headers['Content-Type'])
    logger.debug("Image uploaded: id={0}, url={1}".format(media['id'], media['url']))

    return media

def compose_status(post, template, max_length, hashtags):
    title = cleanup_text(post["title"])
    summary = cleanup_html(post["summary"])
    content = "\n\n".join([cleanup_html(c["value"]) for c in post["content"] if c["type"] == "text/html"])
    link = post["link"]
    
    text = template.format(title=title, summary=summary, content=content, link=link)
    text = text[:max_length - len(hashtags) - 2]
    return text + "\n\n" + hashtags

def cleanup_text(text):
    text = re.sub('\xa0+', ' ', text)
    text = re.sub('  +', ' ', text)
    text = re.sub(' +\n', '\n', text)
    text = re.sub('\n\n\n+', '\n\n', text, flags=re.M)
    return text.strip()

def cleanup_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    return cleanup_text(text)

def save_state(state, args):
    logger.debug("Saving state")
    try:
        with open(args.state_file, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error("Failed to save state: " + str(e))
        raise e

if __name__ == "__main__":
    main()
