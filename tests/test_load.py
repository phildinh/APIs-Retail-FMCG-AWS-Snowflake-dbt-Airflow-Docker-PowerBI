import pytest
from unittest.mock import patch, MagicMock
from ingestion.storage.load import load_to_s3


class TestLoadToS3:

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_returns_s3_key(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        mock_api_response_products
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        result = load_to_s3(
            entity="products",
            data=mock_api_response_products
        )

        assert isinstance(result, str)
        assert result.startswith("raw/products/")
        assert result.endswith(".json")

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_calls_put_object(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        mock_api_response_products
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        load_to_s3(
            entity="products",
            data=mock_api_response_products
        )

        mock_s3_client.put_object.assert_called_once()

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_uses_correct_bucket(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        mock_api_response_products
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        load_to_s3(
            entity="products",
            data=mock_api_response_products
        )

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_key_contains_entity_name(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        mock_api_response_products
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        load_to_s3(
            entity="products",
            data=mock_api_response_products
        )

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert "products" in call_kwargs["Key"]

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_content_type_is_json(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        mock_api_response_products
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        load_to_s3(
            entity="products",
            data=mock_api_response_products
        )

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["ContentType"] == "application/json"

    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_empty_data_still_writes(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        result = load_to_s3(
            entity="products",
            data=[]
        )

        mock_s3_client.put_object.assert_called_once()
        assert isinstance(result, str)

    @pytest.mark.parametrize("entity", ["products", "users", "carts"])
    @patch("ingestion.storage.load.get_s3_client")
    @patch("ingestion.storage.load.get_settings")
    def test_load_key_contains_entity_for_all_entities(
        self,
        mock_get_settings,
        mock_get_s3_client,
        mock_settings,
        mock_s3_client,
        entity
    ):
        mock_get_settings.return_value = mock_settings
        mock_get_s3_client.return_value = mock_s3_client

        result = load_to_s3(entity=entity, data=[{"id": 1}])

        assert entity in result