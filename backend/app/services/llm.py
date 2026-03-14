"""
LLM service for interacting with Groq API.

This module handles communication with the Groq API for
generating responses using cloud-hosted LLMs.
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from groq import AsyncGroq, APIConnectionError, RateLimitError
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


class GroqService:
    """
    Service for interacting with Groq API.

    This class handles making requests to the Groq API to generate
    responses using cloud-hosted LLM models.

    Attributes:
        model: Model name to use (e.g., 'llama-3.3-70b-versatile')
    """

    def __init__(self):
        """Initialize Groq service."""
        self.model = settings.groq_model
        self._client: Optional[AsyncGroq] = None

    def _get_client(self) -> AsyncGroq:
        """Get or create Groq async client."""
        if self._client is None:
            self._client = AsyncGroq(api_key=settings.groq_api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
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

        Retries up to 3 times on connection errors or rate limits with exponential backoff.

        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate (None = model default)

        Returns:
            Generated text response

        Raises:
            Exception: If the Groq API request fails after all retries
        """
        try:
            client = self._get_client()

            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs: Dict[str, Any] = {
                "messages": messages,
                "model": self.model,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            logger.info(f"Generating response with {self.model}")
            logger.debug(f"Prompt length: {len(prompt)} chars")

            chat_completion = await client.chat.completions.create(**kwargs)
            generated_text = chat_completion.choices[0].message.content or ""

            logger.info(f"Generated response: {len(generated_text)} chars")

            return generated_text

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.

        Streams tokens as they are generated using Groq's streaming API.
        Each token is yielded as soon as it's available.

        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate (None = model default)

        Yields:
            Generated text tokens

        Raises:
            Exception: If the Groq API request fails
        """
        try:
            client = self._get_client()

            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs: Dict[str, Any] = {
                "messages": messages,
                "model": self.model,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            logger.info(f"🤖 Starting streaming generation with {self.model}")
            logger.debug(f"   Prompt length: {len(prompt)} chars")

            stream = await client.chat.completions.create(**kwargs)

            token_count = 0
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    token_count += 1
                    if token_count <= 3 or token_count % 20 == 0:
                        logger.debug(f"   Token #{token_count}: {repr(content[:20])}")
                    yield content

            logger.info(f"✓ Streaming generation complete ({token_count} tokens)")

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
            >>> service = GroqService()
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
            >>> service = GroqService()
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
        Check if the Groq API is accessible and the model is available.

        Returns:
            True if Groq API is accessible, False otherwise
        """
        try:
            client = self._get_client()
            # Make a minimal API call to verify connectivity and API key
            await client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model=self.model,
                max_tokens=1,
            )
            logger.info(f"Groq API health check passed: {self.model} is available")
            return True
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False


def get_ollama_service() -> GroqService:
    """
    Factory function to get a GroqService instance.

    Named get_ollama_service for backward compatibility with existing callers
    in routes.py and websocket.py.

    Returns:
        GroqService instance with default configuration
    """
    return GroqService()
