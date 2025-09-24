from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()


response = client.embeddings.create(
    input="Your text string goes here",
    model="text-embedding-3-small"
)

print(response.data[0].embedding)