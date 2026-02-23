import os

import tiktoken
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.stock_fetcher import CompanyData

# ============================================================================
# CACHE & UTILS
# ============================================================================
_company_cache = {}

def get_company_client(ticker: str) -> CompanyData:
    """Get or create a cached CompanyData instance."""
    ticker = ticker.upper()
    if ticker not in _company_cache:
        _company_cache[ticker] = CompanyData(ticker)
    return _company_cache[ticker]

def get_cached_companies():
    """Return list of currently cached company tickers."""
    return list(_company_cache.keys())

def truncate_tool_output(text: str, max_tokens: int = 5000) -> str:
    """Truncate tool output to prevent exceeding LLM token limits (200k budget)."""
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        return enc.decode(tokens) + f"\n... [output truncated from {len(tokens)} to {max_tokens} tokens]"
    return text


# ============================================================================
# TOOLS
# ============================================================================
@tool
def get_company_info(ticker: str):
    """Fetch key company metrics like P/E ratio, Market Cap, and business summary."""
    client = get_company_client(ticker)
    result = client.get_info().to_string()
    return truncate_tool_output(result, max_tokens=5000)

@tool
def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    """Fetch daily price history (OHLCV) for a given ticker and period.

    IMPORTANT: The period must be one of the following valid values:
    1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

    If the user requests a period that is NOT in the list above (e.g. '1w', '2w', '3m', 'week',
    'month', 'year'), you MUST call correct_period_parameter first to get the valid equivalent,
    then pass the corrected value here.
    """
    client = get_company_client(ticker)
    result = client.get_ticker_data(period=period, interval=interval).tail(10).to_string()
    return truncate_tool_output(result, max_tokens=5000)

@tool
def get_financial_statements(ticker: str):
    """Fetch the annual income statement and financial metrics."""
    client = get_company_client(ticker)
    result = client.get_financials().to_string()
    return truncate_tool_output(result, max_tokens=5000)

@tool
def correct_period_parameter(invalid_period: str) -> str:
    """
    Convert a user-supplied period string (e.g. '1w', '2w', '3m', 'week', 'month', 'year')
    into the nearest valid yfinance period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).
    Call this BEFORE get_stock_history whenever the requested period is not already a valid value.
    Returns the corrected valid period string.
    """
    # Direct mapping for common cases
    period_mapping = {
        '1w': '5d',
        '2w': '1mo',
        '3w': '1mo',
        '4w': '1mo',
        'week': '5d',
        'month': '1mo',
        'year': '1y',
        '3m': '3mo',
        '6m': '6mo',
        '2y': '2y',
        '5y': '5y',
        '10y': '10y',
    }

    # check for direct mapping first
    period_lower = invalid_period.lower().strip()
    if period_lower in period_mapping:
        return period_mapping[period_lower]

    # LLM fallback for edge cases
    correction_llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0
    )

    correction_prompt = f"""Given the invalid period '{invalid_period}'.
        Map it to the nearest valid option, ALWAYS choosing one larger than the invalid value to ensure we get enough data. Valid periods are: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
        Always choose a period that is larger than the invalid input to ensure sufficient data is returned.
        Return ONLY the corrected period value, nothing else."""

    correction_response = correction_llm.invoke([
        SystemMessage(content="Map invalid period to nearest valid option."),
        HumanMessage(content=correction_prompt)
    ])

    corrected = correction_response.content.strip()

    # Validate the response is actually valid
    valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    if corrected in valid_periods:
        return corrected

    # Default fallback
    return '1mo'


class StockMentions(BaseModel):
    symbols: list[str] = Field(description="Explicit ticker symbols found e.g. AAPL, TSLA")
    companies: list[str] = Field(description="Company names found e.g. Apple, Tesla")

@tool
def extract_stock_mentions(query: str) -> dict:
    """
    Extract stock ticker symbols and company names from a user query,
    then search for their symbols. Returns structured data ready for further analysis.
    """
    query = truncate_tool_output(query, max_tokens=1500)
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_model = model.with_structured_output(StockMentions)

    result: StockMentions = structured_model.invoke([
        {
            "role": "system",
            "content": (
                "You are a financial entity extractor. Your job is to extract ONLY explicitly mentioned stock tickers and company names.\n\n"
                "RULES:\n"
                "- Ticker symbols are usually 1-5 uppercase letters (e.g. AAPL, TSLA, GOOGL)\n"
                "- Do NOT extract common English words that happen to be uppercase (e.g. 'IT', 'AI', 'US')\n"
                "- Do NOT infer tickers from company names — only extract what is literally written\n"
                "- Include informal references if unambiguous (e.g. 'the EV maker Elon runs' → Tesla)\n"
                "- Normalize company names to their official form (e.g. 'Meta' → 'Meta Platforms')\n"
                "- If a ticker and company refer to the same entity, include both\n"
                "- Return empty lists if nothing is explicitly mentioned"
            )
        },
        {
            "role": "user",
            "content": query
        }
    ])

    resolved = []

    # If tickers were directly mentioned, use them as-is
    for symbol in result.symbols:
        resolved.append({
            "symbol": symbol,
            "source": "ticker_mentioned",
            "search_result": None
        })

    # For company names, search for their ticker
    for company in result.companies:
        # Skip if we already have a ticker for this company
        already_found = any(r["symbol"].upper() == company.upper() for r in resolved)
        if already_found:
            continue

        search_result = CompanyData.search_stock_symbol(company)
        if search_result["found"]:
            resolved.append({
                "symbol": search_result["symbol"],
                "name": search_result["name"],
                "source": "company_name_searched",
                "search_result": search_result
            })
        else:
            resolved.append({
                "symbol": None,
                "name": company,
                "source": "company_name_searched",
                "search_result": search_result
            })

    # Limit resolved results to prevent token bloat
    resolved_limited = resolved[:20] if len(resolved) > 20 else resolved

    return {
        "mentions": {
            "symbols": result.symbols,
            "companies": result.companies
        },
        "resolved": resolved_limited,
        "summary": (
            f"Found {len(result.symbols)} ticker(s) and {len(result.companies)} company name(s). "
            f"Resolved {sum(1 for r in resolved_limited if r['symbol'])} to valid symbols. "
            f"(Limited to {len(resolved_limited)} results)"
        )
    }
