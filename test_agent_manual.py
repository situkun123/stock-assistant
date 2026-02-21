from backend.agent import create_financial_agent, run_financial_agent
from backend.tools import extract_stock_mentions
from backend.stock_fetcher import CompanyData
from backend.utils import create_state_graph, open_ai_key_test
from backend.database import clear_thread_checkpoints
import openai
import os
from dotenv import load_dotenv

def main():
    print("Creating financial agent...")
    app = create_financial_agent()
    print("✓ Agent created successfully\n")

    clear_thread_checkpoints("test-session")
    print("✓ Cleared previous session memory\n")

    # Test queries
    test_queries = [
        # "What is the current stock price of AAPL?",
        # "Compare bp and shell stock performance over the last month",
        # 'what is the pe ratio of Abbott Laboratories and 3M',
        # "Tell me about Tesla's recent performance",
        "What is the current stock price of Rollins Inc?"
    ]

    for i, query in enumerate(test_queries, 1):
        print("=" * 80)
        print(f"Query {i}: {query}")
        print("=" * 80)

        try:
            responses = run_financial_agent(
                app, query, thread_id="test-session", enable_logging=False
            )
            for response in responses:
                if isinstance(response, str):
                    print(f"\n✓ Response:\n{response}\n")
                elif isinstance(response, dict):
                    print(f"📊 Metadata:")
                    print(f"  Tokens: {response['total_tokens']}")
                    print(f"  Cost: ${response['total_cost_usd']}")
                    print(f"  Tool calls: {response['tool_calls']}")
                    print(f"  No. of LLM calls: {response['llm_calls']}")
                    print(f"  Tools used: {response['tools_used']}")
        except Exception as e:
            print(f"✗ Error: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # open_ai_key_test()
        # from pprint import pprint   
    # main()
    # query = 'what is the pe ratio of Abbott Laboratories and 3M'
    # # app = create_financial_agent()
    # create_state_graph(app)
   
    # result = extract_stock_mentions.invoke({
    #     "query": query
    #     })
    # pprint(result)


