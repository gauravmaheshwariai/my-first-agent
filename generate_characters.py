import json
import os
import base64
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

with open("story.json", "r") as f:
    story = json.load(f)

for c in story["characters"]:
    filename = f"character_{c['name'].replace(' ', '_')}.png"
    if os.path.exists(filename):
        print(f"{filename} already exists, skipping.")
        continue

    prompt = (
        f"A children's storybook character reference portrait, watercolor style, "
        f"warm colors. {c['visual_description']} "
        f"Full body, simple plain background, facing forward, standing pose."
    )

    print(f"Generating reference image for {c['name']}...")
    interaction = client.interactions.create(
        model="gemini-2.5-flash-image",
        input=prompt,
    )

    with open(filename, "wb") as f:
        f.write(base64.b64decode(interaction.output_image.data))
    print(f"  Saved {filename}")

print("\nDone generating character references!")