import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_api_response_products():
    return[
        {
            "id":           1,
            "title":        "Test Backpack",
            "price":        109.95,
            "category":     "men's clothing",
            "description":  "A test product",
            "image":        "https://fakestoreapi.com/img/test.jpg",
            "rating":       {"rate": 3.9, "count": 120}
        },
        {
            "id": 2,
            "title": "Test Jewellery",
            "price": 695.0,
            "category": "jewelery",
            "description": "Another test product",
            "image": "https://fakestoreapi.com/img/test2.jpg",
            "rating": {"rate": 4.1, "count": 400}
        }
    ]

@pytest.fixture
def mock_api_response_users():
    return [
        {
            "id": 1,
            "email": "john@example.com",
            "username": "johnd",
            "password": "m38rmF$",
            "name": {"firstname": "John", "lastname": "Doe"},
            "address": {
                "city": "Sydney",
                "street": "1 Test St",
                "number": 1,
                "zipcode": "2000",
                "geolocation": {"lat": "-33.8", "long": "151.2"}
            },
            "phone": "0412345678"
        }
    ]

@pytest.fixture
def mock_api_response_carts():
    return [
        {
            "id": 1,
            "userId": 1,
            "date": "2026-03-28T00:00:00.000Z",
            "products": [
                {"productId": 1, "quantity": 2},
                {"productId": 2, "quantity": 1}
            ]
        }
    ]

@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    return client

@pytest.fixture
def mock_settings():
    settings =                          MagicMock()
    settings.fakestore_base_url =       "https://fakestoreapi.com"
    settings.aws_bucket_name =          "test-bucket"
    settings.aws_access_key_id =        "fake-key"
    settings.aws_secret_access_key =    "fake-secret"
    settings.aws_region =               "ap-southeast-2"
    settings.log_level =                "INFO"
    return settings