# ingestion/api

Handles all outbound HTTP concerns for the ingestion layer.
Responsible for making reliable API requests and extracting
raw data from FakeStoreAPI. Nothing in this folder knows
about S3, Snowflake, or any storage concern.

---

## Files

### api_client.py
Generic HTTP client built on `requests.Session` with
tenacity retry logic.

Handles all low-level HTTP concerns — connection reuse,
timeouts, status code validation, and automatic retries
with exponential backoff. Completely generic — knows nothing
about specific endpoints or business entities.

Retry behaviour:
- Maximum attempts: 3
- Backoff: exponential (2s → 4s → 8s, capped at 10s)
- Retries on: network errors and timeouts only
- Does not retry: 4xx and 5xx responses (not transient)

Usage:
    from ingestion.api.api_client import APIClient

    client = APIClient()
    data = client.get("products")

---

### extract.py
Business-specific extractor for FakeStoreAPI endpoints.

Wraps `APIClient` with named methods for each entity.
Knows the specific endpoints, logs extraction counts,
and provides `extract_all()` to run all entities in
one call. Returns plain Python dictionaries — no
transformation applied here.

Entities extracted:
- products  → /products
- users     → /users
- carts     → /carts

Usage:
    from ingestion.api.extract import FakeStoreExtractor

    extractor = FakeStoreExtractor()

    # extract one entity
    products = extractor.extract_products()

    # extract all entities in one call
    results = extractor.extract_all()
    # returns:
    # {
    #     "products": [{...}, {...}],
    #     "users":    [{...}, {...}],
    #     "carts":    [{...}, {...}]
    # }

---

## Design decisions

**Why split api_client.py and extract.py?**
`api_client.py` is generic — it knows how to make a reliable
HTTP request to any endpoint. `extract.py` is business-specific
— it knows FakeStoreAPI's endpoints and entity shapes.

Keeping them separate means:
- Adding a new endpoint only touches extract.py
- Swapping the API source only touches extract.py
- Retry and session logic is defined once in api_client.py

**Why exponential backoff instead of fixed wait?**
If an API is struggling under load, retrying immediately
makes the problem worse. Exponential backoff gives the
server time to recover between attempts. Industry standard
for any production HTTP client.

**Why retry on RequestException only?**
Network errors and timeouts are transient — retrying may
succeed. A 404 or 401 response is not transient — the
request is fundamentally wrong and retrying will never
fix it. Retrying non-transient errors wastes time and
masks real problems.

**Why use requests.Session?**
A session reuses the underlying TCP connection across
multiple requests. Calling three endpoints without a
session opens and closes three separate connections.
With a session, all three share one connection — faster
and more efficient.
