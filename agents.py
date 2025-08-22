# agents.py
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from tools import get_weather, calculate_sum, semantic_search, wiki_search, wiki_summary
import config  # ensure .env is loaded (load_dotenv runs in config)

def get_llm():
    return ChatOpenAI(model="gpt-4.1", temperature=0)

def create_agent():
    llm = get_llm()
    # Ưu tiên semantic_search đứng trước wiki_search
    tools = [get_weather, calculate_sum, semantic_search, wiki_search, wiki_summary]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    return agent
