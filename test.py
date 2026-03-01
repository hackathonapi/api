import base64
import requests

response = requests.post(
    "http://localhost:8000/clearview",
    json={
        "input": "https://www.earthwin.org/blogs/news/your-home-is-burning-because-our-home-is-being-destroyed?gad_source=1&gad_campaignid=22643414352&gbraid=0AAAAA90agjghMfkUgRmLQYu5_pvw1upGs&gclid=Cj0KCQiAwYrNBhDcARIsAGo3u33sj2QaLA7PBIr3rVXAeRbdPE9DDxOtOCl9r-JrzYRQSmwP7HGZ_xEaAkWkEALw_wcB"
    },
    timeout=120,
)

print(f"status:  {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"title:   {data['title']}")
    print(f"words:   {data['word_count']}")
    print(f"summary: {'ok' if data['summary'] else 'failed'}")
    print(f"source:  {data['source']}")

    pdf_bytes = base64.b64decode(data["pdf"])
    with open("output.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"pdf:     saved to output.pdf ({len(pdf_bytes):,} bytes)")
else:
    print(response.text)
