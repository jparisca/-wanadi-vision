import requests
import time
import sys
import os

# Agregamos el directorio raíz al path para que los imports funcionen correctamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from refinery.cleaner import PromptRefinery
from database.db_utils import save_prompt_to_db

REDDIT_USER_AGENT = "NexusPromptScraper/0.1 (by /u/nexus_builder)"
SUBREDDITS = ["midjourney", "stablediffusion", "fluxai"]
DELAY_SECONDS = 2

def fetch_reddit_posts(subreddit, limit=25):
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    headers = {"User-Agent": REDDIT_USER_AGENT}
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        posts = data["data"]["children"]
        return posts
    except Exception as e:
        print(f"❌ Error fetching r/{subreddit}: {e}")
        return []

def extract_text_from_post(post):
    """Devuelve el título + selftext (si existe) como candidato a prompt."""
    data = post["data"]
    title = data.get("title", "")
    selftext = data.get("selftext", "")
    full_text = f"{title}\n{selftext}".strip()
    return full_text, title, selftext

def process_reddit_post(post, refinery, subreddit):
    full_text, title, selftext = extract_text_from_post(post)
    if not full_text:
        return None
    
    result = refinery.process(full_text)
    
    if len(result["clean_text"]) < 10:
        print(f"⏭️  Descartado (texto muy corto): {title[:50]}")
        return None
    
    post_id = post["data"]["id"]
    url = f"https://reddit.com/r/{subreddit}/comments/{post_id}"
    author = post["data"].get("author", "[deleted]")
    engagement = post["data"].get("ups", 0)
    
    save_prompt_to_db(
        refinery_result=result,
        platform="Reddit",
        url=url,
        author=author,
        engagement_score=float(engagement)
    )
    return result

def main():
    refinery = PromptRefinery()
    for sub in SUBREDDITS:
        print(f"\n🔍 Escaneando r/{sub} ...")
        posts = fetch_reddit_posts(sub, limit=25)
        print(f"   Encontrados {len(posts)} posts.")
        for post in posts:
            process_reddit_post(post, refinery, sub)
            time.sleep(DELAY_SECONDS)

if __name__ == "__main__":
    main()
