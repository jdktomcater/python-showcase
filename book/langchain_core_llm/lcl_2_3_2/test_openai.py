import openai
import os

openai.api_key=os.getenv("OPEN_AI_KEY")

response = openai.embeddings.create(
            model="text-embedding-3-large",
            input="Hello World"
        )


print("生成文本:",response.choices[0].text.strip())