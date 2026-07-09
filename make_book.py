"""
make_book.py — combined pipeline

Runs all three steps in order:
  1. generate_story()   -> asks Claude for the story as JSON
  2. generate_images()  -> asks Pollinations.ai OR Gemini for one image per page
  3. build_html()        -> assembles everything into storybook.html

This file doesn't introduce new logic — it's story.py + illustrate.py +
build_book.py, with the __main__ blocks merged into one flow so the whole
book can be made with a single command: `py make_book.py`
"""

import os
import re
import json
import time
import base64
import requests
from datetime import datetime
from urllib.parse import quote
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

FIXED_SEED = 42
BASE_STORIES_DIR = "stories"


# ---------------------------------------------------------------------------
# Folder naming: stories/<date>_<run-number>_<character-names>/
# ---------------------------------------------------------------------------
def sanitize_for_filename(text):
    """Turn a string into something safe to use in a folder/file name.
    Removes punctuation, replaces spaces with hyphens."""
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text)   # drop anything that isn't a letter/number/space/hyphen
    text = re.sub(r"\s+", "-", text)       # collapse spaces into hyphens
    return text


def get_next_run_number(date_str):
    """Look inside stories/ for folders already starting with today's date,
    and return the next number in sequence (e.g. if 01 and 02 exist, return 03)."""
    if not os.path.exists(BASE_STORIES_DIR):
        return 1

    todays_folders = [d for d in os.listdir(BASE_STORIES_DIR) if d.startswith(date_str)]
    if not todays_folders:
        return 1

    numbers_found = []
    for folder_name in todays_folders:
        parts = folder_name.split("_")
        if len(parts) >= 2 and parts[1].isdigit():
            numbers_found.append(int(parts[1]))

    return max(numbers_found, default=0) + 1


def build_story_folder_name(story):
    date_str = datetime.now().strftime("%Y-%m-%d")
    run_number = get_next_run_number(date_str)
    character_names = "-".join(
        sanitize_for_filename(c["name"]) for c in story["characters"]
    )
    return f"{date_str}_{run_number:02d}_{character_names}"


# ---------------------------------------------------------------------------
# STEP 1: Story generation  (from story.py)
# ---------------------------------------------------------------------------
def generate_story(characters, num_pages=6):
    prompt = f"""Write a warm, gentle bedtime story for 5-6 year old children, featuring: {characters}.

WRITING STYLE:
- Write like a parent telling the story out loud, not like a formal book
- Use short, simple sentences and easy words a 5-6 year old understands
- Use warmth, gentle humor, and soft repetition (bedtime stories often repeat sweet little phrases)
- Avoid fancy or poetic vocabulary - keep it simple and cozy

Split the story into exactly {num_pages} pages, 2-3 short sentences per page.

IMPORTANT: If any character speaks, use single quotes for their dialogue (like 'Goodnight, Coco'), never double quotes, since double quotes inside the JSON text will break the file format.

Also create a FIXED visual description for each character (hair, clothes, colors, size) that will be reused on every page so the character looks the same throughout the book. Be specific and concrete.

Also include a soft, one-line closing message or gentle moral from the story - simple enough for a 5-6 year old, warm and comforting, not preachy or instructional. It should feel like a soft whisper at the end of the story, not a lesson.

Respond ONLY with valid JSON in this exact format, no other text:
{{
  "title": "story title here",
  "characters": [
    {{"name": "character name", "visual_description": "detailed fixed appearance: hair, clothing, colors, size"}}
  ],
  "pages": [
    {{"text": "...", "scene_description": "what is physically happening in this scene, no character appearance details"}}
  ],
  "moral": "a soft one-line closing message"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.content[0].text

    print("--- RAW RESPONSE ---")
    print(raw_text)
    print("--- END RAW RESPONSE ---\n")

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    story = json.loads(cleaned)
    return story


# ---------------------------------------------------------------------------
# STEP 2: Illustration  (from illustrate.py) — Pollinations backend
# ---------------------------------------------------------------------------
def build_full_prompt(story, page):
    character_block = ". ".join(
        f"{c['name']}: {c['visual_description']}" for c in story['characters']
    )
    scene = page['scene_description']
    return (
        f"{character_block}. Scene: {scene}. "
        f"children's storybook illustration, watercolor style, warm colors, "
        f"consistent character design"
    )


def generate_images(story, max_retries=3):
    for i, page in enumerate(story['pages'], 1):
        filename = f"page_{i}.png"

        if os.path.exists(filename):
            print(f"Page {i} already exists, skipping.")
            continue

        full_prompt = build_full_prompt(story, page)
        encoded_prompt = quote(full_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=768&height=512&nologo=true&seed={FIXED_SEED}&model=flux"
        )

        for attempt in range(1, max_retries + 1):
            print(f"Generating image for page {i} (attempt {attempt})...")
            response = requests.get(url, timeout=60)

            if response.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"  Saved {filename}")
                break
            else:
                print(f"  Failed: status {response.status_code}")
                if attempt < max_retries:
                    print("  Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"  Giving up on page {i} after {max_retries} attempts.")


# ---------------------------------------------------------------------------
# STEP 3: HTML assembly  (from build_book.py) — Pollinations backend
# ---------------------------------------------------------------------------
def image_to_base64(filename):
    with open(filename, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def build_html(story):
    html_parts = [f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{story['title']}</title>
<style>
    body {{
        font-family: Georgia, serif;
        background-color: #fdf6e3;
        margin: 0;
        padding: 40px;
    }}
    h1 {{
        text-align: center;
        color: #5b3a29;
    }}
    .page {{
        max-width: 700px;
        margin: 40px auto;
        background: white;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
    }}
    .page img {{
        max-width: 100%;
        border-radius: 8px;
        margin-bottom: 20px;
    }}
    .page p {{
        font-size: 20px;
        line-height: 1.6;
        color: #333;
    }}
    .page.moral {{
        background: #fff8e7;
    }}
    .page.moral p {{
        font-size: 18px;
        color: #7a5c3e;
    }}
</style>
</head>
<body>
<h1>{story['title']}</h1>
"""]

    for i, page in enumerate(story['pages'], 1):
        image_data_uri = image_to_base64(f"page_{i}.png")
        html_parts.append(f"""
<div class="page">
    <img src="{image_data_uri}" alt="Page {i} illustration">
    <p>{page['text']}</p>
</div>
""")

    html_parts.append(f"""
<div class="page moral">
    <p><em>{story['moral']}</em></p>
</div>
""")

    html_parts.append("</body></html>")
    return "".join(html_parts)


# ---------------------------------------------------------------------------
# ORCHESTRATION
# ---------------------------------------------------------------------------
def make_book(characters, image_backend="pollinations"):
    print(f"\n=== Step 1/3: Writing the story ===")
    story = generate_story(characters)

    print(f"\nTitle: {story['title']}\n")
    print("--- Characters ---")
    for c in story['characters']:
        print(f"{c['name']}: {c['visual_description']}")
    print()

    for i, page in enumerate(story['pages'], 1):
        print(f"--- Page {i} ---")
        print(page['text'])
        print(f"[Scene: {page['scene_description']}]\n")

    print(f"--- Moral ---\n{story['moral']}\n")

    # Build a unique folder for this story, e.g. stories/2026-07-07_01_Duggu-Coco/
    # so that generating multiple books in one day never overwrites or
    # accidentally reuses another story's images.
    folder_name = build_story_folder_name(story)
    folder_path = os.path.join(BASE_STORIES_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    print(f"Saving this story to: {folder_path}\n")
    print(f"Image backend: {image_backend}\n")

    # Everything below (story.json, page_N.png, storybook.html) uses plain
    # relative filenames, same as the original scripts did. Rather than
    # rewrite every function to accept a folder path, we temporarily change
    # the "current directory" to the new folder, run the same code as
    # before, then change back — the `try/finally` guarantees we always
    # switch back even if something fails partway through.
    original_dir = os.getcwd()
    os.chdir(folder_path)
    try:
        # Saved to disk even though we also pass `story` in memory below —
        # this way, if step 2 or 3 fails, the story text isn't lost and you
        # can rerun illustration/build separately without paying for
        # another Claude API call.
        with open("story.json", "w") as f:
            json.dump(story, f, indent=2)
        print("Saved to story.json")

        print(f"\n=== Step 2/3: Illustrating ===")
        if image_backend == "gemini":
            # Imported here (not at the top of the file) so that Pollinations-only
            # runs never need the google-genai package installed at all.
            from gemini_illustrate import generate_images as gemini_generate_images
            gemini_generate_images(story)
        else:
            generate_images(story)

        print(f"\n=== Step 3/3: Building the storybook ===")
        if image_backend == "gemini":
            from gemini_build_book import build_html as gemini_build_html
            html = gemini_build_html(story)
        else:
            html = build_html(story)

        with open("storybook.html", "w", encoding="utf-8") as f:
            f.write(html)
    finally:
        os.chdir(original_dir)

    storybook_path = os.path.join(folder_path, "storybook.html")
    print(f"\nAll done! Open {storybook_path} in your browser.")

    return folder_path


if __name__ == "__main__":
    characters = input("Enter 2-3 characters (e.g. 'a shy fox, a wise old owl'): ")
    make_book(characters)