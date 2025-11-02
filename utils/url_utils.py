"""
URL Utilities for JobSearchAI Application Queue Bridge
Provides centralized URL normalization and comparison utilities.

Part of Story 1.4: Application Queue Integration Bridge
"""

from typing import Optional
from urllib.parse import urlparse, urlunparse
import re


class URLNormalizer:
    """
    Centralized URL handling service for consistent URL operations.
    
    Single Source of Truth for URL transformations:
    - Converts relative paths to full URLs
    - Normalizes URLs for comparison
    - Extracts job IDs for fallback matching
    """
    
    DEFAULT_BASE_URL = "https://www.ostjob.ch"
    
    @staticmethod
    def normalize(url: str, base_url: Optional[str] = None) -> str:
        """
        Normalize URL for database storage and comparison.
        
        This is the primary method for URL normalization used throughout the application.
        It ensures consistent URL format for deduplication and storage.
        
        Args:
            url: URL string (relative or full)
            base_url: Base URL to use (defaults to ostjob.ch)
            
        Returns:
            Fully normalized URL
            
        Examples:
            >>> URLNormalizer.normalize("/job/product-owner/1032053")
            'https://www.ostjob.ch/job/product-owner/1032053'
            
            >>> URLNormalizer.normalize("ostjob.ch/job/title/123")
            'https://www.ostjob.ch/job/title/123'
        """
        return URLNormalizer.to_full_url(url, base_url)
    
    @staticmethod
    def to_full_url(url: str, base_url: Optional[str] = None) -> str:
        """
        Convert relative URL to full URL and normalize for consistent storage.
        
        Normalizes by:
        - Adding protocol (https) if missing
        - Adding www. prefix if missing (for ostjob.ch)
        - Removing trailing slashes
        
        Args:
            url: URL string (relative or full)
            base_url: Base URL to use (defaults to ostjob.ch)
            
        Returns:
            Fully normalized URL
            
        Examples:
            >>> URLNormalizer.to_full_url("/job/product-owner/1032053")
            'https://www.ostjob.ch/job/product-owner/1032053'
            
            >>> URLNormalizer.to_full_url("ostjob.ch/job/title/123")
            'https://www.ostjob.ch/job/title/123'
            
            >>> URLNormalizer.to_full_url("https://ostjob.ch/job/title/123/")
            'https://www.ostjob.ch/job/title/123'
        """
        if not url:
            return ""
        
        # Remove trailing slashes
        url = url.rstrip('/')
            
        # Already a full URL - normalize it
        if url.startswith(('http://', 'https://')):
            # Parse URL
            parsed = urlparse(url)
            
            # Ensure https protocol
            protocol = 'https'
            
            # Normalize domain (add www. for ostjob.ch if missing)
            domain = parsed.netloc
            if 'ostjob.ch' in domain and not domain.startswith('www.'):
                domain = 'www.' + domain
            
            # Rebuild URL
            path = parsed.path.rstrip('/')
            return f"{protocol}://{domain}{path}"
            
        # Relative URL - add base
        base = base_url or URLNormalizer.DEFAULT_BASE_URL
        
        # Ensure base doesn't end with slash and url starts with slash
        base = base.rstrip('/')
        if not url.startswith('/'):
            url = '/' + url
            
        return f"{base}{url}"
    
    @staticmethod
    def normalize_for_comparison(url: str) -> str:
        """
        Normalize URL for comparison by removing protocol, www, and trailing slashes.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL string for comparison
            
        Examples:
            >>> URLNormalizer.normalize_for_comparison("https://www.ostjob.ch/job/title/123/")
            'ostjob.ch/job/title/123'
            
            >>> URLNormalizer.normalize_for_comparison("http://ostjob.ch/job/title/123")
            'ostjob.ch/job/title/123'
        """
        if not url:
            return ""
            
        # Parse URL to extract components
        parsed = urlparse(url)
        
        # Remove protocol (scheme)
        domain = parsed.netloc or parsed.path.split('/')[0]
        
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        # Get path, remove leading/trailing slashes
        if parsed.netloc:
            path = parsed.path
        else:
            # Handle case where URL was just a path
            path = '/' + '/'.join(parsed.path.split('/')[1:])
            
        path = path.strip('/')
        
        # Combine domain and path
        normalized = f"{domain}/{path}" if path else domain
        
        return normalized.lower()
    
    @staticmethod
    def clean_malformed_url(url: str) -> str:
        """
        Clean malformed URLs with doubled protocols or file extensions.
        
        Handles common URL issues:
        - Doubled base URLs (e.g., https://site.com/https://site.com/path)
        - File extensions incorrectly appended (.md, .json, etc.)
        - Leading slashes before full URLs (/https://site.com/path)
        
        Args:
            url: Potentially malformed URL
            
        Returns:
            Cleaned URL
            
        Examples:
            >>> URLNormalizer.clean_malformed_url("https://www.ostjob.ch/https://www.ostjob.ch/job/test/123.md")
            'https://www.ostjob.ch/job/test/123'
            
            >>> URLNormalizer.clean_malformed_url("/https://www.ostjob.ch/job/test/123")
            'https://www.ostjob.ch/job/test/123'
            
            >>> URLNormalizer.clean_malformed_url("https://www.ostjob.ch/job/test/123.json")
            'https://www.ostjob.ch/job/test/123'
        """
        if not url:
            return url
        
        # Remove common file extensions that don't belong in URLs
        for ext in ['.md', '.json', '.html', '.txt']:
            if url.endswith(ext):
                url = url[:-len(ext)]
        
        # Fix doubled URLs: /https://example.com/https://example.com/path
        # or https://example.com/https://example.com/path
        if url.count('https://') > 1 or url.count('http://') > 1:
            # Extract the last occurrence of the protocol
            if 'https://' in url:
                parts = url.split('https://')
                # Take the last non-empty part
                url = 'https://' + parts[-1]
            elif 'http://' in url:
                parts = url.split('http://')
                url = 'http://' + parts[-1]
        
        # Handle case where URL starts with /http:// or /https://
        if url.startswith('/http://') or url.startswith('/https://'):
            url = url[1:]  # Remove leading slash
        
        return url
    
    @staticmethod
    def extract_job_id(url: str) -> Optional[str]:
        """
        Extract job ID from ostjob.ch URL for fallback matching.
        
        Args:
            url: URL containing job ID
            
        Returns:
            Job ID string or None if not found
            
        Examples:
            >>> URLNormalizer.extract_job_id("https://www.ostjob.ch/job/product-owner/1032053")
            '1032053'
            
            >>> URLNormalizer.extract_job_id("/job/title/123")
            '123'
        """
        if not url:
            return None
            
        # Pattern: /job/{slug}/{job_id} or /job/{job_id}
        # Job ID is typically numeric at the end
        match = re.search(r'/job/[^/]+/(\d+)', url)
        if match:
            return match.group(1)
            
        # Try simpler pattern: /job/{job_id}
        match = re.search(r'/job/(\d+)', url)
        if match:
            return match.group(1)
            
        return None
    
    @staticmethod
    def urls_match(url1: str, url2: str) -> bool:
        """
        Check if two URLs refer to the same job posting.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            True if URLs match after normalization, False otherwise
            
        Examples:
            >>> URLNormalizer.urls_match(
            ...     "https://www.ostjob.ch/job/title/123/",
            ...     "http://ostjob.ch/job/title/123"
            ... )
            True
        """
        # Convert relative URLs to full URLs for consistent comparison
        full_url1 = URLNormalizer.to_full_url(url1)
        full_url2 = URLNormalizer.to_full_url(url2)
        
        # Try normalized comparison
        norm1 = URLNormalizer.normalize_for_comparison(full_url1)
        norm2 = URLNormalizer.normalize_for_comparison(full_url2)
        
        if norm1 == norm2:
            return True
            
        # Fallback: Compare job IDs only if domains match
        # Extract domains from normalized URLs
        domain1 = norm1.split('/')[0] if '/' in norm1 else norm1
        domain2 = norm2.split('/')[0] if '/' in norm2 else norm2
        
        # Only compare job IDs if domains are the same
        if domain1 == domain2:
            id1 = URLNormalizer.extract_job_id(full_url1)
            id2 = URLNormalizer.extract_job_id(full_url2)
            
            if id1 and id2 and id1 == id2:
                return True
            
        return False
