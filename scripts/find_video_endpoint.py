"""Find the correct video generation endpoint."""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_endpoints():
    """Try different endpoint variations."""

    # Possible endpoint variations
    endpoints_to_try = [
        "/api/v1/video/captioned",
        "/api/v1/video/generate",
        "/api/v1/video/create",
        "/api/v1/video/caption",
        "/api/v1/media/video/captioned",
        "/api/v1/media/video/generate",
        "/api/v1/media/video-tools/captioned",
        "/api/v1/media/video-tools/generate",
        "/video/captioned",
        "/video/generate",
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, try to get OpenAPI docs if available
        print("[1] Checking for OpenAPI documentation...")
        try:
            for doc_path in ["/openapi.json", "/docs", "/api/docs"]:
                try:
                    response = await client.get(f"{BASE_URL}{doc_path}")
                    if response.status_code == 200:
                        print(f"✅ Found docs at: {BASE_URL}{doc_path}")
                        if "json" in doc_path:
                            data = response.json()
                            # Look for video-related paths
                            if "paths" in data:
                                print("\n📋 Video-related endpoints found:")
                                for path, methods in data["paths"].items():
                                    if "video" in path.lower():
                                        print(f"  {path}")
                                        for method, details in methods.items():
                                            if method.upper() == "POST":
                                                print(f"    - {method.upper()}: {details.get('summary', 'No description')}")
                        return
                except:
                    pass
            print("❌ No OpenAPI docs found")
        except Exception as e:
            print(f"Error checking docs: {e}")

        # Try each endpoint
        print("\n[2] Testing endpoint variations with OPTIONS...")
        for endpoint in endpoints_to_try:
            try:
                # Try OPTIONS first to see if endpoint exists
                response = await client.options(f"{BASE_URL}{endpoint}")
                if response.status_code != 404:
                    print(f"✅ {endpoint} - Status: {response.status_code}")
                    if "Allow" in response.headers:
                        print(f"   Methods: {response.headers['Allow']}")
            except:
                pass

        print("\n[3] Checking available routes with GET...")
        for endpoint in endpoints_to_try:
            try:
                response = await client.get(f"{BASE_URL}{endpoint}")
                if response.status_code != 404:
                    print(f"✅ {endpoint} exists (GET status: {response.status_code})")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(test_endpoints())
