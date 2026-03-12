"""快速测试 /api/generate 接口"""
import httpx
import json

url = "http://localhost:8000/api/generate"
test_image = "C:/Users/monarch/fablelens/backend/uploads/test_book.jpg"

with open(test_image, "rb") as f:
    files = {"file": ("test_book.jpg", f, "image/jpeg")}
    data = {"style": "治愈"}
    response = httpx.post(url, files=files, data=data, timeout=60)

print(f"Status: {response.status_code}")
result = response.json()
print(json.dumps(result, ensure_ascii=False, indent=2))
