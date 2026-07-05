import json
import os
import time
import requests
from urllib.parse import quote

FIXED_SEED = 42

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

if __name__ == "__main__":
    with open("story.json", "r") as f:
        story = json.load(f)

    print(f"Illustrating: {story['title']}\n")
    generate_images(story)
    print("\nDone! Check your folder for page_1.png, page_2.png, etc.")