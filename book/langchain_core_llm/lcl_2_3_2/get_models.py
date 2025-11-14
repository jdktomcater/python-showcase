import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

models = client.models.list()
for m in models.data:
    print(m)
