#!/usr/bin/env python3
"""
Debug script for ScrapeGraphAI job scraper
This script tests different configurations to identify why the scraper returns empty results
"""
import os
import json
import logging
from datetime import datetime
from scrapegraphai.graphs import SmartScraperGraph
import sys

# Add the parent directory to the Python path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the config manager to get the correct environment variables
try:
    from config import ConfigManager
    config_manager = ConfigManager()
    OPENAI_API_KEY = config_manager.get_env("OPENAI_API_KEY")
    logger = logging.getLogger("debug_scraper")
    if OPENAI_API_KEY:
        logger.info(f"Using OpenAI API key from config: {OPENAI_API_KEY[:12]}...")
    else:
        logger.error("No OpenAI API key found in config")
except Exception as e:
    logger = logging.getLogger("debug_scraper")
    logger.error(f"Failed to load config manager: {e}")
    # Fallback to environment variable
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if OPENAI_API_KEY:
        logger.info(f"Using fallback API key: {OPENAI_API_KEY[:12]}...")

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_scraper")

def test_openai_models():
    """Test different OpenAI model names with ScrapeGraphAI"""
    
    # Different model name formats to try
    model_variants = [
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "openai/gpt-4o-mini",
        "openai/gpt-4-turbo",
        "openai/gpt-3.5-turbo"
    ]
    
    simple_prompt = "Extract the page title and first paragraph from this webpage."
    test_url = "https://httpbin.org/html"  # Simple test page
    
    for model in model_variants:
        try:
            logger.info(f"Testing model: {model}")
            
            config = {
                "llm": {
                    "model": model,
                    "api_key": OPENAI_API_KEY,
                    "temperature": 0.1
                },
                "verbose": True,
                "headless": True,
                "output_format": "json"
            }
            
            scraper = SmartScraperGraph(
                prompt=simple_prompt,
                source=test_url,
                config=config
            )
            
            result = scraper.run()
            logger.info(f"✓ Model {model} works! Result: {result}")
            return model  # Return the first working model
            
        except Exception as e:
            logger.error(f"✗ Model {model} failed: {e}")
            continue
    
    logger.error("No working OpenAI model found!")
    return None

def test_simple_job_site_scrape(working_model):
    """Test scraping with a simpler prompt on the job site"""
    
    simple_job_prompt = """
    Look at this webpage and tell me:
    1. What is the page title?
    2. How many job listings can you see?
    3. Extract the title of the first job listing you can find.
    
    Return your answer as JSON with these fields: page_title, job_count, first_job_title
    """
    
    config = {
        "llm": {
            "model": working_model,
            "api_key": OPENAI_API_KEY,
            "temperature": 0.1
        },
        "verbose": True,
        "headless": False,  # Try non-headless first
        "output_format": "json"
    }
    
    test_urls = [
        "https://www.ostjob.ch/job/alle-jobs-nach-datum-seite-1",
        "https://www.ostjob.ch"  # Try the main page first
    ]
    
    for url in test_urls:
        try:
            logger.info(f"Testing simple scrape on: {url}")
            
            scraper = SmartScraperGraph(
                prompt=simple_job_prompt,
                source=url,
                config=config
            )
            
            result = scraper.run()
            logger.info(f"Result from {url}: {result}")
            
            if result and result != []:
                logger.info(f"✓ Got results from {url}!")
                return result
                
        except Exception as e:
            logger.error(f"Error testing {url}: {e}")
    
    return None

def test_headless_vs_non_headless(working_model):
    """Compare headless vs non-headless browser behavior"""
    
    simple_prompt = "Extract the page title and count how many links are on this page."
    test_url = "https://www.ostjob.ch"
    
    for headless in [False, True]:
        try:
            logger.info(f"Testing headless={headless}")
            
            config = {
                "llm": {
                    "model": working_model,
                    "api_key": OPENAI_API_KEY,
                    "temperature": 0.1
                },
                "verbose": True,
                "headless": headless,
                "output_format": "json"
            }
            
            scraper = SmartScraperGraph(
                prompt=simple_prompt,
                source=test_url,
                config=config
            )
            
            result = scraper.run()
            logger.info(f"Headless={headless} result: {result}")
            
        except Exception as e:
            logger.error(f"Headless={headless} failed: {e}")

def main():
    logger.info("=== ScrapeGraphAI Debug Session ===")
    
    # Test 1: Find a working OpenAI model
    logger.info("\n1. Testing OpenAI model compatibility...")
    working_model = test_openai_models()
    
    if not working_model:
        logger.error("Cannot proceed without a working model!")
        return
    
    logger.info(f"Using working model: {working_model}")
    
    # Test 2: Simple job site scrape
    logger.info("\n2. Testing simple job site scraping...")
    simple_result = test_simple_job_site_scrape(working_model)
    
    if simple_result:
        logger.info("✓ Basic scraping works!")
    else:
        logger.error("✗ Basic scraping failed")
    
    # Test 3: Headless vs non-headless
    logger.info("\n3. Testing browser modes...")
    test_headless_vs_non_headless(working_model)
    
    logger.info("\n=== Debug session complete ===")

if __name__ == "__main__":
    main()
