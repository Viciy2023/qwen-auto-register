import requests

access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjhjZWJjOTQxLWQ1MzEtNGY2OS1hZmMwLTNiMTRkMWUzMmFmZiIsImxhc3RfcGFzc3dvcmRfY2hhbmdlIjoxNzczMDgxNjI1LCJleHAiOjE3NzU2NzM2Mzd9.Rogq0ueqK-1-uRdybqZqSkj8E9Es2mcPuZOsrKey1Oo"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# 测试 Qwen API
response = requests.get("https://portal.qwen.ai/v1/models", headers=headers)

print(f"状态码：{response.status_code}")
print(f"响应：{response.text[:500]}")