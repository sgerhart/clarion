#!/usr/bin/env python3
"""
Quick API Test

Tests the FastAPI endpoints (requires server to be running).
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, data=None, description=""):
    """Test an API endpoint."""
    url = f"{BASE_URL}{path}"
    print(f"\n{description or path}")
    print("-" * 60)
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            print(f"❌ Unknown method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        
        if response.status_code < 400:
            try:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"Response: {response.text[:200]}...")
            print("✅ PASSED")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            print("❌ FAILED")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the API server running?")
        print(f"   Start with: python scripts/run_api.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("CLARION API TEST")
    print("=" * 70)
    print(f"Testing API at: {BASE_URL}")
    print("\nMake sure the API server is running:")
    print("  python scripts/run_api.py")
    print()
    
    results = []
    
    # Health checks
    results.append(("GET", "/health", None, "Health Check"))
    results.append(("GET", "/health/detailed", None, "Detailed Health"))
    
    # Edge endpoints
    results.append(("GET", "/api/edge/sketches", None, "List Sketches"))
    results.append(("GET", "/api/edge/sketches/stats", None, "Sketch Statistics"))
    
    # Clustering (this will actually run clustering)
    print("\n⚠️  Note: Clustering endpoint will take ~10 seconds to run...")
    results.append(("POST", "/api/clustering/run", {
        "min_cluster_size": 50,
        "min_samples": 10,
    }, "Run Clustering"))
    
    # Policy endpoints
    results.append(("GET", "/api/policy/sgacls", None, "List SGACLs"))
    results.append(("GET", "/api/policy/matrix", None, "Get Policy Matrix"))
    
    # Visualization
    results.append(("GET", "/api/viz/clusters/distribution", None, "Cluster Distribution"))
    
    # Export
    results.append(("GET", "/api/export/json", None, "Export JSON"))
    
    passed = 0
    failed = 0
    
    for method, path, data, desc in results:
        if test_endpoint(method, path, data, desc):
            passed += 1
        else:
            failed += 1
            if "Connection failed" in str(sys.exc_info()):
                print("\n⚠️  Stopping tests - server not running")
                break
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    print("=" * 70)

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("❌ requests library not installed")
        print("   Install with: pip install requests")
        sys.exit(1)
    
    main()


