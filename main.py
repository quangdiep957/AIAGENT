from graph import build_graph

if __name__ == "__main__":
    workflow = build_graph()

    user_input = "Xin tóm tắt 3 điểm chính về công nghệ LangGraph"
    result = workflow.invoke({"input": user_input})

    print("✅ Final output:", result["output"])
