#!/usr/bin/env python3
"""
Optimized Graph Scraper Utils - Headless Browser Quality Solution

This module provides optimized configurations for headless browser scraping
that maintain high quality extraction while being deployment-ready.

Key optimizations identified:
1. Increased wait time for dynamic content loading
2. Enhanced browser configuration to avoid bot detection
3. Quality monitoring and fallback mechanisms
4. Hybrid approach with intelligent mode switching
"""

import os
import json
import logging
import re
import time
from scrapegraphai.graphs import SmartScraperGraph
from pathlib import Path
from datetime import datetime

# Set up logger for this module
logger = logging.getLogger("optimized_graph_scraper_utils")

def substitute_env_vars(config_str):
    """
    Substitute environment variable placeholders in configuration string.
    Replaces ${VAR_NAME} with the actual environment variable value.
    """
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value:
            # Only log first few characters for security
            logger.info(f"Substituting ${var_name} with env value: {env_value[:15]}...")
            return env_value
        else:
            logger.warning(f"Environment variable ${var_name} not found, keeping placeholder")
            return match.group(0)
    
    # Pattern to match ${VAR_NAME}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_var, config_str)

def substitute_env_vars_in_dict(config_dict):
    """
    Recursively substitute environment variables in a configuration dictionary.
    """
    if isinstance(config_dict, dict):
        return {k: substitute_env_vars_in_dict(v) for k, v in config_dict.items()}
    elif isinstance(config_dict, list):
        return [substitute_env_vars_in_dict(item) for item in config_dict]
    elif isinstance(config_dict, str):
        return substitute_env_vars(config_dict)
    else:
        return config_dict

def load_config():
    """Loads configuration from job-data-acquisition/settings.json"""
    try:
        project_root = Path.cwd()
        possible_paths = [
            project_root / "job-data-acquisition" / "settings.json",
            Path(__file__).parent / "job-data-acquisition" / "settings.json",
            Path("job-data-acquisition") / "settings.json"
        ]
        
        config_path = None
        for path in possible_paths:
            if path.is_file():
                config_path = path
                logger.info(f"Found configuration file at: {config_path}")
                break
        
        if config_path is None:
            logger.error("Configuration file not found")
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"Successfully loaded configuration from {config_path}")
            
            # Apply environment variable substitution
            logger.info("Applying environment variable substitution to configuration...")
            config = substitute_env_vars_in_dict(config)
            logger.info("Environment variable substitution complete")
            
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}", exc_info=True)
        return None

# Load config at module level
CONFIG = load_config()

# Structured extraction prompt (same as original)
SINGLE_JOB_EXTRACTION_PROMPT = """
Extrahiere die Details des Stellenangebots von dieser Seite IN DER GLEICHEN SPRACHE WIE DIE JOB-AUSSCHREIBUNG. Gib ein JSON-Objekt mit den folgenden Feldern zurück:
1. Job Title (Stellentitel)
2. Company Name (Firmenname)
3. Job Description (Stellenbeschreibung - Erstelle eine umfassende Zusammenfassung, falls möglich)
4. Required Skills (Erforderliche Fähigkeiten - Liste spezifische erwähnte Fähigkeiten auf)
5. Responsibilities (Verantwortlichkeiten - Detailliere die Hauptaufgaben und Pflichten)
6. Company Information (Unternehmensinformationen - Füge Details zur Unternehmenskultur, Vorteilen usw. hinzu, falls verfügbar)
7. Location (Standort/Arbeitsort)
8. Salary Range (Gehaltsspanne - Falls erwähnt)
9. Posting Date (Veröffentlichungsdatum - Falls erwähnt)
10. Application URL (Verwende die ursprüngliche Quell-URL)
11. Contact Person (Ansprechpartner - Falls erwähnt)
12. Application Email (Bewerbungs-E-Mail - Falls erwähnt)
13. Salutation (Anrede - z.B. 'Sehr geehrter Herr **Nachname Contact Person**', 'Sehr geehrte Frau **Nachname Contact Person**', oder 'Sehr geehrte Damen und Herren', falls kein spezifischer Kontakt gefunden wird)

Die Ausgabe muss ein einzelnes JSON-Objekt sein. Wenn ein Feld nicht gefunden wird, verwende null oder einen leeren String.
Priorisiere die Extraktion aussagekräftiger Inhalte für 'Job Description', 'Required Skills' und 'Responsibilities'.

AUSGABE IN DER GLEICHEN SPRACHE WIE DER TEXT DES STELLENANGEBOTES!
"""

class QualityMetrics:
    """Quality assessment for extracted job details"""
    
    @staticmethod
    def calculate_quality_score(details):
        """Calculate quality score based on completeness and content richness"""
        if not details:
            return 0
        
        score = 0
        weights = {
            'Job Title': 10,
            'Company Name': 8,
            'Job Description': 15,
            'Required Skills': 12,
            'Responsibilities': 12,
            'Company Information': 8,
            'Contact Person': 5,
            'Location': 5,
            'Application Email': 3,
            'Salary Range': 3
        }
        
        for field, weight in weights.items():
            value = details.get(field, "")
            if value and str(value).strip():
                # Base score for having the field
                field_score = weight * 0.5
                # Additional score based on content length
                content_length = len(str(value).strip())
                if content_length > 10:
                    field_score += min(weight * 0.5, content_length / 100 * weight * 0.5)
                score += field_score
        
        return round(score, 2)
    
    @staticmethod
    def assess_extraction_quality(details):
        """Assess if extraction meets quality thresholds"""
        if not details:
            return False, "No details extracted"
        
        # Critical fields that must not be empty
        critical_fields = ['Job Title', 'Company Name']
        for field in critical_fields:
            if not details.get(field) or not str(details.get(field)).strip():
                return False, f"Critical field '{field}' is missing or empty"
        
        # Important content fields - at least one should have meaningful content
        content_fields = ['Job Description', 'Required Skills', 'Responsibilities']
        has_meaningful_content = False
        
        for field in content_fields:
            value = details.get(field, "")
            if value and isinstance(value, (str, list)) and len(str(value).strip()) > 20:
                has_meaningful_content = True
                break
        
        if not has_meaningful_content:
            return False, "No meaningful content in job description, skills, or responsibilities"
        
        quality_score = QualityMetrics.calculate_quality_score(details)
        if quality_score < 30:
            return False, f"Quality score too low: {quality_score}"
        
        return True, f"Quality score: {quality_score}"

def get_optimized_headless_config():
    """Get optimized configuration for headless mode based on analysis results"""
    
    if not CONFIG:
        raise Exception("Configuration not loaded")
    
    scraper_config = CONFIG["scraper"]
    llm_config = scraper_config['llm'].copy()
    
    # Ensure model_provider is set
    if 'model_provider' not in llm_config:
        if 'openai' in llm_config.get('model', ''):
            llm_config['model_provider'] = 'openai'
    
    # Optimized configuration based on analysis results
    optimized_config = {
        "llm": llm_config,
        "verbose": True,  # Enable for debugging
        "headless": True,  # Deployment-ready
        "output_format": "json",
        "wait_time": 5,  # KEY OPTIMIZATION: Increased wait time for dynamic content
        "browser_config": {
            "args": [
                "--disable-blink-features=AutomationControlled",  # Avoid bot detection
                "--disable-dev-shm-usage",  # Better memory management
                "--no-sandbox",  # Required for some server environments
                "--disable-setuid-sandbox",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-timer-throttling",  # Ensure JS runs properly
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection"
            ],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080}  # Standard desktop viewport
        },
        "timeout": 30000,  # 30 second timeout
        "load_wait": "networkidle"  # Wait for network to be idle
    }
    
    return optimized_config

def get_fallback_config():
    """Get fallback non-headless configuration for quality assurance"""
    
    if not CONFIG:
        raise Exception("Configuration not loaded")
    
    scraper_config = CONFIG["scraper"]
    llm_config = scraper_config['llm'].copy()
    
    if 'model_provider' not in llm_config:
        if 'openai' in llm_config.get('model', ''):
            llm_config['model_provider'] = 'openai'
    
    fallback_config = {
        "llm": llm_config,
        "verbose": True,
        "headless": False,  # Non-headless fallback
        "output_format": "json",
        "wait_time": 3,
        "timeout": 45000  # Longer timeout for non-headless
    }
    
    return fallback_config

def extract_with_config(job_url, config, mode_name="default"):
    """Extract job details using specified configuration"""
    logger.info(f"Extracting from {job_url} using {mode_name} mode")
    
    try:
        scraper = SmartScraperGraph(
            prompt=SINGLE_JOB_EXTRACTION_PROMPT,
            source=job_url,
            config=config
        )
        
        start_time = time.time()
        result = scraper.run()
        extraction_time = time.time() - start_time
        
        # Process result
        job_details = process_scraper_result(result, job_url)
        
        # Assess quality
        is_quality, quality_msg = QualityMetrics.assess_extraction_quality(job_details)
        quality_score = QualityMetrics.calculate_quality_score(job_details) if job_details else 0
        
        logger.info(f"{mode_name.upper()} extraction completed in {extraction_time:.2f}s - {quality_msg}")
        
        return {
            "success": job_details is not None,
            "details": job_details,
            "extraction_time": extraction_time,
            "quality_score": quality_score,
            "is_quality": is_quality,
            "quality_message": quality_msg,
            "mode": mode_name
        }
        
    except Exception as e:
        logger.error(f"Error in {mode_name} extraction from {job_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "details": None,
            "extraction_time": None,
            "quality_score": 0,
            "is_quality": False,
            "quality_message": f"Extraction failed: {str(e)}",
            "mode": mode_name
        }

def process_scraper_result(result, job_url):
    """Process and validate scraper result (from original code)"""
    if not isinstance(result, dict):
        return None
    
    job_details = None
    if 'content' in result and isinstance(result['content'], dict):
        job_details = result['content']
    elif len(result) == 1 and isinstance(list(result.values())[0], list) and len(list(result.values())[0]) > 0 and isinstance(list(result.values())[0][0], dict):
        job_details = list(result.values())[0][0]
    elif 'Job Title' in result:
        job_details = result
    else:
        return None
    
    if not isinstance(job_details, dict):
        return None
    
    # Basic validation
    title = job_details.get('Job Title')
    if not title:
        return None
    
    # Ensure URL is preserved
    job_details['Application URL'] = job_url
    return job_details

def get_job_details_with_optimized_headless(job_url, enable_fallback=True, quality_threshold=35):
    """
    Extract job details using optimized headless mode with intelligent fallback.
    
    Args:
        job_url (str): The URL of the job posting page
        enable_fallback (bool): Whether to use non-headless fallback if quality is poor
        quality_threshold (float): Minimum quality score to accept headless results
    
    Returns:
        dict: Extraction results with quality metrics
    """
    logger.info(f"Starting optimized headless extraction for: {job_url}")
    
    # Try optimized headless mode first
    optimized_config = get_optimized_headless_config()
    headless_result = extract_with_config(job_url, optimized_config, "optimized_headless")
    
    # Check if headless result meets quality threshold
    if (headless_result["success"] and 
        headless_result["is_quality"] and 
        headless_result["quality_score"] >= quality_threshold):
        
        logger.info(f"Optimized headless extraction successful - Quality Score: {headless_result['quality_score']}")
        return headless_result
    
    # If fallback is disabled, return headless result regardless of quality
    if not enable_fallback:
        logger.warning(f"Headless quality below threshold ({headless_result.get('quality_score', 0)} < {quality_threshold}) but fallback disabled")
        return headless_result
    
    # Use fallback mode for better quality
    logger.warning(f"Headless quality below threshold ({headless_result.get('quality_score', 0)} < {quality_threshold}), trying fallback")
    
    try:
        fallback_config = get_fallback_config()
        fallback_result = extract_with_config(job_url, fallback_config, "non_headless_fallback")
        
        # Compare results and choose the best one
        if (fallback_result["success"] and 
            fallback_result["quality_score"] > headless_result.get("quality_score", 0)):
            
            logger.info(f"Fallback mode provided better quality: {fallback_result['quality_score']} vs {headless_result.get('quality_score', 0)}")
            
            # Mark as fallback used for monitoring
            fallback_result["fallback_used"] = True
            fallback_result["original_headless_score"] = headless_result.get("quality_score", 0)
            
            return fallback_result
        else:
            logger.info("Headless result was still the best available")
            return headless_result
            
    except Exception as e:
        logger.error(f"Fallback extraction failed: {e}")
        logger.info("Returning headless result as fallback failed")
        return headless_result

def get_job_details_with_graphscrapeai(job_url):
    """
    Main extraction function - maintains backward compatibility while using optimized approach.
    This replaces the original function in graph_scraper_utils.py
    """
    return get_job_details_with_optimized_headless(
        job_url=job_url,
        enable_fallback=False,  # Disable fallback for deployment (headless-only)
        quality_threshold=30    # Lower threshold for production use
    )

class ExtractionMonitor:
    """Monitor extraction quality and performance"""
    
    def __init__(self):
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "fallback_used_count": 0,
            "average_quality_score": 0,
            "quality_scores": []
        }
    
    def log_extraction(self, result):
        """Log extraction result for monitoring"""
        self.extraction_stats["total_extractions"] += 1
        
        if result.get("success"):
            self.extraction_stats["successful_extractions"] += 1
            
            quality_score = result.get("quality_score", 0)
            self.extraction_stats["quality_scores"].append(quality_score)
            
            # Update average
            if self.extraction_stats["quality_scores"]:
                self.extraction_stats["average_quality_score"] = sum(self.extraction_stats["quality_scores"]) / len(self.extraction_stats["quality_scores"])
            
            if result.get("fallback_used"):
                self.extraction_stats["fallback_used_count"] += 1
    
    def get_stats(self):
        """Get current extraction statistics"""
        success_rate = 0
        if self.extraction_stats["total_extractions"] > 0:
            success_rate = (self.extraction_stats["successful_extractions"] / self.extraction_stats["total_extractions"]) * 100
        
        fallback_rate = 0
        if self.extraction_stats["successful_extractions"] > 0:
            fallback_rate = (self.extraction_stats["fallback_used_count"] / self.extraction_stats["successful_extractions"]) * 100
        
        return {
            **self.extraction_stats,
            "success_rate": round(success_rate, 2),
            "fallback_rate": round(fallback_rate, 2)
        }

# Global monitor instance
extraction_monitor = ExtractionMonitor()

if __name__ == '__main__':
    # Test the optimized extraction
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    test_urls = [
        "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023929",
        "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023928",
        "https://www.ostjob.ch/job/verkaufstalent-im-aussendienst-80-100-m-w-d/1023927"
    ]
    
    print("\n" + "="*80)
    print("TESTING OPTIMIZED HEADLESS EXTRACTION")
    print("="*80)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTesting URL {i}: {url}")
        print("-" * 80)
        
        # Test optimized headless extraction
        result = get_job_details_with_optimized_headless(url, enable_fallback=False)
        extraction_monitor.log_extraction(result)
        
        if result["success"]:
            details = result["details"]
            print(f"✅ SUCCESS - Quality Score: {result['quality_score']}")
            print(f"   Job Title: {details.get('Job Title', 'N/A')}")
            print(f"   Company: {details.get('Company Name', 'N/A')}")
            print(f"   Required Skills: {len(str(details.get('Required Skills', ''))) > 10}")
            print(f"   Responsibilities: {len(str(details.get('Responsibilities', ''))) > 10}")
            print(f"   Contact Person: {details.get('Contact Person', 'N/A')}")
            print(f"   Extraction Time: {result['extraction_time']:.2f}s")
        else:
            print(f"❌ FAILED - {result.get('quality_message', 'Unknown error')}")
    
    print("\n" + "="*80)
    print("EXTRACTION STATISTICS")
    print("="*80)
    stats = extraction_monitor.get_stats()
    for key, value in stats.items():
        if key != "quality_scores":  # Skip the raw list
            print(f"{key}: {value}")
