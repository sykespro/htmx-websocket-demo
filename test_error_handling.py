#!/usr/bin/env python3
"""
Simple test script to verify error handling functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_sse_endpoint():
    """Test the SSE endpoint for basic functionality and error handling"""
    print("Testing SSE endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Basic SSE connection
            print("1. Testing basic SSE connection...")
            async with session.get('http://localhost:8000/sse-stream') as response:
                if response.status == 200:
                    print("✓ SSE endpoint is accessible")
                    
                    # Read a few events to verify streaming works
                    event_count = 0
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data:'):
                            event_count += 1
                            print(f"✓ Received SSE event {event_count}")
                            
                        if event_count >= 3:  # Test with 3 events
                            break
                    
                    print(f"✓ Successfully received {event_count} SSE events")
                else:
                    print(f"✗ SSE endpoint returned status {response.status}")
                    
    except aiohttp.ClientConnectorError:
        print("✗ Could not connect to server. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"✗ Error testing SSE endpoint: {e}")

async def test_health_endpoint():
    """Test the health check endpoint"""
    print("\n2. Testing health check endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/sse-health') as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("✓ Health endpoint is accessible")
                    print(f"✓ Active connections: {health_data.get('active_connections', 0)}")
                    
                    if 'connection_details' in health_data:
                        print("✓ Connection details available")
                    else:
                        print("✗ Connection details missing")
                else:
                    print(f"✗ Health endpoint returned status {response.status}")
                    
    except Exception as e:
        print(f"✗ Error testing health endpoint: {e}")

async def test_sse_demo_page():
    """Test that the SSE demo page loads correctly"""
    print("\n3. Testing SSE demo page...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/sse-demo') as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Check for key elements
                    checks = [
                        ('HTMX core library', 'htmx.org' in content),
                        ('SSE extension', 'sse.js' in content),
                        ('Alpine.js', 'alpinejs' in content),
                        ('Error handling UI', 'connectionStatus === \'error\'' in content),
                        ('Network monitoring', 'networkStatus' in content),
                        ('Reconnect functionality', 'reconnect()' in content),
                    ]
                    
                    for check_name, check_result in checks:
                        if check_result:
                            print(f"✓ {check_name} found")
                        else:
                            print(f"✗ {check_name} missing")
                            
                    print("✓ SSE demo page loads successfully")
                else:
                    print(f"✗ SSE demo page returned status {response.status}")
                    
    except Exception as e:
        print(f"✗ Error testing SSE demo page: {e}")

async def main():
    """Run all tests"""
    print("=== SSE Error Handling Test Suite ===")
    print(f"Test started at: {datetime.now()}")
    print()
    
    await test_sse_demo_page()
    await test_health_endpoint()
    await test_sse_endpoint()
    
    print("\n=== Test Summary ===")
    print("If all tests passed, the error handling implementation is working correctly.")
    print("To test error scenarios manually:")
    print("1. Start the server: uvicorn main:app --reload")
    print("2. Open http://localhost:8000/sse-demo")
    print("3. Try connecting/disconnecting to test error handling")
    print("4. Disconnect your network to test offline handling")

if __name__ == "__main__":
    asyncio.run(main())