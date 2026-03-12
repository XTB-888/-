"""完整联调测试 - 冒险风格"""
import httpx
import json
import time

url = "http://localhost:8000/api/generate"
test_image = "C:/Users/monarch/fablelens/backend/uploads/test_book.jpg"

t0 = time.time()
with open(test_image, "rb") as f:
    files = {"file": ("test_book.jpg", f, "image/jpeg")}
    data = {"style": "冒险"}
    response = httpx.post(url, files=files, data=data, timeout=180)

elapsed = round(time.time() - t0, 1)
d = response.json()

print(f"Status: {response.status_code} | {elapsed}s")
print(f"Title: {d['story']['title']}")
print(f"Words: {len(d['story']['full_text'])}")
print(f"Images: {len([u for u in d['image_urls'] if u])}")
print(f"Quality: {d['status']}")
print(f"\nTimings:")
for k, v in sorted(d.get("step_timings", {}).items()):
    print(f"  {k}: {v}s")
print(f"\nStory preview:")
print(d["story"]["full_text"][:300] + "...")
