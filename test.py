import httpx

response = httpx.post(
    "https://hackathon-api-87l4.onrender.com/pdf",
    json={
        "input": "https://www.earthwin.org/blogs/news/your-home-is-burning-because-our-home-is-being-destroyed?gad_source=1&gad_campaignid=22643414352&gbraid=0AAAAA90agjghMfkUgRmLQYu5_pvw1upGs&gclid=Cj0KCQiAwYrNBhDcARIsAGo3u33sj2QaLA7PBIr3rVXAeRbdPE9DDxOtOCl9r-JrzYRQSmwP7HGZ_xEaAkWkEALw_wcB"
    },
)

print(f"status: {response.status_code}")
print(f"content-type: {response.headers.get('content-type')}")

if response.status_code == 200:
    with open("output.pdf", "wb") as f:
        f.write(response.content)
    print("saved to output.pdf")
else:
    print(response.text)
