# agents.py
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from tools import get_weather, calculate_sum

def get_llm():
    return ChatOpenAI(model="gpt-4.1", temperature=0)

def create_agent():
    llm = get_llm()
    tools = [get_weather, calculate_sum]

    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    return agent
