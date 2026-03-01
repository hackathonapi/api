import requests

response = requests.post(
    "http://127.0.0.1:8000/audiobook",
    json={
        "input": "https://www.earthwin.org/blogs/news/your-home-is-burning-because-our-home-is-being-destroyed?gad_source=1&gad_campaignid=22643414352&gbraid=0AAAAA90agjghMfkUgRmLQYu5_pvw1upGs&gclid=Cj0KCQiAwYrNBhDcARIsAGo3u33sj2QaLA7PBIr3rVXAeRbdPE9DDxOtOCl9r-JrzYRQSmwP7HGZ_xEaAkWkEALw_wcB"
    },
    timeout=120,
)

print(f"status:  {response.status_code}")

if response.status_code == 200:
    with open("output.mp3", "wb") as f:
        f.write(response.content)
    print(f"audio:   saved to output.mp3 ({len(response.content):,} bytes)")
else:
    print(response.text)
