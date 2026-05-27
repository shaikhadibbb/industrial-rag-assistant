"""Download free industrial manuals for testing."""
import httpx
import os

docs = [
    {
        "url": "https://www.atlascopco.com/content/dam/atlas-copco/local-countries/pakistan/documents/compressed-air-manual.pdf",
        "filename": "atlas-copco-compressed-air-guide.pdf"
    }
]

os.makedirs("data/raw", exist_ok=True)

for doc in docs:
    path = f"data/raw/{doc['filename']}"
    if os.path.exists(path):
        print(f"Already exists: {path}")
        continue
    print(f"Downloading {doc['filename']}...")
    try:
        r = httpx.get(doc["url"], follow_redirects=True, timeout=30)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"✅ Saved: {path}")
        else:
            print(f"❌ Failed: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
