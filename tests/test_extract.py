import pytest
from unittest.mock import patch, MagicMock
from ingestion.api.extract import FakeStoreExtractor


class TestFakeStoreExtractor:

    @patch("ingestion.api.extract.APIClient")
    def test_extract_products_returns_list(
        self, mock_client_class, mock_api_response_products
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_api_response_products
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_products()

        assert isinstance(result, list)
        assert len(result) == 2
        mock_client.get.assert_called_once_with("products")

    @patch("ingestion.api.extract.APIClient")
    def test_extract_products_record_shape(
        self, mock_client_class, mock_api_response_products
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_api_response_products
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_products()

        first = result[0]
        assert "id" in first
        assert "title" in first
        assert "price" in first
        assert "category" in first
        assert "rating" in first

    @patch("ingestion.api.extract.APIClient")
    def test_extract_users_returns_list(
        self, mock_client_class, mock_api_response_users
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_api_response_users
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_users()

        assert isinstance(result, list)
        assert len(result) == 1
        mock_client.get.assert_called_once_with("users")

    @patch("ingestion.api.extract.APIClient")
    def test_extract_carts_returns_list(
        self, mock_client_class, mock_api_response_carts
    ):
        mock_client = MagicMock()
        mock_client.get.return_value = mock_api_response_carts
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_carts()

        assert isinstance(result, list)
        assert len(result) == 1
        mock_client.get.assert_called_once_with("carts")

    @patch("ingestion.api.extract.APIClient")
    def test_extract_all_returns_all_entities(
        self,
        mock_client_class,
        mock_api_response_products,
        mock_api_response_users,
        mock_api_response_carts
    ):
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            mock_api_response_products,
            mock_api_response_users,
            mock_api_response_carts
        ]
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_all()

        assert "products" in result
        assert "users" in result
        assert "carts" in result
        assert len(result["products"]) == 2
        assert len(result["users"]) == 1
        assert len(result["carts"]) == 1

    @patch("ingestion.api.extract.APIClient")
    def test_extract_all_total_records(
        self,
        mock_client_class,
        mock_api_response_products,
        mock_api_response_users,
        mock_api_response_carts
    ):
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            mock_api_response_products,
            mock_api_response_users,
            mock_api_response_carts
        ]
        mock_client_class.return_value = mock_client

        extractor = FakeStoreExtractor()
        result = extractor.extract_all()

        total = sum(len(v) for v in result.values())
        assert total == 4