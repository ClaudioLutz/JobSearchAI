#!/usr/bin/env python3
"""
Headless Browser Quality Analysis Tool

This script systematically compares content extraction quality between 
headless and non-headless browser modes to identify root causes of 
quality degradation and test optimization strategies.
"""

import os
import json
import logging
import time
from pathlib import Path
from scrapegraphai.graphs import SmartScraperGraph
from datetime import datetime
import asyncio
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("headless_quality_analyzer")

# Test URLs from the task description
TEST_URLS = [
    "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023929",
    "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023928", 
    "https://www.ostjob.ch/job/verkaufstalent-im-aussendienst-80-100-m-w-d/1023927"
]

# Load configuration from settings.json
def load_config():
    """Loads configuration from job-data-acquisition/settings.json"""
    try:
        config_path = Path("job-data-acquisition/settings.json")
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return None
            
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

# Extraction prompt from the original code
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

class HeadlessQualityAnalyzer:
    def __init__(self):
        self.config = load_config()
        if not self.config:
            raise Exception("Failed to load configuration")
        
        self.results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "test_results": {},
            "comparison_summary": {},
            "recommendations": []
        }
        
    def extract_job_details(self, job_url, headless=True, extra_config=None):
        """Extract job details with specified headless configuration"""
        logger.info(f"Extracting from {job_url} with headless={headless}")
        
        try:
            # Base configuration from settings.json
            if not self.config:
                raise Exception("Configuration not loaded")
            scraper_config = self.config["scraper"]
            llm_config = scraper_config['llm'].copy()
            
            # Ensure model_provider is set
            if 'model_provider' not in llm_config:
                if 'openai' in llm_config.get('model', ''):
                    llm_config['model_provider'] = 'openai'
            
            # Build graph configuration
            graph_config = {
                "llm": llm_config,
                "verbose": False,  # Reduce verbosity for cleaner analysis
                "headless": headless,
                "output_format": "json"
            }
            
            # Apply extra configuration for optimization testing
            if extra_config:
                graph_config.update(extra_config)
            
            # Create and run scraper
            scraper = SmartScraperGraph(
                prompt=SINGLE_JOB_EXTRACTION_PROMPT,
                source=job_url,
                config=graph_config
            )
            
            start_time = time.time()
            result = scraper.run()
            extraction_time = time.time() - start_time
            
            # Process result similar to original code
            job_details = self._process_scraper_result(result, job_url)
            
            return {
                "success": job_details is not None,
                "details": job_details,
                "extraction_time": extraction_time,
                "config_used": graph_config
            }
            
        except Exception as e:
            logger.error(f"Error extracting from {job_url} (headless={headless}): {e}")
            return {
                "success": False,
                "error": str(e),
                "details": None,
                "extraction_time": None,
                "config_used": None
            }
    
    def _process_scraper_result(self, result, job_url):
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
    
    def compare_extractions(self, url):
        """Compare headless vs non-headless extraction for a single URL"""
        logger.info(f"Comparing extractions for: {url}")
        
        # Extract with non-headless mode
        non_headless_result = self.extract_job_details(url, headless=False)
        time.sleep(2)  # Brief pause between extractions
        
        # Extract with headless mode
        headless_result = self.extract_job_details(url, headless=True)
        
        # Analyze differences
        comparison = self._analyze_extraction_differences(
            non_headless_result, headless_result, url
        )
        
        return {
            "url": url,
            "non_headless": non_headless_result,
            "headless": headless_result,
            "comparison": comparison
        }
    
    def _analyze_extraction_differences(self, non_headless, headless, url):
        """Analyze the differences between headless and non-headless extractions"""
        if not non_headless["success"] or not headless["success"]:
            return {
                "both_successful": False,
                "non_headless_success": non_headless["success"],
                "headless_success": headless["success"],
                "quality_score_difference": None
            }
        
        nh_details = non_headless["details"]
        h_details = headless["details"]
        
        # Calculate quality scores
        nh_score = self._calculate_quality_score(nh_details)
        h_score = self._calculate_quality_score(h_details)
        
        # Field-by-field comparison
        field_comparison = {}
        key_fields = ['Job Title', 'Company Name', 'Job Description', 'Required Skills', 
                     'Responsibilities', 'Company Information', 'Contact Person']
        
        for field in key_fields:
            nh_value = nh_details.get(field, "")
            h_value = h_details.get(field, "")
            
            field_comparison[field] = {
                "non_headless_length": len(str(nh_value)) if nh_value else 0,
                "headless_length": len(str(h_value)) if h_value else 0,
                "content_difference": self._calculate_content_difference(nh_value, h_value),
                "non_headless_empty": not bool(nh_value and str(nh_value).strip()),
                "headless_empty": not bool(h_value and str(h_value).strip())
            }
        
        return {
            "both_successful": True,
            "non_headless_score": nh_score,
            "headless_score": h_score,
            "quality_score_difference": nh_score - h_score,
            "extraction_time_difference": non_headless.get("extraction_time", 0) - headless.get("extraction_time", 0),
            "field_comparison": field_comparison
        }
    
    def _calculate_quality_score(self, details):
        """Calculate a quality score based on completeness and content richness"""
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
                # Additional score based on content length (up to weight * 0.5)
                content_length = len(str(value).strip())
                if content_length > 10:
                    field_score += min(weight * 0.5, content_length / 100 * weight * 0.5)
                score += field_score
        
        return round(score, 2)
    
    def _calculate_content_difference(self, content1, content2):
        """Calculate content similarity (simple approach)"""
        if not content1 and not content2:
            return 1.0
        if not content1 or not content2:
            return 0.0
        
        str1 = str(content1).lower().strip()
        str2 = str(content2).lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Simple word-based similarity
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def test_raw_html_extraction(self, url):
        """Test raw HTML content extraction with different browser configurations"""
        logger.info(f"Testing raw HTML extraction for: {url}")
        
        configurations = [
            {
                "name": "headless_default",
                "headless": True,
                "args": []
            },
            {
                "name": "non_headless_default",
                "headless": False,
                "args": []
            },
            {
                "name": "headless_optimized",
                "headless": True,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-extensions",
                    "--disable-plugins"
                ],
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        ]
        
        results = {}
        
        async with async_playwright() as p:
            for config in configurations:
                try:
                    browser = await p.chromium.launch(
                        headless=config["headless"],
                        args=config.get("args", [])
                    )
                    
                    context = await browser.new_context(
                        user_agent=config.get("user_agent"),
                        viewport={"width": 1920, "height": 1080}
                    )
                    
                    page = await context.new_page()
                    
                    # Navigate and wait for content
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)  # Additional wait for dynamic content
                    
                    # Get page content
                    content = await page.content()
                    
                    results[config["name"]] = {
                        "content_length": len(content),
                        "has_job_content": "stellenanzeige" in content.lower() or "job" in content.lower(),
                        "has_javascript": "<script" in content,
                        "config": config
                    }
                    
                    await browser.close()
                    await asyncio.sleep(1)  # Brief pause between tests
                    
                except Exception as e:
                    logger.error(f"Error testing {config['name']} for {url}: {e}")
                    results[config["name"]] = {
                        "error": str(e),
                        "config": config
                    }
        
        return results
    
    def test_optimized_configurations(self, url):
        """Test various optimized configurations for headless mode"""
        logger.info(f"Testing optimized configurations for: {url}")
        
        optimizations = [
            {
                "name": "increased_wait_time",
                "extra_config": {"wait_time": 5}
            },
            {
                "name": "custom_user_agent",
                "extra_config": {
                    "browser_config": {
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                }
            },
            {
                "name": "no_sandbox",
                "extra_config": {
                    "browser_config": {
                        "args": ["--no-sandbox", "--disable-setuid-sandbox"]
                    }
                }
            },
            {
                "name": "disable_automation_flags",
                "extra_config": {
                    "browser_config": {
                        "args": ["--disable-blink-features=AutomationControlled"]
                    }
                }
            }
        ]
        
        results = {}
        
        for optimization in optimizations:
            try:
                result = self.extract_job_details(
                    url, 
                    headless=True, 
                    extra_config=optimization.get("extra_config")
                )
                results[optimization["name"]] = result
                time.sleep(2)  # Brief pause between tests
                
            except Exception as e:
                logger.error(f"Error testing {optimization['name']}: {e}")
                results[optimization["name"]] = {"error": str(e)}
        
        return results
    
    def run_comprehensive_analysis(self):
        """Run comprehensive analysis across all test URLs"""
        logger.info("Starting comprehensive headless quality analysis")
        
        for i, url in enumerate(TEST_URLS):
            logger.info(f"Processing URL {i+1}/{len(TEST_URLS)}: {url}")
            
            url_results = {
                "url": url,
                "basic_comparison": None,
                "raw_html_test": None,
                "optimization_tests": None
            }
            
            try:
                # Basic headless vs non-headless comparison
                url_results["basic_comparison"] = self.compare_extractions(url)
                
                # Raw HTML extraction test
                url_results["raw_html_test"] = asyncio.run(self.test_raw_html_extraction(url))
                
                # Optimization tests
                url_results["optimization_tests"] = self.test_optimized_configurations(url)
                
            except Exception as e:
                logger.error(f"Error analyzing {url}: {e}")
                url_results["error"] = str(e)
            
            self.results["test_results"][f"url_{i+1}"] = url_results
            
            # Brief pause between URLs
            if i < len(TEST_URLS) - 1:
                time.sleep(5)
        
        # Generate summary and recommendations
        self._generate_analysis_summary()
        
        # Save results
        self._save_results()
        
        logger.info("Comprehensive analysis completed")
    
    def _generate_analysis_summary(self):
        """Generate analysis summary and recommendations"""
        summary = {
            "total_urls_tested": len(TEST_URLS),
            "quality_degradation_detected": False,
            "avg_quality_difference": 0,
            "common_issues": [],
            "successful_optimizations": []
        }
        
        quality_differences = []
        
        for url_key, url_data in self.results["test_results"].items():
            if "basic_comparison" in url_data and url_data["basic_comparison"]:
                comparison = url_data["basic_comparison"]["comparison"]
                if comparison and comparison.get("both_successful"):
                    diff = comparison.get("quality_score_difference", 0)
                    quality_differences.append(diff)
                    
                    if diff > 10:  # Significant degradation threshold
                        summary["quality_degradation_detected"] = True
        
        if quality_differences:
            summary["avg_quality_difference"] = sum(quality_differences) / len(quality_differences)
        
        # Generate recommendations
        recommendations = []
        
        if summary["quality_degradation_detected"]:
            recommendations.append({
                "priority": "high",
                "issue": "Significant quality degradation in headless mode detected",
                "recommendation": "Implement browser optimization strategies and fallback mechanisms"
            })
        
        if summary["avg_quality_difference"] > 5:
            recommendations.append({
                "priority": "medium",
                "issue": "Moderate quality difference between headless and non-headless modes",
                "recommendation": "Fine-tune wait times and browser configuration"
            })
        
        recommendations.append({
            "priority": "low",
            "issue": "Monitoring needed",
            "recommendation": "Implement quality monitoring in production to detect extraction issues"
        })
        
        self.results["comparison_summary"] = summary
        self.results["recommendations"] = recommendations
    
    def _save_results(self):
        """Save analysis results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"headless_quality_analysis_{timestamp}.json"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis results saved to: {filename}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def print_summary_report(self):
        """Print a concise summary report"""
        print("\n" + "="*80)
        print("HEADLESS BROWSER QUALITY ANALYSIS SUMMARY")
        print("="*80)
        
        summary = self.results.get("comparison_summary", {})
        
        print(f"URLs Tested: {summary.get('total_urls_tested', 0)}")
        print(f"Quality Degradation Detected: {summary.get('quality_degradation_detected', False)}")
        print(f"Average Quality Difference: {summary.get('avg_quality_difference', 0):.2f}")
        
        print(f"\nRECOMMENDATIONS:")
        print("-" * 40)
        for rec in self.results.get("recommendations", []):
            print(f"[{rec['priority'].upper()}] {rec['issue']}")
            print(f"  → {rec['recommendation']}\n")
        
        print("="*80)

def main():
    """Main execution function"""
    try:
        analyzer = HeadlessQualityAnalyzer()
        analyzer.run_comprehensive_analysis()
        analyzer.print_summary_report()
        
        print(f"\nDetailed results saved. Check the generated JSON file for complete analysis.")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
