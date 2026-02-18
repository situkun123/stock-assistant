import os

import chainlit as cl
from dotenv import load_dotenv

from backend.agent import (
    create_financial_agent,
    run_financial_agent,
)
from backend.tools import (
    get_cached_companies,
)

ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "false").lower() == "true"
load_dotenv()

def load_users():
    """Load users from AUTH_USERS env variable (format: user1:pass1,user2:pass2)."""
    users_str = os.getenv("AUTH_USERS")
    if not users_str:
        raise ValueError("AUTH_USERS environment variable is not set.")
    users = {}
    for pair in users_str.split(","):
        parts = pair.strip().split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid AUTH_USERS entry: '{pair.strip()}'. Expected format: username:password")
        users[parts[0]] = parts[1]
    return users

USERS = load_users()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Simple username/password authentication."""
    if username in USERS and USERS[username] == password:
        return cl.User(
            identifier=username, 
            metadata={
                "role": "user",
                "provider": "credentials"
            }
        )
    else:
        return None


@cl.on_chat_start
async def start():
    """Initialize the agent when a new chat session starts."""
    user = cl.user_session.get("user")

    app = create_financial_agent()
    thread_id = user.identifier

    cl.user_session.set("agent", app)
    cl.user_session.set("thread_id", thread_id)

    actions = [
        cl.Action(name="compare", payload={"query": "Compare AAPL and MSFT"}, label="📊 Compare Stocks"),
        cl.Action(name="info", payload={"query": "Tell me about Tesla (TSLA)"}, label="💼 Company Info"),
        cl.Action(name="price", payload={"query": "What's NVDA's current price?"}, label="💰 Stock Price"),
        cl.Action(name="pe", payload={"query": "What's the P/E ratio of GOOGL?"}, label="📈 P/E Ratio"),
    ]

    await cl.Message(
        content="""👋 Welcome to the Financial Analysis Assistant! Ask me anything about stocks, companies, or financial metrics. It is best to use the stock symbol (e.g., AAPL for Apple) for more accurate results, Here are some example actions to get you started:""",
        actions=actions
    ).send()

@cl.action_callback("compare")
@cl.action_callback("info")
@cl.action_callback("price")
@cl.action_callback("pe")
async def on_action(action: cl.Action):
    """Handle suggested action clicks."""
    query = action.payload["query"]
    await cl.Message(content=query, author="You").send()
    await main(cl.Message(content=query))


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages from the user."""
    app = cl.user_session.get("agent")
    thread_id = cl.user_session.get("thread_id") 
    msg = cl.Message(content="")

    await msg.send()
    response, cost = run_financial_agent(
        app, 
        message.content, 
        thread_id=thread_id, 
        enable_logging=ENABLE_LOGGING
    )

    # Update the message with the result
    msg.content = response
    await msg.update()
    cached = get_cached_companies()
    if cost['tools_used']:
        tools_str = ', '.join([f"{tool}: {count}" for tool, count in cost['tools_used'].items()])
    else:
        tools_str = 'None'

    cost_info = f"""
            📊 **Usage Statistics:**
            - Total Tokens: {cost['total_tokens']:,}
            - Prompt Tokens: {cost['prompt_tokens']:,}
            - Completion Tokens: {cost['completion_tokens']:,}
            - Total Cost: ${cost['total_cost_usd']:.6f} USD
            - LLM API Calls: {cost['llm_calls']}
            - Tool Calls: {cost['tool_calls']}
            - Cached Companies: {', '.join(cached) if cached else 'None'}
            - Tools Used: {tools_str}
            """
    await cl.Message(
        content=cost_info,
        author="System"
    ).send()


@cl.on_chat_end
async def end():
    """Clean up when chat session ends."""
    await cl.Message(
        content="👋 Thanks for using the Financial Analysis Assistant! Session ended.",
        author="System"
    ).send()



if __name__ == "__main__":
    # This will be handled by the chainlit run command
    pass
