from langchain_openai import ChatOpenAI

# agent chính
def get_llm():
    return ChatOpenAI(model="gpt-4.1", temperature=0)