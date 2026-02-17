import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

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
    def test_safe_get_rate_limit_retry(self, mock_ticker_class):
        """test the exceotion of the safe_get method when the rate limit is hit."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.non_existent_attr = None 
        mock_ticker_class.return_value = mock_ticker_instance
        result = self.company_data.safe_get(self.ticker_symbol, "non_existent_attr")
        self.assertIsNone(result)

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

if __name__ == "__main__":
    unittest.main()
