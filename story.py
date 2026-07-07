import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

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

if __name__ == "__main__":
    characters = input("Enter 2-3 characters (e.g. 'a shy fox, a wise old owl'): ")
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

    with open("story.json", "w") as f:
        json.dump(story, f, indent=2)
    print("Saved to story.json")