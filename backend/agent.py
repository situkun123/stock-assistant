import os
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.database import Logger
from backend.tools import (
    correct_period_parameter,
    extract_stock_mentions,
    get_company_info,
    get_financial_statements,
    get_stock_history,
)

root_dir = Path(__file__).resolve().parent.parent

# 2. Add that root directory to sys.path
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

load_dotenv()

# ============================================================================
# STATE & GRAPH NODES
# ============================================================================
class AgentState(TypedDict):
    """State object that flows through the graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]

def trim_message_history(messages: Sequence[BaseMessage], max_tokens: int = 160000) -> list[BaseMessage]:
    """
    Trim messages to stay under token limit.
    Always preserves the SystemMessage and the latest HumanMessage.
    """
    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        strategy="last",           # keep the most recent messages
        token_counter=ChatOpenAI(model="gpt-4o-mini"),
        include_system=True,       # always keep the system prompt
        allow_partial=False,       # never cut a message in half
        start_on="human",          # ensure trimmed history starts on a human turn
    )
    if len(trimmed) < len(messages):
        dropped = len(messages) - len(trimmed)
        print(f"⚠️  Trimmed {dropped} messages to stay under {max_tokens:,} token limit.")
    return trimmed

def call_model(state: AgentState, model, tools):
    """Call LLM with tool binding to decide next action."""
    messages = state["messages"]
    messages = trim_message_history(messages, max_tokens=20000)

    try:
        input_tokens = model.get_num_tokens_from_messages(messages)
    except Exception:
        input_tokens = "unknown"

    print(f"📨 Next call input: {len(messages)} messages, ~{input_tokens} tokens")

    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Route to tools, fallback, or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # Count total LLM responses (AIMessages) as a proxy for LLM calls
    llm_calls = sum(
        1 for m in messages
        if hasattr(m, "type") and m.type == "ai"
    )

    if llm_calls >= 20:
        return "fallback"

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        total_tool_calls = sum(
            len(m.tool_calls)
            for m in messages
            if hasattr(m, "tool_calls") and m.tool_calls
        )
        if total_tool_calls >= 50:
            return "fallback"
        return "tools"

    return "end"

def fallback_response(state: AgentState):
    """Return fallback message when LLM call limit is reached."""
    fallback = SystemMessage(
        content="I'm sorry, I wasn't able to find a confident answer for your query. "
                "Please try rephrasing your question or provide more specific details such as the stock symbol."
    )
    return {"messages": [fallback]}

# ============================================================================
# AGENT CREATION
# ============================================================================
def create_financial_agent():
    """Create financial analysis agent using LangGraph StateGraph."""
    tools = [
             get_company_info, 
             get_stock_history, 
             get_financial_statements, 
             correct_period_parameter, 
             extract_stock_mentions]

    model = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0
    )

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", lambda state: call_model(state, model, tools))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("fallback", fallback_response)  # ← new node

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "fallback": "fallback",  # ← route to fallback when limit hit
        "end": END
    })
    workflow.add_edge("tools", "agent")
    workflow.add_edge("fallback", END) 

    db_path = os.getenv("CHECKPOINT_DB_PATH", str(root_dir / "data" / "checkpoints.db"))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)

    return workflow.compile(checkpointer=memory)
    # return workflow.compile()


def run_financial_agent(app, user_query: str, thread_id: str = "default", enable_logging: bool = True):
    """Execute agent and yield responses with cost breakdown."""

    system_prompt = """You are a financial analysis assistant. Your role is to:
                - Analyze stock data and financial statements objectively
                - Provide clear, data-driven insights
                - Use available tools to gather accurate information
                - Always cite your data sources"""

    initial_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query)
    ]
    config = {"configurable": {"thread_id": thread_id}}

    with get_openai_callback() as cb:
        result = app.invoke({"messages": initial_messages}, config=config)
        tool_calls = 0
        tools_used = {}

        for message in result["messages"]:
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls += len(message.tool_calls)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name", "Unknown")
                    tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

            response_content = message.content
            # print(response_content)  # Print the response content for streaming

        metadata = {
            "total_tokens": cb.total_tokens,
            "prompt_tokens": cb.prompt_tokens,
            "completion_tokens": cb.completion_tokens,
            "total_cost_usd": round(cb.total_cost, 6),
            "successful_requests": cb.successful_requests,
            "llm_calls": cb.successful_requests,
            "tool_calls": tool_calls,
            "tools_used": tools_used
        }

        if enable_logging:
            try:
                logger = Logger(database_name="stock-assistant")
                logger.connect()
                logger.log_agent_run(user_query, response_content, metadata)
                logger.close()
            except Exception as e:
                print(f"⚠️  Warning: Failed to log to MotherDuck: {e}")
        return response_content, metadata


if __name__ == "__main__":
    pass
    # prompt = "Is MSFT still a buy"
    # response, cost = run_financial_agent(
    #     app,
    #     prompt
    # )

    # print("=" * 80)
    # print("RESPONSE:")
    # print("=" * 80)
    # print(response)
    # print("\n" + "=" * 80)
    # print("COST:")
    # print("=" * 80)
    # print(cost)
    # print(f"Cached companies: {get_cached_companies()}")
