"""
API utilities for JobsearchAI.

This module provides wrappers and utilities for API operations,
particularly OpenAI API operations which are used across the application.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, cast

import openai

from config import config, get_openai_api_key, get_openai_defaults
from utils.decorators import handle_exceptions, retry, cache_result

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIClient:
    """
    Wrapper for OpenAI API client with centralized configuration and error handling.
    
    This class provides a standardized interface for OpenAI API operations,
    with consistent error handling, retries, and caching.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(OpenAIClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the OpenAI client (only once)"""
        if self._initialized:
            return
        
        # Get API key from configuration
        self.api_key = get_openai_api_key()
        
        # Get default parameters
        self.defaults = get_openai_defaults()
        
        # Initialize client
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI API key not found, client not initialized")
            self.client = None
        
        self._initialized = True
    
    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized with a valid API key"""
        return self.client is not None
    
    @handle_exceptions(default_return=None)
    @retry(max_attempts=3, delay=1.0, backoff_factor=2.0, 
           exceptions=(openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError))
    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Generate a chat completion using the OpenAI API.
        
        Args:
            messages: List of message objects with role and content
            model: OpenAI model to use (defaults to config value)
            temperature: Sampling temperature (defaults to config value)
            max_tokens: Maximum tokens to generate (defaults to config value)
            response_format: Response format specification (e.g., {"type": "json_object"})
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Generated completion text, or None if generation fails
        
        Example:
            response = openai_client.generate_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Tell me a joke."}
                ]
            )
        """
        if not self.is_initialized:
            logger.error("OpenAI client not initialized, cannot generate completion")
            return None
        
        # Use provided values or defaults
        model = model or self.defaults.get("model")
        temperature = temperature if temperature is not None else self.defaults.get("temperature")
        max_tokens = max_tokens or self.defaults.get("max_tokens")
        
        # Log the request
        logger.info(f"Generating chat completion with model {model}")
        
        # Make the API call
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs
        )
        
        # Extract and return the completion text
        if response and response.choices and len(response.choices) > 0:
            completion = response.choices[0].message.content
            logger.info(f"Successfully generated completion ({len(completion)} chars)")
            return completion.strip()
        
        # Shouldn't normally reach here due to error handling,
        # but just in case the response structure is unexpected
        logger.warning("Received unexpected response structure from OpenAI API")
        return None
    
    @handle_exceptions(default_return=None)
    @cache_result(max_size=100, ttl=3600)  # Cache for 1 hour
    def generate_structured_output(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant that returns structured data.",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output from a prompt.
        
        This method ensures that the output is valid JSON and handles error cases.
        
        Args:
            prompt: The prompt text
            system_prompt: System message to set the context
            model: OpenAI model to use (defaults to config value)
            temperature: Sampling temperature (defaults to config value)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Parsed JSON object, or None if generation or parsing fails
        
        Example:
            job_details = openai_client.generate_structured_output(
                prompt="Extract job details from this text: ...",
                system_prompt="You are an expert at extracting structured job data."
            )
        """
        # Set up messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Set response format to JSON
        response_format = {"type": "json_object"}
        
        # Generate the completion
        completion = self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature or 0.2,  # Lower temperature for structured data
            response_format=response_format,
            **kwargs
        )
        
        if not completion:
            logger.warning("Failed to generate completion for structured output")
            return None
        
        # Parse JSON
        try:
            result = json.loads(completion)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Generated text is not valid JSON: {e}")
            # Log a preview of the problematic text for debugging
            if completion:
                preview = completion[:100] + "..." if len(completion) > 100 else completion
                logger.error(f"Invalid JSON text preview: {preview}")
            return None
    
    @handle_exceptions(default_return="")
    def summarize_text(
        self,
        text: str,
        prompt_template: str = "Summarize the following text:\n\n{text}",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Summarize text using the OpenAI API.
        
        Args:
            text: The text to summarize
            prompt_template: Template for the prompt, with {text} placeholder
            model: OpenAI model to use (defaults to config value)
            temperature: Sampling temperature (defaults to config value)
            max_tokens: Maximum tokens to generate (defaults to config value)
            
        Returns:
            Summarized text, or empty string if summarization fails
        
        Example:
            summary = openai_client.summarize_text(
                text="Long document to summarize...",
                prompt_template="Provide a concise summary of this document:\n\n{text}"
            )
        """
        # Format the prompt
        prompt = prompt_template.format(text=text)
        
        # Generate the summary
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": prompt}
        ]
        
        return self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        ) or ""

# Global OpenAI client instance
openai_client = OpenAIClient()

# Helper functions for common operations
def generate_json_from_prompt(
    prompt: str,
    system_prompt: str = "You are a helpful assistant that returns structured data.",
    default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate JSON from a prompt with error handling.
    
    Args:
        prompt: The prompt text
        system_prompt: System message to set the context
        default: Default value to return if generation fails
        
    Returns:
        Generated JSON object, or default if generation fails
    
    Example:
        data = generate_json_from_prompt(
            prompt="Extract job details from this text: ...",
            system_prompt="You are an expert at extracting structured job data.",
            default={"error": "Failed to extract job details"}
        )
    """
    result = openai_client.generate_structured_output(
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    if result is None:
        return default or {}
    
    return result

def summarize_cv(
    cv_text: str,
    template: Optional[str] = None
) -> str:
    """
    Summarize a CV using the OpenAI API.
    
    Args:
        cv_text: The CV text to summarize
        template: Custom prompt template (optional)
        
    Returns:
        Summarized CV text
    
    Example:
        summary = summarize_cv(cv_text)
    """
    # Default template focuses on career aspects
    if template is None:
        template = """
        Fasse den folgenden Lebenslauf zusammen und extrahiere die wichtigsten Informationen:
        
        1. Karrierepfad und -entwicklung
        2. Berufliche Präferenzen (Tätigkeiten, Branchen, Unternehmensgröße, Umgebung)
        3. Ableitbare Karriereziele
        4. Indikatoren für Zufriedenheit in früheren Rollen
        5. Arbeitswerte und kulturelle Präferenzen
        
        {text}
        """
    
    return openai_client.summarize_text(
        text=cv_text,
        prompt_template=template,
        temperature=0.2  # Lower temperature for more consistent output
    )
