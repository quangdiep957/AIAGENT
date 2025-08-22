from graph import build_graph

if __name__ == "__main__":
    workflow = build_graph()

    user_input = "thời tiết tại hà nội hôm nay"
    result = workflow.invoke({"input": user_input})

    print("✅ Final output:", result["output"])
