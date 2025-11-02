#!/usr/bin/env python3
"""
Fallback Quality Manager for Production Deployment

This module provides intelligent quality monitoring and fallback mechanisms
for the optimized headless browser scraping system. It can be integrated
into production to ensure consistent extraction quality.
"""

import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

# Import the optimized scraper functions
from graph_scraper_utils import get_job_details_with_graphscrapeai, calculate_quality_score

logger = logging.getLogger("fallback_quality_manager")

class QualityThresholds:
    """Quality thresholds for different deployment scenarios"""
    
    PRODUCTION_MINIMUM = 25.0    # Absolute minimum for production
    QUALITY_WARNING = 35.0       # Below this triggers quality warnings
    QUALITY_TARGET = 50.0        # Target quality score
    FALLBACK_TRIGGER = 20.0      # Below this triggers fallback consideration

class ProductionQualityManager:
    """Manages quality monitoring and fallback for production deployment"""
    
    def __init__(self, enable_monitoring=True, log_to_file=True):
        self.enable_monitoring = enable_monitoring
        self.log_to_file = log_to_file
        self.extraction_stats = {
            "session_start": datetime.now().isoformat(),
            "total_extractions": 0,
            "successful_extractions": 0,
            "quality_failures": 0,
            "average_quality": 0.0,
            "quality_scores": [],
            "failed_urls": [],
            "low_quality_urls": []
        }
        
        if self.log_to_file:
            self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging for production monitoring"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"quality_monitoring_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        
        # Add to existing loggers
        for logger_name in ["graph_scraper_utils", "fallback_quality_manager"]:
            existing_logger = logging.getLogger(logger_name)
            existing_logger.addHandler(file_handler)
    
    def extract_with_quality_monitoring(self, job_url: str, quality_threshold: Optional[float] = None) -> Tuple[Optional[Dict], Dict]:
        """
        Extract job details with comprehensive quality monitoring
        
        Args:
            job_url: URL to extract from
            quality_threshold: Minimum acceptable quality score (uses defaults if None)
        
        Returns:
            Tuple of (extracted_details, quality_report)
        """
        if quality_threshold is None:
            quality_threshold = QualityThresholds.PRODUCTION_MINIMUM
        
        start_time = time.time()
        extraction_result = None
        quality_report = {
            "url": job_url,
            "extraction_time": 0,
            "quality_score": 0,
            "meets_threshold": False,
            "status": "unknown",
            "warnings": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            logger.info(f"Starting production extraction with quality monitoring: {job_url}")
            
            # Perform extraction using optimized method
            extraction_result = get_job_details_with_graphscrapeai(job_url)
            extraction_time = time.time() - start_time
            
            quality_report["extraction_time"] = round(extraction_time, 2)
            
            if extraction_result:
                quality_score = calculate_quality_score(extraction_result)
                quality_report["quality_score"] = quality_score
                quality_report["meets_threshold"] = quality_score >= quality_threshold
                
                # Assess quality level
                if quality_score >= QualityThresholds.QUALITY_TARGET:
                    quality_report["status"] = "excellent"
                elif quality_score >= QualityThresholds.QUALITY_WARNING:
                    quality_report["status"] = "good"
                elif quality_score >= QualityThresholds.PRODUCTION_MINIMUM:
                    quality_report["status"] = "acceptable"
                    quality_report["warnings"].append("Quality below target but acceptable for production")
                else:
                    quality_report["status"] = "poor"
                    quality_report["warnings"].append("Quality below production minimum")
                
                # Content-specific warnings
                self._assess_content_quality(extraction_result, quality_report)
                
                logger.info(f"Extraction completed - Quality: {quality_score:.2f} ({quality_report['status']})")
                
                # Update monitoring statistics
                if self.enable_monitoring:
                    self._update_stats(quality_score, success=True, url=job_url, warnings=quality_report["warnings"])
            
            else:
                quality_report["status"] = "failed"
                quality_report["warnings"].append("Extraction returned no results")
                logger.error(f"Extraction failed for {job_url}")
                
                if self.enable_monitoring:
                    self._update_stats(0, success=False, url=job_url, warnings=["Extraction failed"])
        
        except Exception as e:
            quality_report["status"] = "error"
            quality_report["warnings"].append(f"Extraction error: {str(e)}")
            logger.error(f"Extraction error for {job_url}: {e}")
            
            if self.enable_monitoring:
                self._update_stats(0, success=False, url=job_url, warnings=[f"Error: {str(e)}"])
        
        return extraction_result, quality_report
    
    def _assess_content_quality(self, details: Dict, quality_report: Dict):
        """Assess specific content quality issues"""
        warnings = quality_report["warnings"]
        
        # Check for empty critical fields
        if not details.get("Required Skills") or str(details.get("Required Skills")).strip() == "":
            warnings.append("Required Skills field is empty")
        
        if not details.get("Responsibilities") or str(details.get("Responsibilities")).strip() == "":
            warnings.append("Responsibilities field is empty")
        
        if not details.get("Contact Person") or str(details.get("Contact Person")).strip() == "":
            warnings.append("Contact Person not found")
        
        # Check for potentially incomplete extraction
        job_description = details.get("Job Description", "")
        if len(str(job_description)) < 50:
            warnings.append("Job Description appears unusually short")
        
        company_info = details.get("Company Information", "")
        if len(str(company_info)) < 30:
            warnings.append("Company Information appears limited")
    
    def _update_stats(self, quality_score: float, success: bool, url: str, warnings: list):
        """Update internal statistics for monitoring"""
        self.extraction_stats["total_extractions"] += 1
        
        if success:
            self.extraction_stats["successful_extractions"] += 1
            self.extraction_stats["quality_scores"].append(quality_score)
            
            # Update average quality
            if self.extraction_stats["quality_scores"]:
                self.extraction_stats["average_quality"] = sum(self.extraction_stats["quality_scores"]) / len(self.extraction_stats["quality_scores"])
            
            # Track quality failures
            if quality_score < QualityThresholds.PRODUCTION_MINIMUM:
                self.extraction_stats["quality_failures"] += 1
                self.extraction_stats["low_quality_urls"].append({
                    "url": url,
                    "quality_score": quality_score,
                    "warnings": warnings
                })
        else:
            self.extraction_stats["failed_urls"].append({
                "url": url,
                "warnings": warnings
            })
    
    def get_quality_report(self) -> Dict:
        """Get comprehensive quality report for monitoring"""
        if self.extraction_stats["total_extractions"] == 0:
            return {"message": "No extractions performed yet"}
        
        success_rate = (self.extraction_stats["successful_extractions"] / self.extraction_stats["total_extractions"]) * 100
        quality_failure_rate = (self.extraction_stats["quality_failures"] / max(self.extraction_stats["successful_extractions"], 1)) * 100
        
        report = {
            "session_summary": {
                "session_start": self.extraction_stats["session_start"],
                "total_extractions": self.extraction_stats["total_extractions"],
                "successful_extractions": self.extraction_stats["successful_extractions"],
                "success_rate": round(success_rate, 2),
                "quality_failures": self.extraction_stats["quality_failures"],
                "quality_failure_rate": round(quality_failure_rate, 2),
                "average_quality": round(self.extraction_stats["average_quality"], 2)
            },
            "quality_distribution": self._get_quality_distribution(),
            "recommendations": self._generate_recommendations(),
            "failed_urls": self.extraction_stats["failed_urls"],
            "low_quality_urls": self.extraction_stats["low_quality_urls"]
        }
        
        return report
    
    def _get_quality_distribution(self) -> Dict:
        """Analyze quality score distribution"""
        if not self.extraction_stats["quality_scores"]:
            return {}
        
        scores = self.extraction_stats["quality_scores"]
        return {
            "excellent": len([s for s in scores if s >= QualityThresholds.QUALITY_TARGET]),
            "good": len([s for s in scores if QualityThresholds.QUALITY_WARNING <= s < QualityThresholds.QUALITY_TARGET]),
            "acceptable": len([s for s in scores if QualityThresholds.PRODUCTION_MINIMUM <= s < QualityThresholds.QUALITY_WARNING]),
            "poor": len([s for s in scores if s < QualityThresholds.PRODUCTION_MINIMUM])
        }
    
    def _generate_recommendations(self) -> list:
        """Generate recommendations based on quality patterns"""
        recommendations = []
        
        if self.extraction_stats["total_extractions"] == 0:
            return recommendations
        
        success_rate = (self.extraction_stats["successful_extractions"] / self.extraction_stats["total_extractions"]) * 100
        quality_failure_rate = (self.extraction_stats["quality_failures"] / max(self.extraction_stats["successful_extractions"], 1)) * 100
        avg_quality = self.extraction_stats["average_quality"]
        
        # Success rate recommendations
        if success_rate < 90:
            recommendations.append({
                "priority": "high",
                "issue": f"Low success rate: {success_rate:.1f}%",
                "recommendation": "Investigate extraction failures and consider network/browser optimizations"
            })
        
        # Quality score recommendations
        if avg_quality < QualityThresholds.QUALITY_WARNING:
            recommendations.append({
                "priority": "high",
                "issue": f"Low average quality: {avg_quality:.1f}",
                "recommendation": "Review extraction prompt and browser configuration for quality improvements"
            })
        elif avg_quality < QualityThresholds.QUALITY_TARGET:
            recommendations.append({
                "priority": "medium",
                "issue": f"Quality below target: {avg_quality:.1f}",
                "recommendation": "Monitor quality trends and consider fine-tuning extraction parameters"
            })
        
        # Quality failure rate recommendations
        if quality_failure_rate > 20:
            recommendations.append({
                "priority": "high",
                "issue": f"High quality failure rate: {quality_failure_rate:.1f}%",
                "recommendation": "Implement quality validation improvements or consider fallback mechanisms"
            })
        
        return recommendations
    
    def save_quality_report(self, filename: Optional[str] = None) -> str:
        """Save detailed quality report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_report_{timestamp}.json"
        
        report = self.get_quality_report()
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"Quality report saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save quality report: {e}")
            return ""

def test_quality_manager():
    """Test the quality manager with the test URLs"""
    test_urls = [
        "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023929",
        "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023928",
        "https://www.ostjob.ch/job/verkaufstalent-im-aussendienst-80-100-m-w-d/1023927"
    ]
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Create quality manager
    quality_manager = ProductionQualityManager(enable_monitoring=True, log_to_file=False)
    
    print("\n" + "="*80)
    print("PRODUCTION QUALITY MANAGER TEST")
    print("="*80)
    
    results = []
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nProcessing URL {i}/3: {url}")
        print("-" * 80)
        
        details, quality_report = quality_manager.extract_with_quality_monitoring(url)
        results.append((details, quality_report))
        
        # Display results
        if details:
            print(f"✅ SUCCESS")
            print(f"   Quality Score: {quality_report['quality_score']}")
            print(f"   Status: {quality_report['status'].upper()}")
            print(f"   Extraction Time: {quality_report['extraction_time']}s")
            
            if quality_report['warnings']:
                print(f"   ⚠️  Warnings:")
                for warning in quality_report['warnings']:
                    print(f"      - {warning}")
            
            # Show key extracted fields
            print(f"   Job Title: {details.get('Job Title', 'N/A')}")
            print(f"   Company: {details.get('Company Name', 'N/A')}")
            print(f"   Has Skills: {'✓' if details.get('Required Skills') and str(details.get('Required Skills')).strip() else '✗'}")
            print(f"   Has Responsibilities: {'✓' if details.get('Responsibilities') and str(details.get('Responsibilities')).strip() else '✗'}")
            print(f"   Contact Person: {details.get('Contact Person', 'N/A') or 'N/A'}")
        else:
            print(f"❌ FAILED")
            print(f"   Status: {quality_report['status'].upper()}")
            if quality_report['warnings']:
                for warning in quality_report['warnings']:
                    print(f"   - {warning}")
    
    # Generate and display final quality report
    print("\n" + "="*80)
    print("QUALITY MONITORING SUMMARY")
    print("="*80)
    
    final_report = quality_manager.get_quality_report()
    summary = final_report["session_summary"]
    
    print(f"Total Extractions: {summary['total_extractions']}")
    print(f"Success Rate: {summary['success_rate']}%")
    print(f"Average Quality Score: {summary['average_quality']}")
    print(f"Quality Failure Rate: {summary['quality_failure_rate']}%")
    
    # Quality distribution
    if "quality_distribution" in final_report:
        dist = final_report["quality_distribution"]
        print(f"\nQuality Distribution:")
        print(f"  Excellent (≥{QualityThresholds.QUALITY_TARGET}): {dist.get('excellent', 0)}")
        print(f"  Good ({QualityThresholds.QUALITY_WARNING}-{QualityThresholds.QUALITY_TARGET}): {dist.get('good', 0)}")
        print(f"  Acceptable ({QualityThresholds.PRODUCTION_MINIMUM}-{QualityThresholds.QUALITY_WARNING}): {dist.get('acceptable', 0)}")
        print(f"  Poor (<{QualityThresholds.PRODUCTION_MINIMUM}): {dist.get('poor', 0)}")
    
    # Recommendations
    if final_report["recommendations"]:
        print(f"\nRecommendations:")
        for rec in final_report["recommendations"]:
            print(f"  [{rec['priority'].upper()}] {rec['issue']}")
            print(f"    → {rec['recommendation']}")
    
    # Save detailed report
    report_file = quality_manager.save_quality_report()
    if report_file:
        print(f"\nDetailed quality report saved to: {report_file}")
    
    print("="*80)
    
    return results, final_report

if __name__ == "__main__":
    test_quality_manager()
