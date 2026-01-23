#!/usr/bin/env python3
# generate_reddit_data_v3.py
# Generates two files:
#  - posts_v3.json  -> list of submission-like objects (kind=t3, data={...})
#  - comments_v3.json -> flat list of comment-like objects (kind=t1, data={...})
#
# The generator purposely:
#  - includes many real-ish Reddit API fields,
#  - sometimes omits fields entirely,
#  - sometimes sets fields to null / empty string / unexpected types,
#  - creates nested replies; replies can be "" (string), a Listing object,
#    or contain "more" placeholder nodes,
#  - includes "rare" fields: poll_data, gallery_data, media, gildings, all_awardings, distinguished, etc.
#
# Usage:
#   python generate_reddit_data_v3.py
#
import json
import random
import uuid
import time
from datetime import timedelta

# ---------- CONFIG ----------
NUM_POSTS = 10
AVG_TOP_COMMENTS = 8
MAX_DEPTH = 4
MAX_CHILD_PER_NODE = 3

OUTPUT_POSTS = "posts_v3.json"
OUTPUT_COMMENTS = "comments_v3.json"

# ---------- English pools ----------
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

# ---------- helpers ----------
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
    # return a dict like {"gid_1": 1, "gid_2": 0}
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

# ---------- generator core ----------
def build_post_obj(post_short_id):
    """Return structure similar to Reddit submission listing: {'kind':'t3', 'data': {...}}"""
    data = {}
    # core ids
    data["id"] = post_short_id
    data["name"] = "t3_" + post_short_id
    data["fullname"] = data["name"]  # sometimes present in dumps
    # text / meta
    data["subreddit"] = random.choice(["anime", "AskReddit", "technology", "dataengineering"])
    data["subreddit_id"] = "t5_" + rand_id(6)
    data["title"] = random.choice(POST_TITLES)
    # selftext sometimes missing / null / text
    st = random.choice(POST_BODIES)
    # introduce weird type occasionally
    if chance(0.03):
        # type mismatch: number instead of string
        data["selftext"] = random.randint(0, 100)
    else:
        data["selftext"] = maybe_null(st, p_null=0.12)
    data["author"] = random.choice(AUTHORS)
    data["author_fullname"] = None if data["author"] in ("[deleted]",) else "t2_" + rand_id(6)
    data["created_utc"] = rand_past_ts(60)
    data["created"] = data["created_utc"]  # alternate name
    data["url"] = f"https://www.reddit.com/r/{data['subreddit']}/comments/{post_short_id}"
    data["permalink"] = f"/r/{data['subreddit']}/comments/{post_short_id}/"
    # numeric / booleans
    data["num_comments"] = random.randint(0, 50)
    # sometimes num_comments is a string (type noise)
    if chance(0.05):
        data["num_comments"] = str(data["num_comments"])
    data["score"] = random.randint(-10, 2000)
    data["ups"] = max(0, int(data["score"] * random.uniform(0.7, 1.0)))
    # likes is often null in API (depends on user), sometimes True/False
    data["likes"] = random.choice([None, True, False])
    data["over_18"] = chance(0.05)
    data["is_video"] = chance(0.1)
    data["is_self"] = chance(0.6)
    data["spoiler"] = chance(0.03)
    data["locked"] = chance(0.02)
    data["stickied"] = chance(0.03)
    data["distinguished"] = None if chance(0.95) else random.choice(["moderator", "admin"])
    # edited: False or timestamp
    data["edited"] = random.choice([False, rand_past_ts(20)]) if chance(0.1) else False
    # flair / thumbnail / preview / media
    data["link_flair_text"] = random.choice([None, "Discussion", "Guide", "Help", "Meta"])
    data["thumbnail"] = random.choice(["", "self", "default", "image", "nsfw"])
    data["preview"] = maybe_null(random_preview_image(), p_null=0.4)
    data["media"] = maybe_null(random_media(), p_null=0.7)
    data["gallery_data"] = maybe_null(random_gallery(), p_null=0.95)
    # awards
    data["gildings"] = random_gildings()
    data["all_awardings"] = random_all_awardings()
    # rarer fields
    if chance(0.07):
        data["poll_data"] = {"voting_end_timestamp": rand_past_ts(1), "options": ["Yes", "No"]}
    # moderation / removal / reports noise
    if chance(0.06):
        data["removed_by_category"] = random.choice([None, "moderator", "admin"])
    if chance(0.05):
        data["banned_by"] = random.choice([None, "autoModerator", "communityMod"])
    data["mod_reports"] = [] if chance(0.85) else [["spam", "modX"]]
    data["user_reports"] = [] if chance(0.9) else [["abusive", 1]]
    # sometimes omit some typical fields to simulate missing-key noise
    for k in ["url", "permalink", "link_flair_text", "thumbnail", "gildings"]:
        if chance(0.08):
            data.pop(k, None)
    # occasionally add raw_popularity as a string -> type noise
    if chance(0.02):
        data["raw_popularity"] = str(random.random() * 1000)
    return {"kind": "t3", "data": data}


# We'll build a flat comment list and also (optionally) embed replies in some parents
def build_comment_tree_and_flat(post_short_id):
    """
    Returns (flat_comments_list)
    flat_comments_list: list of comment objects {'kind':'t1','data':{...}}
    """
    flat = []

    def make_comment(parent_id, depth):
        cid = rand_id(6)
        name = "t1_" + cid
        data = {}
        data["id"] = cid
        data["name"] = name
        data["link_id"] = "t3_" + post_short_id
        data["parent_id"] = parent_id  # either t3_<post> or t1_<something>
        data["author"] = random.choice(AUTHORS)
        data["author_fullname"] = None if data["author"] in ("[deleted]",) else "t2_" + rand_id(6)
        # body noise: text / removed / deleted / empty / sometimes long
        body = random.choice(COMMENT_BODIES)
        if chance(0.02):
            # very long body
            body = " ".join([random.choice(COMMENT_BODIES + POST_BODIES) for _ in range(random.randint(5, 30))])
        data["body"] = maybe_null(body, p_null=0.08)
        data["created_utc"] = rand_past_ts(60)
        data["score"] = random.randint(-10, 600)
        data["ups"] = max(0, int(data["score"] * random.uniform(0.6, 1.0)))
        data["downs"] = max(0, data["ups"] - data["score"]) if isinstance(data["score"], int) else random.randint(0, 5)
        # edited can be false / timestamp
        data["edited"] = random.choice([False, rand_past_ts(10)]) if chance(0.12) else False
        data["gilded"] = random.randint(0, 3)
        data["gildings"] = random_gildings()
        data["distinguished"] = None if chance(0.97) else random.choice(["moderator", "admin"])
        data["controversiality"] = random.choice([0, 1])
        data["collapsed"] = chance(0.05)
        if data["collapsed"]:
            data["collapsed_reason"] = random.choice(["low_score", "report"])
        # replies: sometimes "", sometimes Listing with embedded child comment objects, sometimes omitted
        # decide number of children
        num_children = 0 if depth >= MAX_DEPTH else random.choices(
            population=[0,1,2,3],
            weights=[0.5,0.25,0.15,0.10],
            k=1
        )[0]
        children_flat = []
        children_embedded = []
        for _ in range(num_children):
            child = make_comment("t1_" + cid, depth + 1)
            # child is appended to flat in recursive call already
            children_flat.append(child)
            # store the entire child object (so it has both 'kind' and 'data')
            children_embedded.append(child)

        # decide how to populate replies field
        r = random.random()
        if num_children == 0:
            # sometimes replies is "", sometimes missing, sometimes a small listing with 'more' placeholder
            if chance(0.25):
                data["replies"] = ""
            elif chance(0.05):
                data["replies"] = {"kind": "Listing", "data": {"children": [], "after": None}}
            elif chance(0.02):
                # 'more' node (placeholder that tells to fetch more children)
                data["replies"] = {"kind": "more", "data": {"children": [rand_id(6) for _ in range(random.randint(1,4))], "count": random.randint(1,10)}}
            # else omit replies key entirely
        else:
            # there are children: sometimes embed them, sometimes set replies to string, sometimes include 'more'
            if r < 0.6:
                # embed children as a Listing (realistic)
                data["replies"] = {"kind": "Listing", "data": {"children": [{"kind": c["kind"], "data": c["data"]} for c in children_embedded], "after": None}}
            elif r < 0.85:
                # put a 'more' placeholder (child ids only)
                data["replies"] = {"kind": "more", "data": {"children": [c["data"]["id"] for c in children_flat], "count": len(children_flat)}}
            else:
                # set replies to empty string (data absent / collapsed)
                data["replies"] = ""

        # mod/user reports sometimes present as lists (or sometimes missing)
        if chance(0.1):
            data["mod_reports"] = [["spam", "modX"]]
        if chance(0.07):
            data["user_reports"] = [["off-topic", 1]]
        # sometimes fields are entirely missing
        for k in ["downs", "gilded", "gildings", "distinguished"]:
            if chance(0.06):
                data.pop(k, None)

        obj = {"kind": "t1", "data": data}
        # append this comment to flat list (children were already appended in recursion)
        flat.append(obj)
        # return the created object (so parent can embed its data)
        return obj

    # create a bunch of top-level comments for this post
    top_n = max(0, int(random.gauss(AVG_TOP_COMMENTS, AVG_TOP_COMMENTS / 2)))
    top_n = min(60, max(0, top_n))
    for _ in range(top_n):
        make_comment("t3_" + post_short_id, depth=0)

    return flat

# ---------- main ----------
def main():
    posts_out = []
    comments_out = []

    for _ in range(NUM_POSTS):
        pid = rand_id(6)
        post_obj = build_post_obj(pid)
        posts_out.append(post_obj)

        # create comment forest for this post
        flat_comments = build_comment_tree_and_flat(pid)
        # flatten returned comments are appended into internal 'flat' list
        comments_out.extend(flat_comments)

    # Shuffle comments to simulate unordered dumps
    random.shuffle(comments_out)

    # Introduce some global noise across posts/comments:
    # - remove random fields from random posts
    for post in posts_out:
        if chance(0.07):
            # remove permalink sometimes
            post["data"].pop("permalink", None)
        if chance(0.05):
            post["data"].pop("author_fullname", None)
        # sometimes change type of upvote_ratio to string
        if "upvote_ratio" in post["data"] and chance(0.02):
            post["data"]["upvote_ratio"] = str(round(random.uniform(0.3, 1.0), 2))

    # For comments, sometimes remove body or set odd types
    for c in comments_out:
        if chance(0.02):
            c["data"]["body"] = None
        if chance(0.01):
            c["data"]["score"] = str(c["data"].get("score", 0))

    # Write out
    with open(OUTPUT_POSTS, "w", encoding="utf-8") as f:
        json.dump(posts_out, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_COMMENTS, "w", encoding="utf-8") as f:
        json.dump(comments_out, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {OUTPUT_POSTS} ({len(posts_out)} posts) and {OUTPUT_COMMENTS} ({len(comments_out)} comments)")

if __name__ == "__main__":
    main()
