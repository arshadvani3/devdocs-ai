"""
LLM service for interacting with Ollama.

This module handles communication with the Ollama API for
generating responses using local LLMs.
"""

import logging
import json
from typing import List, Optional, Dict, Any, AsyncGenerator
import httpx
from httpx import Timeout
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.config import settings
from app.models import DocumentChunk

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service for interacting with Ollama API.

    This class handles making requests to the Ollama API to generate
    responses using local LLM models.

    Attributes:
        base_url: Base URL for Ollama API
        model: Model name to use (e.g., 'llama3.1:8b')
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize Ollama service.

        Args:
            base_url: Ollama API base URL (defaults to config)
            model: Model name (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

        # Ensure base_url doesn't end with /
        self.base_url = self.base_url.rstrip("/")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response from the LLM with automatic retry on transient errors.

        Retries up to 3 times on connection errors or timeouts with exponential backoff.

        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate (None = model default)

        Returns:
            Generated text response

        Raises:
            httpx.HTTPError: If the request fails
            Exception: If Ollama is not running or model is not available
        """
        try:
            url = f"{self.base_url}/api/generate"

            # Build the request payload
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # For Phase 1, no streaming
                "options": {
                    "temperature": temperature,
                }
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add max_tokens if specified
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            logger.info(f"Generating response with {self.model}")
            logger.debug(f"Prompt length: {len(prompt)} chars")

            # Make async request to Ollama
            async with httpx.AsyncClient(timeout=Timeout(self.timeout)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                generated_text = result.get("response", "")

                logger.info(
                    f"Generated response: {len(generated_text)} chars, "
                    f"took {result.get('total_duration', 0) / 1e9:.2f}s"
                )

                return generated_text

        except httpx.ConnectError as e:
            logger.error(f"Could not connect to Ollama at {self.base_url}: {e}")
            raise Exception(
                f"Ollama is not running or not accessible at {self.base_url}. "
                "Please start Ollama with 'ollama serve'"
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Model {self.model} not found")
                raise Exception(
                    f"Model '{self.model}' not found. "
                    f"Please pull it with 'ollama pull {self.model}'"
                ) from e
            logger.error(f"HTTP error from Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM with automatic retry.

        Streams tokens as they are generated using Ollama's streaming API.
        Each token is yielded as soon as it's available.
        Retries up to 3 times on connection errors or timeouts with exponential backoff.

        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate (None = model default)

        Yields:
            Generated text tokens

        Raises:
            httpx.HTTPError: If the request fails
            Exception: If Ollama is not running or model is not available
        """
        try:
            url = f"{self.base_url}/api/generate"

            # Build the request payload
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,  # Enable streaming
                "options": {
                    "temperature": temperature,
                }
            }

            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt

            # Add max_tokens if specified
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            logger.info(f"🤖 Starting streaming generation with {self.model}")
            logger.debug(f"   Prompt length: {len(prompt)} chars")

            # Make async streaming request to Ollama
            async with httpx.AsyncClient(timeout=Timeout(self.timeout)) as client:
                logger.debug(f"   Making streaming POST to {url}")
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    logger.info(f"✓ Ollama streaming connection established (status {response.status_code})")

                    token_count = 0
                    # Process NDJSON stream (one JSON object per line)
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)

                                # Yield the response token if present
                                if "response" in chunk:
                                    token = chunk["response"]
                                    if token:  # Only yield non-empty tokens
                                        token_count += 1
                                        if token_count <= 3 or token_count % 20 == 0:
                                            logger.debug(f"   Token #{token_count}: {repr(token[:20])}")
                                        yield token

                                # Check if done
                                if chunk.get("done", False):
                                    logger.info(f"✓ Streaming generation complete ({token_count} tokens)")
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse JSON line: {line[:50]}")
                                continue

        except httpx.ConnectError as e:
            logger.error(f"Could not connect to Ollama at {self.base_url}: {e}")
            raise Exception(
                f"Ollama is not running or not accessible at {self.base_url}. "
                "Please start Ollama with 'ollama serve'"
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Model {self.model} not found")
                raise Exception(
                    f"Model '{self.model}' not found. "
                    f"Please pull it with 'ollama pull {self.model}'"
                ) from e
            logger.error(f"HTTP error from Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during streaming generation: {e}")
            raise

    async def generate_with_context(
        self,
        question: str,
        context_chunks: List[DocumentChunk],
        max_context_length: Optional[int] = None,
    ) -> str:
        """
        Generate a response using RAG (Retrieval-Augmented Generation).

        This method takes the user's question and relevant context chunks,
        formats them into a prompt, and generates an answer.

        Args:
            question: User's question
            context_chunks: Relevant document chunks retrieved from vector DB
            max_context_length: Maximum characters for context (defaults to config)

        Returns:
            Generated answer

        Example:
            >>> service = OllamaService()
            >>> chunks = [...]  # Retrieved from vector DB
            >>> answer = await service.generate_with_context(
            ...     "How does auth work?",
            ...     chunks
            ... )
        """
        max_context = max_context_length or settings.rag_context_window

        # Build context from chunks
        context_parts = []
        total_length = 0

        for chunk in context_chunks:
            chunk_text = (
                f"File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n"
                f"```{chunk.language}\n{chunk.text}\n```\n"
            )

            # Check if adding this chunk would exceed limit
            if total_length + len(chunk_text) > max_context:
                logger.info(
                    f"Reached context limit ({max_context} chars), "
                    f"using {len(context_parts)} of {len(context_chunks)} chunks"
                )
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        context = "\n\n".join(context_parts)

        # Create the RAG prompt
        prompt = f"""Use the following code snippets to answer the question. If the answer cannot be found in the provided context, say so.

Context:
{context}

Question: {question}

Answer:"""

        # System prompt to guide the model
        system_prompt = """You are a helpful AI assistant that answers questions about code.
You provide clear, accurate answers based on the provided code snippets.
Always cite the specific files and line numbers when referencing code.
If you're not sure about something, say so rather than making assumptions."""

        logger.info(
            f"Generating RAG response with {len(context_parts)} context chunks "
            f"({total_length} chars)"
        )

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more factual responses
        )

    async def generate_with_context_streaming(
        self,
        question: str,
        context_chunks: List[DocumentChunk],
        max_context_length: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using RAG (Retrieval-Augmented Generation).

        This method takes the user's question and relevant context chunks,
        formats them into a prompt, and streams the answer token-by-token.

        Args:
            question: User's question
            context_chunks: Relevant document chunks retrieved from vector DB
            max_context_length: Maximum characters for context (defaults to config)

        Yields:
            Generated answer tokens

        Example:
            >>> service = OllamaService()
            >>> chunks = [...]  # Retrieved from vector DB
            >>> async for token in service.generate_with_context_streaming(
            ...     "How does auth work?",
            ...     chunks
            ... ):
            ...     print(token, end='')
        """
        max_context = max_context_length or settings.rag_context_window

        # Build context from chunks (reuse same logic as non-streaming version)
        context_parts = []
        total_length = 0

        for chunk in context_chunks:
            chunk_text = (
                f"File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n"
                f"```{chunk.language}\n{chunk.text}\n```\n"
            )

            # Check if adding this chunk would exceed limit
            if total_length + len(chunk_text) > max_context:
                logger.info(
                    f"Reached context limit ({max_context} chars), "
                    f"using {len(context_parts)} of {len(context_chunks)} chunks"
                )
                break

            context_parts.append(chunk_text)
            total_length += len(chunk_text)

        context = "\n\n".join(context_parts)

        # Create the RAG prompt
        prompt = f"""Use the following code snippets to answer the question. If the answer cannot be found in the provided context, say so.

Context:
{context}

Question: {question}

Answer:"""

        # System prompt to guide the model
        system_prompt = """You are a helpful AI assistant that answers questions about code.
You provide clear, accurate answers based on the provided code snippets.
Always cite the specific files and line numbers when referencing code.
If you're not sure about something, say so rather than making assumptions."""

        logger.info(
            f"Streaming RAG response with {len(context_parts)} context chunks "
            f"({total_length} chars)"
        )

        # Stream the response
        async for token in self.generate_streaming(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more factual responses
        ):
            yield token

    async def check_health(self) -> bool:
        """
        Check if Ollama is running and the model is available.

        Returns:
            True if Ollama is accessible and model is available, False otherwise
        """
        try:
            # Check if Ollama is running
            url = f"{self.base_url}/api/tags"
            async with httpx.AsyncClient(timeout=Timeout(5.0)) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Check if our model is in the list
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]

                if self.model in model_names:
                    logger.info(f"Ollama health check passed: {self.model} is available")
                    return True
                else:
                    logger.warning(
                        f"Model {self.model} not found. Available models: {model_names}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


def get_ollama_service() -> OllamaService:
    """
    Factory function to get an OllamaService instance.

    Returns:
        OllamaService instance with default configuration
    """
    return OllamaService()
