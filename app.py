import chainlit as cl

from backend.agent import (
    create_financial_agent,
    run_financial_agent,
)
from backend.tools import (
    get_cached_companies,
)


@cl.on_chat_start
async def start():
    """Initialize the agent when a new chat session starts."""
    app = create_financial_agent()
    cl.user_session.set("agent", app)

    await cl.Message(
        content="👋 Welcome to the Financial Analysis Assistant! Ask me about stock comparisons, company info, or financial metrics. Try: 'Compare TSLA and F' or 'What's the P/E ratio of AAPL?'"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages from the user."""
    app = cl.user_session.get("agent")
    msg = cl.Message(content="")
    await msg.send()
    response, cost = run_financial_agent(app, message.content, enable_logging=True)

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
