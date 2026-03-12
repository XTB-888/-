"""导出 LangGraph 工作流图的 Mermaid 描述"""
from app.chains.fablelens_graph import build_fablelens_graph


def export_graph():
    graph = build_fablelens_graph()
    compiled = graph.compile()

    # 打印 Mermaid 图
    try:
        mermaid = compiled.get_graph().draw_mermaid()
        print("=== LangGraph Mermaid ===")
        print(mermaid)

        # 保存到文件
        with open("C:/Users/monarch/fablelens/docs/pipeline_graph.md", "w", encoding="utf-8") as f:
            f.write("# FableLens Pipeline Graph\n\n```mermaid\n")
            f.write(mermaid)
            f.write("\n```\n")
        print("\n已保存到 docs/pipeline_graph.md")
    except Exception as e:
        print(f"Mermaid 导出失败: {e}")

    # 打印节点和边
    print("\n=== 节点 ===")
    g = compiled.get_graph()
    for node in g.nodes:
        print(f"  {node}")

    print("\n=== 边 ===")
    for edge in g.edges:
        print(f"  {edge}")


if __name__ == "__main__":
    export_graph()
