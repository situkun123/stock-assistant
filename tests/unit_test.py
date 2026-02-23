import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

os.environ.setdefault("YF_CACHE_DIR", tempfile.mkdtemp())

from backend.stock_fetcher import CompanyData


class TestCompanyData(unittest.TestCase):
    def setUp(self):
        """Initialize the class with a dummy ticker."""
        self.ticker_symbol = "NVDA"
        with patch('yfinance.Ticker'):
            self.company_data = CompanyData(self.ticker_symbol)

    @patch('yfinance.Ticker')
    def test_safe_get_success(self, mock_ticker_class):
        """Test safe_get returns data when yfinance succeeds."""
        # Setup mock
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {"sector": "Technology", "fullTimeEmployees": 26000}
        mock_ticker_class.return_value = mock_ticker_instance

        result = self.company_data.safe_get(self.ticker_symbol, "info")

        self.assertEqual(result["sector"], "Technology")
        self.assertEqual(len(result), 2)

    @patch('yfinance.Ticker')
    def test_get_info_returns_dataframe(self, mock_ticker_class):
        """Test get_info converts the dictionary to a formatted DataFrame."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {"marketCap": 3000000000}
        mock_ticker_class.return_value = mock_ticker_instance

        with patch.object(CompanyData, 'safe_get', return_value={"marketCap": 3000000000}):
            df = self.company_data.get_info()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.loc["marketCap", "Value"], 3000000000)

    @patch('yfinance.Ticker')
    def test_get_ticker_data_failure(self, mock_ticker_class):
        """Test get_ticker_data returns empty DataFrame on failure."""
        with patch.object(CompanyData, 'safe_get', return_value=None):
            df = self.company_data.get_ticker_data()

        self.assertTrue(df.empty)
        self.assertIsInstance(df, pd.DataFrame)

class TestAgentFunctions(unittest.TestCase):

    def test_should_continue_returns_tools_when_tool_calls_present(self):
        """should_continue routes to 'tools' when the last message has tool_calls."""
        mock_message = MagicMock()
        mock_message.tool_calls = [{"name": "get_stock_history", "args": {}}]
        state = {"messages": [mock_message]}

        from backend.agent import should_continue
        result = should_continue(state)
        self.assertEqual(result, "tools")

    def test_should_continue_returns_end_when_no_tool_calls(self):
        """should_continue routes to 'end' when the last message has no tool_calls."""
        mock_message = MagicMock()
        mock_message.tool_calls = []
        state = {"messages": [mock_message]}

        from backend.agent import should_continue
        result = should_continue(state)
        self.assertEqual(result, "end")

    def test_call_model_returns_message_in_state(self):
        """call_model invokes the model and wraps the response in a messages dict."""
        from langchain_core.messages import HumanMessage

        mock_response = MagicMock()
        mock_model = MagicMock()
        mock_model_with_tools = MagicMock()
        mock_model.bind_tools.return_value = mock_model_with_tools
        mock_model_with_tools.invoke.return_value = mock_response

        state = {"messages": [HumanMessage(content="Test message")]}
        tools = []

        from backend.agent import call_model
        result = call_model(state, mock_model, tools)

        self.assertIn("messages", result)
        self.assertEqual(result["messages"], [mock_response])

    def test_call_model_with_multiple_messages(self):
        """call_model invokes the model with multiple messages in state."""
        from langchain_core.messages import HumanMessage

        from backend.agent import call_model

        mock_response = MagicMock()
        mock_model = MagicMock()
        mock_model_with_tools = MagicMock()
        mock_model.bind_tools.return_value = mock_model_with_tools
        mock_model_with_tools.invoke.return_value = mock_response

        state = {
            "messages": [HumanMessage(content="What is AAPL?")],
        }
        tools = []
        result = call_model(state, mock_model, tools)

        self.assertIn("messages", result)
        self.assertEqual(result["messages"], [mock_response])
        # Verify that invoke was called with the messages from state
        mock_model_with_tools.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main()
