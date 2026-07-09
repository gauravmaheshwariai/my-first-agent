"""
app.py — a tiny web server around make_book.py

Routes (a "route" is just: which URL triggers which function):
  GET  /            -> shows the form (templates/index.html)
  POST /generate     -> runs make_book() with the submitted characters,
                         then sends the browser to the finished storybook
  GET  /stories/...  -> serves the generated images/HTML files so the
                         browser can actually display them

This file also works when packaged into a Windows .exe with PyInstaller
(see the comment block below for why the path handling looks the way it does).
"""

import sys
import os

# ---------------------------------------------------------------------------
# Path setup — this block MUST run before we import make_book, because
# make_book.py calls load_dotenv() as soon as it's imported, and that
# needs to find .env in the right folder.
#
# The problem this solves: when PyInstaller packages this into a single
# .exe with --onefile, double-clicking that exe extracts everything into
# a TEMPORARY folder at runtime (accessible via sys._MEIPASS) and deletes
# it when the app closes. If we saved stories there, they'd vanish. So:
#   - BASE_DIR = the folder where the real, permanent .exe lives
#     (used for .env, and for saving story.json/images/stories/)
#   - TEMPLATE_DIR = where the bundled templates/index.html actually is
#     (the temporary extracted folder, since that's a bundled resource,
#      not something we write to)
#
# `sys.frozen` is a flag PyInstaller sets automatically inside the exe —
# it's False when you run `py app.py` normally, so this code works
# identically in both cases.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    TEMPLATE_DIR = os.path.join(sys._MEIPASS, "templates")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Make BASE_DIR the working directory BEFORE importing make_book, so its
# load_dotenv() call (which looks in the current directory by default)
# finds the .env file sitting next to the real .exe.
os.chdir(BASE_DIR)

import random
import threading
import webbrowser
from flask import Flask, render_template, request, redirect, send_from_directory

from make_book import make_book, BASE_STORIES_DIR

app = Flask(__name__, template_folder=TEMPLATE_DIR)


# ---------------------------------------------------------------------------
# Preset generation — a fresh set of character combos every time the
# form page loads, using modern Indian (Gen Z-style) names.
# ---------------------------------------------------------------------------
BOY_NAMES = [
    "Aarav", "Vihaan", "Reyansh", "Ayaan", "Kabir", "Advait",
    "Arjun", "Rudra", "Ishaan", "Veer", "Dhruv", "Aryan",
]
GIRL_NAMES = [
    "Anaya", "Diya", "Myra", "Aadhya", "Ira", "Kiara",
    "Saanvi", "Anvi", "Riya", "Zara", "Meher", "Navya",
]

HUMAN_TEMPLATES_BOY = [
    "a curious little boy named {name}",
    "a cheerful baby boy named {name}",
    "a brave young boy named {name}",
]
HUMAN_TEMPLATES_GIRL = [
    "a curious little girl named {name}",
    "a cheerful baby girl named {name}",
    "a brave young girl named {name}",
]

# Each animal has a description phrase and a pool of possible pet-style
# names, so the same animal type doesn't always get the same name.
ANIMALS = [
    {"phrase": "a wise old owl", "names": ["Hoot", "Ollie", "Whisk"]},
    {"phrase": "a mischievous little monkey", "names": ["Bunty", "Chintu", "Jhumroo"]},
    {"phrase": "a gentle green crocodile", "names": ["Snappy", "Miru", "Guddu"]},
    {"phrase": "a curious baby elephant", "names": ["Tumbo", "Gaju", "Bellu"]},
    {"phrase": "a clever little fox", "names": ["Foxy", "Chiku", "Ruby"]},
    {"phrase": "a playful puppy", "names": ["Max", "Bruno", "Coco"]},
    {"phrase": "a sleepy kitten", "names": ["Luna", "Milo", "Bella"]},
    {"phrase": "a fluffy white rabbit", "names": ["Snowy", "Fluffy", "Bunny"]},
    {"phrase": "a tiny chirpy sparrow", "names": ["Pip", "Chiv", "Tweety"]},
    {"phrase": "a colorful parrot", "names": ["Mithu", "Rangeela", "Polly"]},
    {"phrase": "a gentle baby bear", "names": ["Leo", "Teddy", "Bruno"]},
    {"phrase": "a curious little tiger cub", "names": ["Sheru", "Rocky", "Simba"]},
]


def build_human_animal_preset():
    is_boy = random.choice([True, False])
    name = random.choice(BOY_NAMES if is_boy else GIRL_NAMES)
    template = random.choice(HUMAN_TEMPLATES_BOY if is_boy else HUMAN_TEMPLATES_GIRL)
    human_desc = template.format(name=name)

    animal = random.choice(ANIMALS)
    animal_name = random.choice(animal["names"])
    animal_desc = f'{animal["phrase"]} named {animal_name}'

    return {
        "label": f"{name} & {animal_name}",
        "text": f"{human_desc}, {animal_desc}",
    }


def build_two_animal_preset():
    animal1, animal2 = random.sample(ANIMALS, 2)  # sample = no repeats
    name1 = random.choice(animal1["names"])
    name2 = random.choice(animal2["names"])

    return {
        "label": f"{name1} & {name2}",
        "text": f'{animal1["phrase"]} named {name1}, {animal2["phrase"]} named {name2}',
    }


def generate_presets(count=3):
    human_animal_presets = [build_human_animal_preset() for _ in range(count)]
    two_animal_presets = [build_two_animal_preset() for _ in range(count)]
    return human_animal_presets, two_animal_presets


@app.route("/")
def home():
    # A new random set is picked on every page load — refresh the page
    # and you'll see different names each time.
    human_animal_presets, two_animal_presets = generate_presets(count=3)

    # render_template looks inside a folder called "templates" by default,
    # fills in the HTML file with the variables passed here, then sends
    # the result to the browser.
    return render_template(
        "index.html",
        human_animal_presets=human_animal_presets,
        two_animal_presets=two_animal_presets,
    )


@app.route("/generate", methods=["POST"])
def generate():
    # When the form is submitted, its input field's `name="characters"`
    # becomes available here via request.form.
    characters = request.form.get("characters", "").strip()

    if not characters:
        # No input — just send them back to the form instead of crashing.
        return redirect("/")

    # Which illustration backend the user picked in the form.
    # Defaults to "pollinations" if the radio buttons aren't in index.html
    # yet, so nothing breaks before you've added the toggle there.
    image_backend = request.form.get("image_backend", "pollinations")

    # This is the exact same function your command-line version calls.
    # It blocks (the page will just sit there loading) until the story,
    # images, and HTML are all done — for a personal project that's fine,
    # but it does mean generation can take 30-60+ seconds per book
    # (longer for Gemini than Pollinations).
    folder_path = make_book(characters, image_backend=image_backend)

    # folder_path looks like "stories/2026-07-07_01_Duggu-Coco"
    # We only need the folder NAME to build the browser URL below.
    folder_name = os.path.basename(folder_path)

    return redirect(f"/stories/{folder_name}/storybook.html")


@app.route("/stories/<path:subpath>")
def serve_story_file(subpath):
    # This lets the browser load storybook.html AND the base64-embedded
    # images inside it directly from your stories/ folder.
    return send_from_directory(BASE_STORIES_DIR, subpath)


def open_browser():
    # Called once, 1.5 seconds after the server starts. The delay matters:
    # if we open the browser tab immediately, Flask may not be listening
    # yet and the tab would show "can't connect."
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()

    # debug=False for the packaged exe: debug mode's auto-reloader can
    # cause Flask to start twice, which would open two browser tabs.
    # (While actively developing with `py app.py`, you can temporarily
    # switch this back to True to get auto-restart-on-save.)
    app.run(debug=False)