import json
import base64

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

if __name__ == "__main__":
    with open("story.json", "r") as f:
        story = json.load(f)

    html = build_html(story)

    with open("storybook.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Saved storybook.html — open it in your browser!")