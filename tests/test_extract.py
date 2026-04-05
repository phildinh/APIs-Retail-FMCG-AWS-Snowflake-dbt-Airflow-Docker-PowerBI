import pytest
from ingestion.api.extract import FakeStoreExtractor
from ingestion.mock_data import PRODUCTS, USERS, CARTS


class TestFakeStoreExtractor:

    def test_extract_products_returns_list(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_products()

        assert isinstance(result, list)
        assert len(result) == len(PRODUCTS)

    def test_extract_products_record_shape(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_products()

        first = result[0]
        assert "id" in first
        assert "title" in first
        assert "price" in first
        assert "category" in first
        assert "rating" in first

    def test_extract_users_returns_list(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_users()

        assert isinstance(result, list)
        assert len(result) == len(USERS)

    def test_extract_carts_returns_list(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_carts()

        assert isinstance(result, list)
        assert len(result) == len(CARTS)

    def test_extract_all_returns_all_entities(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_all()

        assert "products" in result
        assert "users" in result
        assert "carts" in result
        assert len(result["products"]) == len(PRODUCTS)
        assert len(result["users"]) == len(USERS)
        assert len(result["carts"]) == len(CARTS)

    def test_extract_all_total_records(self):
        extractor = FakeStoreExtractor()
        result = extractor.extract_all()

        total = sum(len(v) for v in result.values())
        assert total == len(PRODUCTS) + len(USERS) + len(CARTS)