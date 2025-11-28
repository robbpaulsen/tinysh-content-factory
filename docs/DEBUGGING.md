# Debugging Guide - TTS Endpoint Issue

## Current Problem

The TTS endpoints return 404 when called via httpx, but work perfectly with curl.

## Evidence

### ✅ What Works (curl)

```bash
# Chatterbox TTS
curl -X POST http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox \
  -F "text=test"

# Response:
{"file_id":"audio_7c8c6107-bb4e-44d0-aa61-9deb97c4f4ef.wav"}

# Kokoro TTS
curl -X POST http://localhost:8000/api/v1/media/audio-tools/tts/kokoro \
  -F "text=test" \
  -F "voice=af_bella"

# Response:
{"file_id":"audio_8cd26b8a-0a46-40bb-8879-b8475deb9241.wav"}
```

### ❌ What Fails (httpx in Python)

```python
# Current code in src/services/media.py:154-192
async def generate_tts_direct(self, text: str) -> str:
    endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/chatterbox"
    payload = {"text": text, ...}
    response = await self.client.post(endpoint, data=payload, timeout=120.0)
    # httpx.HTTPStatusError: Client error '404 Not Found'
```

## Investigation Steps

### 1. Check Exact URL Being Called

Add debug logging:

```python
# In src/services/media.py, add before the request:
logger.debug(f"Full URL: {endpoint}")
logger.debug(f"Base URL: {self.base_url}")
logger.debug(f"Payload: {payload}")
```

### 2. Compare HTTP Headers

**curl sends**:
```
Content-Type: multipart/form-data; boundary=------------------------bb0sWuPxqKy8afZcHAdhFD
```

**httpx sends** (when using `data=`):
```python
# Unknown - need to check
```

**Test**: Print httpx request headers:
```python
response = await self.client.post(endpoint, data=payload, timeout=120.0)
print(f"Request headers: {response.request.headers}")
```

### 3. Test with Different httpx Parameters

Try these variations:

```python
# Option 1: Explicit files parameter (multipart/form-data)
response = await self.client.post(
    endpoint,
    files={"text": (None, text), "voice": (None, "af_bella")}
)

# Option 2: Data parameter with explicit Content-Type
response = await self.client.post(
    endpoint,
    data=payload,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

# Option 3: JSON parameter
response = await self.client.post(endpoint, json=payload)

# Option 4: httpx.Client with different settings
client = httpx.AsyncClient(
    timeout=120.0,
    follow_redirects=True,
    base_url=self.base_url
)
response = await client.post("/api/v1/media/audio-tools/tts/chatterbox", data=payload)
```

### 4. Check Base URL Construction

```python
# In __init__:
self.base_url = (base_url or settings.media_server_url).rstrip("/")
# This should give: "http://192.168.68.60:8000"

# When building endpoint:
endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/chatterbox"
# This should give: "http://192.168.68.60:8000/api/v1/media/audio-tools/tts/chatterbox"

# Double check no double slashes or missing slashes
```

### 5. Test Direct httpx Request (Outside Class)

Create `test_tts.py`:

```python
import asyncio
import httpx

async def test_tts():
    client = httpx.AsyncClient()

    # Test 1: Exact curl equivalent
    data = {"text": "test"}
    response = await client.post(
        "http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox",
        data=data
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    await client.aclose()

asyncio.run(test_tts())
```

Run: `uv run python test_tts.py`

### 6. Check Media Server Logs

When the httpx request is made, check the media server logs to see:
- Is the request arriving at all?
- What path is it hitting?
- What error is the server returning?

### 7. Network Capture

Use Wireshark or tcpdump to compare:
- curl request packet
- httpx request packet

Look for differences in:
- HTTP method
- Path
- Headers
- Body encoding

## Hypotheses

### Hypothesis 1: Content-Type Mismatch
**Theory**: httpx `data=` might not be sending `multipart/form-data`

**Test**:
```python
# Try with files parameter instead
response = await self.client.post(
    endpoint,
    files={"text": (None, text)}
)
```

### Hypothesis 2: URL Construction Issue
**Theory**: Double slash or missing slash in URL

**Test**:
```python
# Print the exact URL
print(f"URL: {endpoint}")
# Should be: http://192.168.68.60:8000/api/v1/media/audio-tools/tts/chatterbox
# Not: http://192.168.68.60:8000//api/v1/... or http://192.168.68.60:8000api/v1/...
```

### Hypothesis 3: Base URL vs Full URL
**Theory**: httpx.AsyncClient might handle base_url differently

**Test**:
```python
# Instead of building full URL, use relative path
client = httpx.AsyncClient(base_url="http://localhost:8000")
response = await client.post("/api/v1/media/audio-tools/tts/chatterbox", data=payload)
```

### Hypothesis 4: IP vs localhost
**Theory**: Using IP (192.168.68.60) vs localhost might matter

**Test**:
```python
# Try with localhost instead
endpoint = "http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox"
```

### Hypothesis 5: httpx Client Configuration
**Theory**: httpx client needs specific settings

**Test**:
```python
# In __init__, modify client creation:
self.client = httpx.AsyncClient(
    timeout=settings.http_timeout,
    follow_redirects=True,  # Add this
    http2=False,  # Disable HTTP/2
)
```

## Quick Debug Script

Create `debug_tts.py`:

```python
import asyncio
import httpx
from src.config import settings

async def debug():
    # Test 1: Exact curl equivalent
    print("Test 1: Basic httpx with data=")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox",
                data={"text": "test"}
            )
            print(f"  ✅ Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test 2: With files parameter
    print("\nTest 2: Using files=")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox",
                files={"text": (None, "test")}
            )
            print(f"  ✅ Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test 3: Using configured URL
    print(f"\nTest 3: Using settings URL: {settings.media_server_url}")
    async with httpx.AsyncClient() as client:
        try:
            base = settings.media_server_url.rstrip("/")
            url = f"{base}/api/v1/media/audio-tools/tts/chatterbox"
            print(f"  Full URL: {url}")
            response = await client.post(url, data={"text": "test"})
            print(f"  ✅ Status: {response.status_code}")
            print(f"  Response: {response.json()}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test 4: Check request details
    print("\nTest 4: Request inspection")
    async with httpx.AsyncClient() as client:
        request = client.build_request(
            "POST",
            "http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox",
            data={"text": "test"}
        )
        print(f"  URL: {request.url}")
        print(f"  Headers: {dict(request.headers)}")
        print(f"  Body: {request.content}")

asyncio.run(debug())
```

Run: `uv run python debug_tts.py`

## Expected vs Actual

### Expected (curl)
```http
POST /api/v1/media/audio-tools/tts/chatterbox HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=------------------------bb0sWuPxqKy8afZcHAdhFD

--------------------------bb0sWuPxqKy8afZcHAdhFD
Content-Disposition: form-data; name="text"

test
--------------------------bb0sWuPxqKy8afZcHAdhFD--
```

### Actual (httpx with data=)
```http
POST /api/v1/media/audio-tools/tts/chatterbox HTTP/1.1
Host: ???
Content-Type: ???

???
```

**TODO**: Capture actual httpx request to compare.

## Resolution Checklist

- [ ] Identified exact URL being called by httpx
- [ ] Compared httpx headers vs curl headers
- [ ] Tested with `files=` parameter
- [ ] Tested with explicit Content-Type
- [ ] Checked for URL construction issues
- [ ] Tested with localhost vs IP address
- [ ] Checked media server logs
- [ ] Found working httpx configuration
- [ ] Updated code with fix
- [ ] Tested TTS generation successfully
- [ ] Documented solution in CHANGELOG.md

## Notes

- Media server is confirmed running and accessible
- Endpoints exist in OpenAPI schema
- curl works perfectly (proves server is fine)
- Issue is with httpx client configuration or request format
- Similar issue might affect video generation endpoints
