## Quick Start

```python
import redis
import numpy as np
from lsh_tokenization import LSHIndexer, LSHConfig
from lsh_tokenization.utils.security import SecurityUtils

# Setup Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Generate HMAC key (32 bytes)
hmac_key = SecurityUtils.generate_hmac_key()

# Initialize
indexer = LSHIndexer(redis_client, hmac_key)

# Add 256-bit image hash
binary_hash = np.random.randint(0, 2, 256, dtype=np.uint8)
indexer.add(
    binary_hash=binary_hash,
    tenant_id="tenant_1",
    hash_id="hash_abc123"  # ← Simple hash ID
)

# Query for similar hashes
query_hash = binary_hash
candidates = indexer.query(query_hash, tenant_id="tenant_1")

# Results: Simple list of hash IDs
print(candidates)
# Output: ['hash_abc123', 'hash_xyz789', ...]
Redis Storage Schema
Simple and Efficient:

text
HMAC_Token_1 → ["hash_001", "hash_002", "hash_003"]
HMAC_Token_2 → ["hash_004", "hash_001", "hash_005"]
HMAC_Token_3 → ["hash_002", "hash_006"]
...
Each token is an HMAC-SHA3-256 hash that maps to a list of hash IDs.

API Reference
LSHIndexer
add(binary_hash, tenant_id, hash_id)

Add 256-bit binary hash to index

Stores hash_id under 6 HMAC tokens

Returns: bool - Success status

query(binary_hash, tenant_id, deduplicate=True)

Query for candidate hash_ids

Returns: List[str] - List of hash IDs

delete_hash(binary_hash, tenant_id, hash_id)

Remove hash_id from all buckets

Returns: int - Number of occurrences removed

add_batch(entries)

Add multiple hashes efficiently

Each entry needs: binary_hash, tenant_id, hash_id

Returns: Dict - Statistics


***
