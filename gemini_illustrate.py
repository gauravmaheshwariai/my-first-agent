import json
import os
import base64
import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

MODEL = "gemini-3.1-flash-lite-image"
DAILY_CAP = 20
CAP_FILE = "gemini_usage_today.json"


def check_and_increment_daily_cap():
    """Refuses to make another call once today's cap is hit.
    Stored as {"date": "...", "count": N} so it self-resets each day."""
    today = datetime.date.today().isoformat()

    if os.path.exists(CAP_FILE):
        with open(CAP_FILE, "r") as f:
            usage = json.load(f)
    else:
        usage = {"date": today, "count": 0}

    if usage.get("date") != today:
        usage = {"date": today, "count": 0}  # new day, reset

    if usage["count"] >= DAILY_CAP:
        raise RuntimeError(
            f"Daily Gemini image cap ({DAILY_CAP}) reached for {today}. "
            f"Stopping here to avoid unexpected spend."
        )

    usage["count"] += 1
    with open(CAP_FILE, "w") as f:
        json.dump(usage, f)

    return usage["count"]


def load_character_images(story, folder="."):
    images = []
    for c in story["characters"]:
        filename = os.path.join(folder, f"character_{c['name'].replace(' ', '_')}.png")
        with open(filename, "rb") as f:
            image_bytes = f.read()
        images.append({
            "type": "image",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": "image/png",
        })
    return images


def generate_images(story, folder="."):
    character_images = load_character_images(story, folder=folder)
    character_names = ", ".join(c["name"] for c in story["characters"])

    for i, page in enumerate(story["pages"], 1):
        filename = os.path.join(folder, f"gemini_page_{i}.png")

        if os.path.exists(filename):
            print(f"Page {i} already exists, skipping.")
            continue

        used_today = check_and_increment_daily_cap()

        scene = page["scene_description"]
        text_prompt = (
            f"Using the exact same characters shown in the reference images "
            f"({character_names}), draw this scene: {scene}. "
            f"Children's storybook illustration, watercolor style, warm colors. "
            f"Keep each character's appearance identical to their reference image."
        )

        request_input = [{"type": "text", "text": text_prompt}] + character_images

        print(f"Generating image for page {i}... (call {used_today}/{DAILY_CAP} today)")
        interaction = client.interactions.create(
            model=MODEL,
            input=request_input,
        )

        with open(filename, "wb") as f:
            f.write(base64.b64decode(interaction.output_image.data))
        print(f"  Saved {filename}")


if __name__ == "__main__":
    with open("story.json", "r") as f:
        story = json.load(f)

    print(f"Illustrating (Gemini): {story['title']}\n")
    generate_images(story)
    print("\nDone! Check your folder for gemini_page_1.png, gemini_page_2.png, etc.")