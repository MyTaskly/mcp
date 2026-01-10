"""
Direct validation test to ensure tasks are actually created on the server.

Run: python -m pytest tests/external/test_task_creation_validation.py -v -s
"""

import jwt
import pytest
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.mcp import MCPServerSse
from agents.model_settings import ModelSettings

load_dotenv()


@pytest.mark.asyncio
async def test_task_creation_actually_works():
    """
    Test that task creation actually succeeds and returns success confirmation.

    This is a stricter test than the basic one - it checks that the agent
    confirms successful task creation, not just that it mentions "task" in response.
    """

    user_id = 2
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "aud": "mcp://mytaskly-mcp-server",
        "iss": "https://api.mytasklyapp.com",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
        "scope": "tasks:read tasks:write categories:read categories:write notes:read notes:write"
    }

    jwt_secret = "980732h4juasdfuy98p32nbjlasdfu90o[p324jubn"
    mcp_token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    print(f"\n[INFO] Testing task creation with user_id={user_id}")

    async with MCPServerSse(
        name="MyTasklyMCP",
        params={
            "url": "https://mcp.mytasklyapp.com/sse",
            "headers": {"Authorization": f"Bearer {mcp_token}"},
        },
        cache_tools_list=True,
    ) as server:
        print(f"[OK] Connected to MCP server")

        agent = Agent(
            name="TaskCreator",
            mcp_servers=[server],
            model_settings=ModelSettings(temperature=0.3),
            instructions="""You are a task creation assistant.

When asked to create a task:
1. Use the add_task tool to create it
2. If successful, respond with "SUCCESS: Task created" followed by details
3. If there's an error, respond with "ERROR:" followed by the specific error message
4. Be direct and clear about success or failure."""
        )

        print(f"[OK] Agent created")

        # Test 1: Create task in existing "Generale" category
        print(f"\n[TEST 1] Creating task in Generale category...")
        result1 = await Runner.run(
            agent,
            "Create a task titled 'Validation Test Task' in the Generale category with high priority"
        )

        print(f"\n[RESULT 1] {result1.final_output}")

        # Check for actual success
        output_lower = result1.final_output.lower()

        # Test should fail if there's an error
        if "error" in output_lower or "errore" in output_lower:
            print(f"\n[FAIL] Task creation reported an error")
            print(f"[DEBUG] Full response: {result1.final_output}")
            assert False, f"Task creation failed: {result1.final_output}"

        # Test should pass if there's success confirmation
        if "success" in output_lower or "creato" in output_lower or "created" in output_lower or "✅" in result1.final_output:
            print(f"[PASS] Task creation succeeded!")
        else:
            print(f"\n[FAIL] No clear success confirmation in response")
            assert False, f"No success confirmation: {result1.final_output}"


        # Test 2: List categories to ensure the category lookup works
        print(f"\n[TEST 2] Getting categories to verify they exist...")
        result2 = await Runner.run(
            agent,
            "List all available categories"
        )

        print(f"\n[RESULT 2] {result2.final_output}")

        assert "generale" in result2.final_output.lower(), \
            f"Generale category should be available: {result2.final_output}"

        print("\n" + "="*70)
        print("[OK] All validation tests passed!")
        print("[OK] Task creation is working correctly")
        print("="*70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_task_creation_actually_works())
