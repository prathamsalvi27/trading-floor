import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langgraph.types import Command

from orchestrator.state import build_initial_state
from orchestrator.graph import build_graph


if __name__ == "__main__":
    import asyncio

    async def main():
        state = build_initial_state("AAPL")
        graph = build_graph()
        config = {"configurable": {"thread_id": "test-run-1"}}

        result = await graph.ainvoke(state, config=config)
        print(result["research_report"])
        print(result["trade_decision"])
        print(result["risk_decision"])

        if "__interrupt__" in result:
            prompt = result["__interrupt__"][0].value
            answer = input(f"{prompt} ")
            result = await graph.ainvoke(Command(resume=answer), config=config)
            print("Trade decision result:", result["trade_decision"])

    asyncio.run(main())
