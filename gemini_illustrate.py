import json
import os
import base64
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

def load_character_images(story):
    """Load each character's saved reference image as base64 data."""
    images = []
    for c in story["characters"]:
        filename = f"character_{c['name'].replace(' ', '_')}.png"
        with open(filename, "rb") as f:
            image_bytes = f.read()
        images.append({
            "type": "image",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
            "mime_type": "image/png"
        })
    return images

def generate_images(story):
    character_images = load_character_images(story)
    character_names = ", ".join(c["name"] for c in story["characters"])

    for i, page in enumerate(story["pages"], 1):
        filename = f"page_{i}.png"

        if os.path.exists(filename):
            print(f"Page {i} already exists, skipping.")
            continue

        scene = page["scene_description"]
        text_prompt = (
            f"Using the exact same characters shown in the reference images "
            f"({character_names}), draw this scene: {scene}. "
            f"Children's storybook illustration, watercolor style, warm colors. "
            f"Keep each character's appearance identical to their reference image."
        )

        # Reference images first, then the text instruction - this order
        # matches Google's documented pattern for image-based generation
        request_input = character_images + [{"type": "text", "text": text_prompt}]

        print(f"Generating image for page {i}...")
        interaction = client.interactions.create(
            model="gemini-2.5-flash-image",
            input=request_input,
        )

        with open(filename, "wb") as f:
            f.write(base64.b64decode(interaction.output_image.data))
        print(f"  Saved {filename}")

if __name__ == "__main__":
    with open("story.json", "r") as f:
        story = json.load(f)

    print(f"Illustrating: {story['title']}\n")
    generate_images(story)
    print("\nDone! Check your folder for page_1.png, page_2.png, etc.")