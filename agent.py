from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv
import os
from backend import CompanyData 
from langchain_community.callbacks import get_openai_callback

load_dotenv()

# Cache CompanyData instances to avoid recreating them
_company_cache = {}

def get_company_client(ticker: str) -> CompanyData:
    """Get or create a cached CompanyData instance."""
    ticker = ticker.upper()
    if ticker not in _company_cache:
        _company_cache[ticker] = CompanyData(ticker)
    return _company_cache[ticker]

@tool
def get_company_info(ticker: str):
    """Fetch key company metrics like P/E ratio, Market Cap, and business summary."""
    client = get_company_client(ticker)
    df = client.get_info()
    return df.to_string()

@tool
def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    """Fetch daily price history (OHLCV) for a given ticker and period."""
    client = get_company_client(ticker)
    df = client.get_ticker_data(period=period, interval=interval)
    return df.tail(10).to_string()

@tool
def get_financial_statements(ticker: str):
    """Fetch the annual income statement and financial metrics."""
    client = get_company_client(ticker)
    df = client.get_financials()
    return df.to_string()

def run_financial_agent(app, user_query: str):
    """Executes the financial agent and returns both the response and cost breakdown."""
    with get_openai_callback() as cb:
        result = app.invoke({"messages": [("user", user_query)]})
        final_message = result["messages"][-1].content
        
        cost_info = {
            "total_tokens": cb.total_tokens,
            "prompt_tokens": cb.prompt_tokens,
            "completion_tokens": cb.completion_tokens,
            "total_cost_usd": round(cb.total_cost, 6),
            "successful_requests": cb.successful_requests
        }
        
        return final_message, cost_info
    
if __name__ == "__main__":
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    tools = [get_company_info, get_stock_history, get_financial_statements]
    model = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY, temperature=0)
    
    app = create_agent(
        model=model, 
        tools=tools, 
        system_prompt="You are a helpful financial assistant."
    )

    # Now when comparing TSLA and F, each ticker gets ONE CompanyData instance
    # that's reused across all tool calls
    final_message, cost_info = run_financial_agent(app, "Compare TSLA and F?")
    print(final_message)
    print(f"\nCost Info: {cost_info}")
    print(f"\nCached companies: {list(_company_cache.keys())}")