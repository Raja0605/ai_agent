#!/usr/bin/env python3
"""Test script for JobSpy HTTP connection"""
import asyncio
import sys
import os
import httpx
sys.path.insert(0, '/app')

async def test_jobspy():
    print("Testing JobSpy HTTP connection...")
    
    # Test direct HTTP connection first
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("http://jobspy_mcp:8500/health")
            print(f"Direct HTTP health check: {response.status_code}")
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Direct HTTP failed: {e}")
    
    # Now test through service
    from app.services.jobspy_service import JobSpyService
    service = JobSpyService()
    
    try:
        health = await service.health()
        print(f"Service health check result: {health}")
        
        if health.get("status") == "connected":
            print("✓ JobSpy HTTP is connected")
            
            # Try to discover tools
            tools = await service.tools()
            print(f"Available tools: {len(tools.get('tools', []))}")
            print(f"Job search tool: {tools.get('job_search_tool')}")
            print(f"Sites: {tools.get('sites', [])}")
        else:
            print("✗ JobSpy HTTP is not connected")
            
    except Exception as e:
        print(f"✗ Error testing JobSpy service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_jobspy())
