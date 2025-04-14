
import os
import requests
import json

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")

def create_blocks_from_markdown(content):
    lines = content.splitlines()
    blocks = []
    for line in lines:
        if line.strip().startswith("#"):
            level = len(line.split(" ")[0])
            text = line[level:].strip()
            blocks.append({
                "object": "block",
                "type": "heading_" + str(min(level, 3)),
                "heading_" + str(min(level, 3)): {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            })
        elif line.strip() == "":
            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}})
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })
    return blocks

def upload_to_notion(page_id, markdown_text):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    blocks = create_blocks_from_markdown(markdown_text)
    for i in range(0, len(blocks), 100):  # Notion API: 최대 100개 블록 제한
        chunk = blocks[i:i + 100]
        res = requests.patch(url, headers=headers, json={"children": chunk})
        print("Notion 응답:", res.status_code)
        if res.status_code != 200:
            print(res.text)

if __name__ == "__main__":
    latest_file = sorted([f for f in os.listdir() if f.startswith("report_") and f.endswith(".md")])[-1]
    with open(latest_file, "r", encoding="utf-8") as f:
        upload_to_notion(NOTION_PAGE_ID, f.read())
