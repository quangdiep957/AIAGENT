from graph import build_graph

if __name__ == "__main__":
    workflow = build_graph()

    user_input = "hãy tính tổng 5 + 5"
    result = workflow.invoke({"input": user_input})

    print("✅ Final output:", result["output"])
