from langgraph.graph import StateGraph, END
from agents import create_agent

# state sẽ lưu thông tin luồng xử lý
class State(dict):
    input: str
    output: str

# step 1: xử lý input
def process_input(state: State):
    print("📥 Input:", state["input"])
    return state

# step 2: gọi agent với tools
def call_agent(state: State):
    agent = create_agent()
    resp = agent.invoke({"input": state["input"]})
    state["output"] = resp["output"]
    return state

# build graph
def build_graph():
    workflow = StateGraph(State)

    workflow.add_node("process_input", process_input)
    workflow.add_node("call_agent", call_agent)

    workflow.set_entry_point("process_input")
    workflow.add_edge("process_input", "call_agent")
    workflow.add_edge("call_agent", END)

    return workflow.compile()
