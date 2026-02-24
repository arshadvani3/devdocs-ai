"""
WebSocket endpoint for streaming chat responses.

This module provides a WebSocket endpoint that enables real-time
streaming of LLM responses for a better user experience.
"""

import logging
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.services.retrieval import get_vector_store
from app.services.llm import get_ollama_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat.

    Protocol:
        Client sends: {
            "question": "How does authentication work?",
            "collection_name": "my_collection",  # Optional
            "top_k": 5  # Optional
        }

        Server streams: {
            "type": "token",
            "content": "word"
        }

        Server ends with: {
            "type": "sources",
            "data": [
                {
                    "file_path": "src/auth.py",
                    "start_line": 10,
                    "end_line": 20,
                    "text_snippet": "def authenticate...",
                    "relevance_score": 0.95
                },
                ...
            ]
        }

        On error: {
            "type": "error",
            "message": "Error description"
        }

    Args:
        websocket: WebSocket connection
    """
    # Accept the connection
    try:
        await websocket.accept()
        logger.info("✓ WebSocket connection accepted successfully")
        logger.info(f"  Client: {websocket.client}")
        logger.info(f"  Headers: {dict(websocket.headers)}")
    except Exception as e:
        logger.error(f"✗ Failed to accept WebSocket connection: {e}")
        return

    try:
        # Wait for incoming message
        while True:
            # Receive JSON message from client
            logger.debug("Waiting for message from client...")
            data = await websocket.receive_text()
            logger.debug(f"Received raw data: {data[:100]}...")

            try:
                request = json.loads(data)
                question = request.get("question")
                collection_name = request.get("collection_name")
                top_k = request.get("top_k") or settings.retrieval_top_k

                if not question:
                    logger.warning("Received request without question field")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing 'question' field in request"
                    })
                    continue

                logger.info(f"📨 Received WebSocket query: '{question}'")

                # Get services
                vector_store = get_vector_store(collection_name)
                ollama_service = get_ollama_service()

                # Retrieve relevant chunks
                logger.info(f"Retrieving top {top_k} relevant chunks")
                search_results = await vector_store.search(
                    query=question,
                    top_k=top_k,
                )

                if not search_results:
                    logger.warning("No relevant documents found for query")
                    await websocket.send_json({
                        "type": "token",
                        "content": "I couldn't find any relevant information in the codebase to answer your question. "
                                   "Please try rephrasing or ensure documents have been ingested."
                    })
                    await websocket.send_json({
                        "type": "sources",
                        "data": []
                    })
                    continue

                # Extract chunks for context
                chunks = [chunk for chunk, score in search_results]
                logger.info(f"Found {len(chunks)} chunks to use as context")

                # Stream the response token by token
                logger.info("🚀 Starting streaming response from LLM")
                token_count = 0

                try:
                    async for token in ollama_service.generate_with_context_streaming(
                        question=question,
                        context_chunks=chunks,
                    ):
                        token_count += 1

                        # Log every 10th token to avoid spam
                        if token_count % 10 == 0:
                            logger.debug(f"  Streamed {token_count} tokens so far...")

                        # Send each token as it arrives
                        try:
                            message = {
                                "type": "token",
                                "content": token
                            }
                            logger.debug(f"📤 Sending token #{token_count}: {repr(token[:20])}")
                            await websocket.send_json(message)

                            # Small delay to prevent overwhelming the connection
                            await asyncio.sleep(0.01)

                        except Exception as send_error:
                            logger.error(f"✗ Error sending token #{token_count}: {send_error}")
                            raise

                    logger.info(f"✓ Streaming complete! Sent {token_count} tokens total")

                except Exception as stream_error:
                    logger.error(f"✗ Error during streaming: {stream_error}", exc_info=True)
                    raise

                # After streaming completes, send sources
                logger.info("📚 Preparing sources...")
                citations = vector_store.format_as_citations(search_results)

                logger.info(f"📤 Sending {len(citations)} source citations")
                try:
                    await websocket.send_json({
                        "type": "sources",
                        "data": [citation.model_dump() for citation in citations]
                    })
                    logger.info(f"✓ Query complete: {len(citations)} sources sent successfully")
                except Exception as send_error:
                    logger.error(f"✗ Error sending sources: {send_error}")
                    raise

            except json.JSONDecodeError as json_error:
                logger.error(f"✗ Received invalid JSON: {json_error}")
                logger.error(f"  Raw data: {data[:200]}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                except:
                    logger.error("Failed to send error message back to client")

            except Exception as e:
                logger.error(f"✗ Error processing WebSocket message: {e}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing query: {str(e)}"
                    })
                except:
                    logger.error("Failed to send error message back to client")

    except WebSocketDisconnect as disconnect:
        logger.info(f"🔌 WebSocket client disconnected (code: {disconnect.code})")
    except Exception as e:
        logger.error(f"✗ Unexpected WebSocket error: {e}", exc_info=True)
    finally:
        logger.info("🔚 WebSocket connection closed")
