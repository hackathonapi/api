import httpx

response = httpx.post(
    "https://hackathon-api-87l4.onrender.com/extract",
    json={"url": "https://www.earthwin.org/blogs/news/your-home-is-burning-because-our-home-is-being-destroyed?gad_source=1&gad_campaignid=22643414352&gbraid=0AAAAA90agjghMfkUgRmLQYu5_pvw1upGs&gclid=Cj0KCQiAwYrNBhDcARIsAGo3u300bYVJlzRJte03g8yNdqSMjnuJUQT_UqL2FNoIlB4nzJuVfqZCzZgaAqqNEALw_wcB"},
)

result = response.json()

print(f"method:     {result['extraction_method']}")
print(f"word_count: {result['word_count']}")
print(f"error:      {result['error']}")
print("\n--- content ---\n")
print(result["content"])
