import openai
import os

openai.api_key=os.getenv("OPEN_AI_KEY")
print("OPEN_AI_KEY:", openai.api_key)
response = openai.embeddings.create(
            model="text-embedding-3-small",
            input="Hello World"
        )
print("生成文本:",response.choices[0].text.strip())