#!/usr/bin/env python3
import json
import random
import uuid
import time
from pathlib import Path

NUM_POSTS = 10
AVG_TOP_COMMENTS = 8
MAX_DEPTH = 4
MAX_CHILD_PER_NODE = 3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_POSTS = PROJECT_ROOT / "data" / "sample" / "posts.json"
OUTPUT_COMMENTS = PROJECT_ROOT / "data" / "sample" / "comments.json"

POST_TITLES = [
    "Have you seen the new episode? Thoughts?",
    "How do you approach data engineering pipelines?",
    "Ask: best practices for unit testing ETL",
    "Why some shows get canceled too early?",
    "Show-and-tell: my tiny home lab setup",
    "Serious: what will AI do to software jobs?"
]

POST_BODIES = [
    "I was surprised by the character development in that arc.",
    "Short post — just wanted to share that I finished a PoC!",
    "Anyone else think the pacing is off recently?",
    "",
    "[removed]",
    "[deleted]",
    "Here's a small writeup of how I built it: ...",
    "Link post with no selftext."
]

COMMENT_BODIES = [
    "Totally agree!",
    "I disagree — there's nuance here.",
    "[removed]",
    "[deleted]",
    "",
    "This is the part I loved most.",
    "Can you share the config?",
    "Lol, that was unexpected 😂",
    "Downvoted for a reason",
    "Helpful explanation, thanks!"
]

AUTHORS = [
    "user_alpha", "data_enthusiast", "otaku99", "throwaway123",
    "[deleted]", "auto_moderator", "mod_jane"
]

AWARD_TYPES = [
    {"name": "Gold", "id": "award1"},
    {"name": "Silver", "id": "award2"},
    {"name": "Helpful", "id": "award3"}
]

def now_ts():
    return int(time.time())

def rand_past_ts(max_days=30):
    return int(time.time() - random.randint(0, max_days * 24 * 3600))

def rand_id(prefix="", length=6):
    return uuid.uuid4().hex[:length]

def chance(p):
    return random.random() < p

def maybe_drop(data_dict, key, p_drop=0.2):
    if key in data_dict and chance(p_drop):
        del data_dict[key]

def maybe_null(value, p_null=0.15):
    return None if chance(p_null) else value

def random_gildings():
    if chance(0.6):
        return {}
    return {f"gid_{i}": random.randint(0, 3) for i in range(random.randint(0, 2))}

def random_all_awardings():
    out = []
    if chance(0.6):
        return out
    for _ in range(random.randint(0, 3)):
        aw = random.choice(AWARD_TYPES)
        out.append({
            "giver_coin_reward": None,
            "subreddit_id": None,
            "is_new": False,
            "days_of_drip_extension": None,
            "coin_price": random.choice([0, 100, 500]),
            "id": aw["id"],
            "name": aw["name"],
            "award_type": "global",
            "count": random.randint(1, 5)
        })
    return out

def random_preview_image():
    if chance(0.75):
        return None
    return {
        "images": [{
            "source": {"url": "https://i.redd.it/" + rand_id(8) + ".jpg", "width": 1280, "height": 720},
            "resolutions": [],
            "id": rand_id(6)
        }],
        "enabled": True
    }

def random_media():
    if chance(0.8):
        return None
    return {
        "type": random.choice(["youtube.com", "gfycat.com", "reddit_video"]),
        "oembed": {"provider_name": "YouTube", "html": "<iframe...>"},
        "reddit_video": {"fallback_url": "https://v.redd.it/" + rand_id(8) + "/DASH_720.mp4"} if chance(0.3) else None
    }

def random_gallery():
    if chance(0.9):
        return None
    return {
        "items": [{"media_id": rand_id(8), "id": 0}, {"media_id": rand_id(8), "id": 1}],
        "caption": None
    }

def build_post_obj(post_short_id):
    data = {}
    data["id"] = post_short_id
    data["name"] = "t3_" + post_short_id
    data["fullname"] = data["name"]
    data["subreddit"] = random.choice(["anime", "AskReddit", "technology", "dataengineering"])
    data["subreddit_id"] = "t5_" + rand_id(6)
    data["title"] = random.choice(POST_TITLES)
    st = random.choice(POST_BODIES)
    if chance(0.03):
        data["selftext"] = random.randint(0, 100)
    else:
        data["selftext"] = maybe_null(st, p_null=0.12)
    data["author"] = random.choice(AUTHORS)
    data["author_fullname"] = None if data["author"] in ("[deleted]",) else "t2_" + rand_id(6)
    data["created_utc"] = rand_past_ts(60)
    data["created"] = data["created_utc"]
    data["url"] = f"https://www.reddit.com/r/{data['subreddit']}/comments/{post_short_id}"
    data["permalink"] = f"/r/{data['subreddit']}/comments/{post_short_id}/"
    data["num_comments"] = random.randint(0, 50)
    if chance(0.05):
        data["num_comments"] = str(data["num_comments"])
    data["score"] = random.randint(-10, 2000)
    data["ups"] = max(0, int(data["score"] * random.uniform(0.7, 1.0)))
    data["likes"] = random.choice([None, True, False])
    data["over_18"] = chance(0.05)
    data["is_video"] = chance(0.1)
    data["is_self"] = chance(0.6)
    data["spoiler"] = chance(0.03)
    data["locked"] = chance(0.02)
    data["stickied"] = chance(0.03)
    data["distinguished"] = None if chance(0.95) else random.choice(["moderator", "admin"])
    data["edited"] = random.choice([False, rand_past_ts(20)]) if chance(0.1) else False
    data["link_flair_text"] = random.choice([None, "Discussion", "Guide", "Help", "Meta"])
    data["thumbnail"] = random.choice(["", "self", "default", "image", "nsfw"])
    data["preview"] = maybe_null(random_preview_image(), p_null=0.4)
    data["media"] = maybe_null(random_media(), p_null=0.7)
    data["gallery_data"] = maybe_null(random_gallery(), p_null=0.95)
    data["gildings"] = random_gildings()
    data["all_awardings"] = random_all_awardings()
    if chance(0.07):
        data["poll_data"] = {"voting_end_timestamp": rand_past_ts(1), "options": ["Yes", "No"]}
    if chance(0.06):
        data["removed_by_category"] = random.choice([None, "moderator", "admin"])
    if chance(0.05):
        data["banned_by"] = random.choice([None, "autoModerator", "communityMod"])
    data["mod_reports"] = [] if chance(0.85) else [["spam", "modX"]]
    data["user_reports"] = [] if chance(0.9) else [["abusive", 1]]
    for k in ["url", "permalink", "link_flair_text", "thumbnail", "gildings"]:
        if chance(0.08):
            data.pop(k, None)
    if chance(0.02):
        data["raw_popularity"] = str(random.random() * 1000)
    return {"kind": "t3", "data": data}


def build_comment_tree_and_flat(post_short_id):
    flat = []

    def make_comment(parent_id, depth):
        cid = rand_id(6)
        name = "t1_" + cid
        data = {}
        data["id"] = cid
        data["name"] = name
        data["link_id"] = "t3_" + post_short_id
        data["parent_id"] = parent_id
        data["author"] = random.choice(AUTHORS)
        data["author_fullname"] = None if data["author"] in ("[deleted]",) else "t2_" + rand_id(6)
        body = random.choice(COMMENT_BODIES)
        if chance(0.02):
            body = " ".join([random.choice(COMMENT_BODIES + POST_BODIES) for _ in range(random.randint(5, 30))])
        data["body"] = maybe_null(body, p_null=0.08)
        data["created_utc"] = rand_past_ts(60)
        data["score"] = random.randint(-10, 600)
        data["ups"] = max(0, int(data["score"] * random.uniform(0.6, 1.0)))
        data["downs"] = max(0, data["ups"] - data["score"]) if isinstance(data["score"], int) else random.randint(0, 5)
        data["edited"] = random.choice([False, rand_past_ts(10)]) if chance(0.12) else False
        data["gilded"] = random.randint(0, 3)
        data["gildings"] = random_gildings()
        data["distinguished"] = None if chance(0.97) else random.choice(["moderator", "admin"])
        data["controversiality"] = random.choice([0, 1])
        data["collapsed"] = chance(0.05)
        if data["collapsed"]:
            data["collapsed_reason"] = random.choice(["low_score", "report"])
        num_children = 0 if depth >= MAX_DEPTH else random.choices(
            population=[0,1,2,3],
            weights=[0.5,0.25,0.15,0.10],
            k=1
        )[0]
        children_flat = []
        children_embedded = []
        for _ in range(num_children):
            child = make_comment("t1_" + cid, depth + 1)
            children_flat.append(child)
            children_embedded.append(child)

        r = random.random()
        if num_children == 0:
            if chance(0.25):
                data["replies"] = ""
            elif chance(0.05):
                data["replies"] = {"kind": "Listing", "data": {"children": [], "after": None}}
            elif chance(0.02):
                data["replies"] = {"kind": "more", "data": {"children": [rand_id(6) for _ in range(random.randint(1,4))], "count": random.randint(1,10)}}
        else:
            if r < 0.6:
                data["replies"] = {"kind": "Listing", "data": {"children": [{"kind": c["kind"], "data": c["data"]} for c in children_embedded], "after": None}}
            elif r < 0.85:
                data["replies"] = {"kind": "more", "data": {"children": [c["data"]["id"] for c in children_flat], "count": len(children_flat)}}
            else:
                data["replies"] = ""

        if chance(0.1):
            data["mod_reports"] = [["spam", "modX"]]
        if chance(0.07):
            data["user_reports"] = [["off-topic", 1]]
        for k in ["downs", "gilded", "gildings", "distinguished"]:
            if chance(0.06):
                data.pop(k, None)

        obj = {"kind": "t1", "data": data}
        flat.append(obj)
        return obj

    top_n = max(0, int(random.gauss(AVG_TOP_COMMENTS, AVG_TOP_COMMENTS / 2)))
    top_n = min(60, max(0, top_n))
    for _ in range(top_n):
        make_comment("t3_" + post_short_id, depth=0)

    return flat

def main():
    posts_out = []
    comments_out = []

    for _ in range(NUM_POSTS):
        pid = rand_id(6)
        post_obj = build_post_obj(pid)
        posts_out.append(post_obj)

        flat_comments = build_comment_tree_and_flat(pid)
        comments_out.extend(flat_comments)

    random.shuffle(comments_out)

    for post in posts_out:
        if chance(0.07):
            post["data"].pop("permalink", None)
        if chance(0.05):
            post["data"].pop("author_fullname", None)
        if "upvote_ratio" in post["data"] and chance(0.02):
            post["data"]["upvote_ratio"] = str(round(random.uniform(0.3, 1.0), 2))

    for c in comments_out:
        if chance(0.02):
            c["data"]["body"] = None
        if chance(0.01):
            c["data"]["score"] = str(c["data"].get("score", 0))

    OUTPUT_POSTS.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_POSTS, "w", encoding="utf-8") as f:
        json.dump(posts_out, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_COMMENTS, "w", encoding="utf-8") as f:
        json.dump(comments_out, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {OUTPUT_POSTS} ({len(posts_out)} posts) and {OUTPUT_COMMENTS} ({len(comments_out)} comments)")

if __name__ == "__main__":
    main()
