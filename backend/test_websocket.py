#!/usr/bin/env python3
"""
WebSocket test script for DevDocs AI.
Tests WebSocket streaming connection and token reception.
"""

import asyncio
import json
import websockets


async def test_websocket():
    """Test WebSocket streaming."""
    uri = "ws://localhost:8000/api/v1/stream"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected!")

            # Send a test question
            question = {
                "question": "What is this codebase about?",
                "top_k": 3
            }

            print(f"\nSending question: {question['question']}")
            await websocket.send(json.dumps(question))
            print("✓ Question sent!")

            print("\nReceiving response:")
            print("-" * 60)

            token_count = 0
            full_response = ""

            # Receive messages
            async for message in websocket:
                data = json.loads(message)

                if data["type"] == "token":
                    token_count += 1
                    content = data["content"]
                    full_response += content
                    print(content, end='', flush=True)

                elif data["type"] == "sources":
                    sources = data["data"]
                    print(f"\n\n✓ Received {len(sources)} sources")
                    for i, source in enumerate(sources, 1):
                        print(f"\n{i}. {source['file_path']} (lines {source['start_line']}-{source['end_line']})")
                        print(f"   Relevance: {source['relevance_score']:.2f}")
                    break

                elif data["type"] == "error":
                    print(f"\n✗ Error: {data['message']}")
                    break

            print("-" * 60)
            print(f"\n✓ Test complete!")
            print(f"  Tokens received: {token_count}")
            print(f"  Response length: {len(full_response)} chars")

    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("DevDocs AI WebSocket Test")
    print("=" * 60)

    # Install websockets if not available
    try:
        import websockets
    except ImportError:
        print("Installing websockets library...")
        import subprocess
        subprocess.check_call(["pip", "install", "websockets"])
        import websockets

    asyncio.run(test_websocket())
