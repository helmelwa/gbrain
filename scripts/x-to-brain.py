#!/usr/bin/env python3
"""Convert xurl JSON output to GBrain-compatible markdown."""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

def convert_tweet(tweet: dict, output_dir: Path) -> None:
    """Convert a single tweet to markdown and write to file."""

    tweet_id = tweet.get("id", "unknown")
    text = tweet.get("text", "")

    # Parse timestamp
    created_at = tweet.get("created_at", "")
    if created_at:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M:%S %Z")
    else:
        date_str = "unknown-date"
        time_str = ""

    # Extract author
    author = "unknown"
    if "author_id" in tweet:
        author = tweet["author_id"]
    elif "includes" in tweet and "users" in tweet["includes"]:
        for user in tweet["includes"]["users"]:
            if user.get("id") == tweet.get("author_id"):
                author = f"@{user.get('username', 'unknown')}"
                break

    # Extract metrics
    metrics = tweet.get("public_metrics", {})
    likes = metrics.get("like_count", 0)
    retweets = metrics.get("retweet_count", 0)
    replies = metrics.get("reply_count", 0)

    # Build filename
    safe_text = text[:50].replace("/", "-").replace(" ", "-").replace("\n", "")[:50]
    filename = f"{date_str}_{tweet_id}_{safe_text}.md"
    filepath = output_dir / filename

    # Build markdown
    md_content = f"""---
type: tweet
tweet_id: "{tweet_id}"
date: {date_str}
author: {author}
likes: {likes}
retweets: {retweets}
replies: {replies}
---

# Tweet by {author} — {date_str}

>{text}

**Likes:** {likes} | **Retweets:** {retweets} | **Replies:** {replies}
**Time:** {time_str}
**Link:** https://x.com/i/web/status/{tweet_id}

---
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Created: {filename}")

def main():
    if len(sys.argv) < 3:
        print("Usage: x-to-brain.py <input.json> <output_dir>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both single tweet and search response formats
    if "data" in data:
        tweets = data["data"]
    elif isinstance(data, list):
        tweets = data
    else:
        tweets = [data]

    for tweet in tweets:
        try:
            convert_tweet(tweet, output_dir)
        except Exception as e:
            print(f"Error processing tweet {tweet.get('id', 'unknown')}: {e}")

    print(f"\nConverted {len(tweets)} tweets to {output_dir}")

if __name__ == "__main__":
    main()
