"""
API utilities for JobsearchAI.

This module provides wrappers and utilities for API operations,
particularly OpenAI API operations which are used across the application.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, cast, Literal

import openai

from config import config, get_openai_api_key, get_openai_defaults
from utils.decorators import handle_exceptions, retry, cache_result

# Type hints for new GPT-5.1 parameters
ReasoningEffort = Literal["none", "low", "medium", "high"]
Verbosity = Literal["low", "medium", "high"]

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
    
    def _is_reasoning_model(self, model: str) -> bool:
        """
        Detect if model uses reasoning architecture (GPT-5.1, o1, o3).
        
        Args:
            model: The model identifier string
            
        Returns:
            True if the model uses reasoning architecture, False otherwise
        """
        reasoning_prefixes = ("gpt-5.1", "gpt-5", "o1", "o3")
        return model.startswith(reasoning_prefixes)
    
    def _normalize_roles(self, messages: List[Dict[str, str]], is_reasoning: bool) -> List[Dict[str, str]]:
        """
        Convert system role to developer role for reasoning models.
        
        GPT-5.1 and other reasoning models use 'developer' role instead of 'system'.
        This method automatically converts system messages for compatibility.
        
        Args:
            messages: List of message dictionaries with role and content
            is_reasoning: Whether the target model is a reasoning model
            
        Returns:
            List of messages with roles normalized for the target model
        """
        if not is_reasoning:
            return messages
        
        normalized = []
        for msg in messages:
            if msg.get("role") == "system":
                normalized.append({"role": "developer", "content": msg["content"]})
                logger.debug("Converted system role to developer role for reasoning model")
            else:
                normalized.append(msg)
        
        return normalized
    
    @handle_exceptions(default_return=None)
    @retry(max_attempts=3, delay=1.0, backoff_factor=2.0, 
           exceptions=(openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError))
    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[ReasoningEffort] = None,
        verbosity: Optional[Verbosity] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Generate a chat completion using the OpenAI API with GPT-5.1 support.
        
        Supports both legacy GPT-4 models and new GPT-5.1 reasoning models with
        automatic parameter routing and role normalization.
        
        Args:
            messages: List of message objects with role and content
            model: OpenAI model to use (defaults to config value)
            temperature: Sampling temperature (defaults to config value)
            max_tokens: Maximum tokens to generate (defaults to config value)
            reasoning_effort: Reasoning level for GPT-5.1 models ("none", "low", "medium", "high")
            verbosity: Output length control for GPT-5.1 models ("low", "medium", "high")
            response_format: Response format specification (e.g., {"type": "json_object"})
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Generated completion text, or None if generation fails
            When return_usage=True in kwargs, returns dict with content and usage
        
        Example:
            # GPT-4 usage (unchanged)
            response = openai_client.generate_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Tell me a joke."}
                ]
            )
            
            # GPT-5.1 usage with reasoning
            response = openai_client.generate_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Solve this complex problem..."}
                ],
                model="gpt-5.1",
                reasoning_effort="high"
            )
        """
        if not self.is_initialized:
            logger.error("OpenAI client not initialized, cannot generate completion")
            return None
        
        # Use provided values or defaults
        model = model or self.defaults.get("model") or "gpt-4.1"
        temperature = temperature if temperature is not None else self.defaults.get("temperature")
        max_tokens = max_tokens or self.defaults.get("max_tokens")
        reasoning_effort = reasoning_effort or self.defaults.get("reasoning_effort")
        verbosity = verbosity or self.defaults.get("verbosity")
        
        # Detect model family
        is_reasoning_model = self._is_reasoning_model(model)
        
        # Log the request with model family
        model_type = "reasoning" if is_reasoning_model else "legacy"
        logger.info(f"Generating chat completion with {model_type} model: {model}")
        
        # Normalize roles for reasoning models (system → developer)
        normalized_messages = self._normalize_roles(messages, is_reasoning_model)
        
        # Prepare request parameters
        request_params = {
            "model": model,
            "messages": normalized_messages,
            "stream": False
        }
        
        # Add model-specific parameters
        if is_reasoning_model:
            # Use new parameter names for GPT-5.1
            if max_tokens:
                request_params["max_completion_tokens"] = max_tokens
            if reasoning_effort:
                request_params["reasoning_effort"] = reasoning_effort
                logger.debug(f"Using reasoning_effort: {reasoning_effort}")
            if verbosity:
                request_params["verbosity"] = verbosity
                logger.debug(f"Using verbosity: {verbosity}")
            
            # Handle temperature with reasoning
            if temperature is not None and reasoning_effort not in [None, "none"]:
                logger.warning(
                    f"Temperature may be ignored for {model} with reasoning_effort={reasoning_effort}. "
                    "OpenAI recommends using reasoning_effort without temperature for reasoning models."
                )
                request_params["temperature"] = temperature
            elif temperature is not None:
                request_params["temperature"] = temperature
        else:
            # Use legacy parameters for GPT-4
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            if temperature is not None:
                request_params["temperature"] = temperature
        
        # Add response format if specified
        if response_format:
            request_params["response_format"] = response_format
        
        # Add any additional kwargs
        request_params.update(kwargs)
        
        # Make the API call
        response = self.client.chat.completions.create(**request_params)
        
        # Check if caller wants detailed usage info
        return_usage = kwargs.get("return_usage", False)
        
        # Extract and return the completion
        if response and response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            
            # Extract token usage
            usage = response.usage
            reasoning_tokens = 0
            
            # Extract reasoning tokens for GPT-5.1 models
            if is_reasoning_model and hasattr(usage, 'completion_tokens_details'):
                details = usage.completion_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    reasoning_tokens = details.reasoning_tokens
            
            # Log comprehensive usage
            logger.info(
                f"Model: {response.model} | "
                f"Total: {usage.total_tokens} | "
                f"Input: {usage.prompt_tokens} | "
                f"Output: {usage.completion_tokens}" +
                (f" | Reasoning: {reasoning_tokens}" if reasoning_tokens > 0 else "")
            )
            
            # Return based on caller's preference
            if return_usage:
                return {
                    "content": content.strip() if content else "",
                    "usage": {
                        "total_tokens": usage.total_tokens,
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "reasoning_tokens": reasoning_tokens
                    },
                    "model": response.model
                }
            else:
                logger.info(f"Successfully generated completion ({len(content) if content else 0} chars)")
                return content.strip() if content else ""
        
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
        
        # Generate the completion (ensure we don't pass return_usage to avoid getting dict)
        completion = self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature or 0.2,  # Lower temperature for structured data
            response_format=response_format,
            **kwargs
        )
        
        # Handle potential dict return (shouldn't happen if return_usage not in kwargs)
        if isinstance(completion, dict):
            completion = completion.get("content", "")
        
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
        
        result = self.generate_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Handle potential dict return (shouldn't happen if return_usage not in kwargs)
        if isinstance(result, dict):
            return result.get("content", "")
        
        return result or ""

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
