from langgraph.graph import StateGraph, END
from agents import get_llm

# state sẽ lưu thông tin luồng xử lý
class State(dict):
    input: str
    output: str

# step 1: xử lý input
def process_input(state: State):
    print("📥 Input:", state["input"])
    return state

# step 2: gọi model
def call_llm(state: State):
    llm = get_llm()
    resp = llm.invoke(state["input"])
    state["output"] = resp.content
    return state

# build graph
def build_graph():
    workflow = StateGraph(State)

    workflow.add_node("process_input", process_input)
    workflow.add_node("call_llm", call_llm)

    workflow.set_entry_point("process_input")
    workflow.add_edge("process_input", "call_llm")
    workflow.add_edge("call_llm", END)

    return workflow.compile()
