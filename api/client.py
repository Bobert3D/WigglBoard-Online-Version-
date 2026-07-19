import httpx

# Configuration
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "SuperSecretPassword123"

# Setup reusable basic authentication object
auth_credentials = httpx.BasicAuth(USERNAME, PASSWORD)

def run_integration_test():
    print("--- Starting Automated API Tests ---")
    
    with httpx.Client(base_url=BASE_URL) as client:
        # 1. Test POST Request (Adding a custom quote)
        quote_payload = {
            "quote_text": "Simplicity is the soul of efficiency.",
            "author_name": "Austin Freeman"
        }
        
        print("\n[POST] Adding a new quote...")
        post_response = client.post("/custom-quotes", json=quote_payload, auth=auth_credentials)
        
        if post_response.status_code == 200:
            print(f"Success! Server response: {post_response.json()}")
        else:
            print(f"Failed! Status: {post_response.status_code}, Body: {post_response.text}")

        # 2. Test GET Request (Fetching all quotes)
        print("\n[GET] Fetching user quotes list...")
        get_response = client.get("/custom-quotes", auth=auth_credentials)
        
        if get_response.status_code == 200:
            print("Success! Current quotes in database:")
            for index, quote in enumerate(get_response.json(), start=1):
                print(f" {index}. \"{quote['en']}\" — {quote['author']}")
        else:
            print(f"Failed! Status: {get_response.status_code}")

        # 3. Test Unauthorized Access (Security Verification)
        print("\n[SECURITY] Testing request WITHOUT credentials...")
        unauth_response = client.get("/custom-quotes")
        print(f"Result (Expected 401): {unauth_response.status_code} - {unauth_response.json().get('detail')}")

if __name__ == "__main__":
    # Ensure your uvicorn application is actively running on port 8000 before executing
    try:
        run_integration_test()
    except httpx.ConnectError:
        print("\nError: Could not connect to the server. Is your FastAPI app running on http://127.0.0.1:8000?")
