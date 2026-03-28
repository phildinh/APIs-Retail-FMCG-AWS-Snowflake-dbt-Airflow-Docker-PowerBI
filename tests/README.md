# tests

pytest test suite covering the Python ingestion layer.
These tests verify that data extraction and S3 loading
behave correctly without making real API calls or writing
to real AWS infrastructure.

---

## What we test vs what dbt tests

There are two separate quality gates in this project:

| Layer | Tool | What it tests |
|---|---|---|
| Python ingestion | pytest (this folder) | API response shape, S3 write behaviour, retry logic |
| Snowflake transforms | dbt test | Nulls, uniqueness, referential integrity, accepted values |

pytest runs in Python and never touches Snowflake.
dbt test runs inside Snowflake and never touches Python.
They are completely independent.

---

## Files

### conftest.py
Shared fixtures available to every test file automatically.
pytest loads this file before any tests run.

Fixtures provided:
- `mock_api_response_products` — 2 fake product records
- `mock_api_response_users`    — 1 fake user record
- `mock_api_response_carts`    — 1 fake cart record
- `mock_s3_client`             — fake boto3 S3 client
- `mock_settings`              — fake Settings object

No imports needed in test files — pytest injects fixtures
automatically when a test function names them as parameters.

---

### test_extract.py
Tests for `ingestion/api/extract.py` — the FakeStoreExtractor class.

| Test | What it verifies |
|---|---|
| `test_extract_products_returns_list` | products returns a list |
| `test_extract_products_record_shape` | each product has required fields |
| `test_extract_users_returns_list` | users returns a list |
| `test_extract_carts_returns_list` | carts returns a list |
| `test_extract_all_returns_all_entities` | all three entities present in result |
| `test_extract_all_total_records` | total record count is correct |

APIClient is mocked in every test — no real HTTP calls are made.

---

### test_load.py
Tests for `ingestion/storage/load.py` — the load_to_s3 function.

| Test | What it verifies |
|---|---|
| `test_load_returns_s3_key` | function returns a string S3 key |
| `test_load_calls_put_object` | S3 put_object is called |
| `test_load_uses_correct_bucket` | correct bucket name is used |
| `test_load_key_contains_entity_name` | entity name appears in S3 key |
| `test_load_content_type_is_json` | ContentType is application/json |
| `test_load_empty_data_still_writes` | empty list still writes to S3 |
| `test_load_key_contains_entity_for_all_entities` | works for products, users, carts |

get_settings and get_s3_client are mocked — no real AWS calls are made.

---

## How to run

Make sure your virtual environment is active.
```powershell
# activate venv
.\venv\Scripts\activate

# run all tests
pytest tests/ -v

# run a specific file
pytest tests/test_extract.py -v
pytest tests/test_load.py -v

# run a specific test
pytest tests/test_extract.py::TestFakeStoreExtractor::test_extract_products_returns_list -v
```

Expected output:
```
tests/test_extract.py::TestFakeStoreExtractor::test_extract_products_returns_list PASSED
tests/test_extract.py::TestFakeStoreExtractor::test_extract_products_record_shape PASSED
tests/test_extract.py::TestFakeStoreExtractor::test_extract_users_returns_list PASSED
tests/test_extract.py::TestFakeStoreExtractor::test_extract_carts_returns_list PASSED
tests/test_extract.py::TestFakeStoreExtractor::test_extract_all_returns_all_entities PASSED
tests/test_extract.py::TestFakeStoreExtractor::test_extract_all_total_records PASSED
tests/test_load.py::TestLoadToS3::test_load_returns_s3_key PASSED
tests/test_load.py::TestLoadToS3::test_load_calls_put_object PASSED
tests/test_load.py::TestLoadToS3::test_load_uses_correct_bucket PASSED
tests/test_load.py::TestLoadToS3::test_load_key_contains_entity_name PASSED
tests/test_load.py::TestLoadToS3::test_load_content_type_is_json PASSED
tests/test_load.py::TestLoadToS3::test_load_empty_data_still_writes PASSED
tests/test_load.py::TestLoadToS3::test_load_key_contains_entity_for_all_entities[products] PASSED
tests/test_load.py::TestLoadToS3::test_load_key_contains_entity_for_all_entities[users] PASSED
tests/test_load.py::TestLoadToS3::test_load_key_contains_entity_for_all_entities[carts] PASSED
```

---

## Key concepts

### Mocking
Tests never make real API calls or write to real S3.
Real dependencies are replaced with MagicMock objects
that return controlled, predictable data.

### Fixtures
Shared setup objects defined in conftest.py and injected
automatically by pytest. Avoids repeating setup code
across multiple test files.

### Parametrize
`@pytest.mark.parametrize` runs the same test multiple
times with different inputs. Used in
`test_load_key_contains_entity_for_all_entities` to verify
all three entities without duplicating test code.

### assert_called_once_with
Verifies not just what a function returned but how it
was called — which arguments were passed. Catches bugs
like wrong endpoint names or missing parameters.