"""
Manual test for LinkedIn Generator Service.

This test file validates the LinkedIn message generation functionality
including character limits, language detection, and error handling.
"""

import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from services.linkedin_generator import generate_linkedin_messages

def test_basic_generation():
    """Test basic LinkedIn message generation with all fields provided."""
    print("\n=== Test 1: Basic Generation ===")
    
    cv_summary = "Experienced Python Developer with 5 years of experience in AI/ML and web development."
    job_details = {
        "Company Name": "Tech Corp",
        "Job Title": "Senior Python Engineer",
        "Contact Person": "John Doe",
        "Job Description": "We are looking for a Python expert with AI experience to join our team."
    }
    
    mock_response = {
        "connection_request_hiring_manager": "Hi John, I saw the Senior Engineer role at Tech Corp. My background in Python and AI seems like a great fit. I'd love to connect!",
        "peer_networking": "Hi, I'm interested in Tech Corp. I see you work there as an Engineer. How do you find the culture?",
        "inmail_message": "Dear John, I am writing to express my interest in the Senior Engineer role. I have 5 years of Python experience in AI/ML and web development..."
    }
    
    with patch('services.linkedin_generator.generate_json_from_prompt', return_value=mock_response):
        result = generate_linkedin_messages(cv_summary, job_details)
        
        if result == mock_response:
            print("✅ PASSED: Basic generation successful")
            print(f"   Connection request length: {len(result['connection_request_hiring_manager'])} chars")
            print(f"   Peer networking length: {len(result['peer_networking'])} chars")
            print(f"   InMail word count: {len(result['inmail_message'].split())} words")
        else:
            print("❌ FAILED: Result does not match expected output")
            print(f"   Expected: {mock_response}")
            print(f"   Got: {result}")

def test_character_limit_validation():
    """Test that character limits are enforced with truncation."""
    print("\n=== Test 2: Character Limit Validation ===")
    
    cv_summary = "Python Developer"
    job_details = {
        "Company Name": "Test Co",
        "Job Title": "Developer",
        "Job Description": "Python role"
    }
    
    # Create a mock response that exceeds limits
    mock_response = {
        "connection_request_hiring_manager": "A" * 350,  # Exceeds 300 char limit
        "peer_networking": "B" * 600,  # Exceeds 500 char limit
        "inmail_message": " ".join(["word"] * 200)  # Exceeds 150 word limit
    }
    
    with patch('services.linkedin_generator.generate_json_from_prompt', return_value=mock_response):
        result = generate_linkedin_messages(cv_summary, job_details)
        
        connection_len = len(result['connection_request_hiring_manager'])
        peer_len = len(result['peer_networking'])
        inmail_words = len(result['inmail_message'].split())
        
        if connection_len <= 300 and peer_len <= 500 and inmail_words <= 150:
            print("✅ PASSED: Character limits enforced")
            print(f"   Connection request: {connection_len}/300 chars")
            print(f"   Peer networking: {peer_len}/500 chars")
            print(f"   InMail: {inmail_words}/150 words")
        else:
            print("❌ FAILED: Character limits not enforced")
            print(f"   Connection: {connection_len} (should be ≤300)")
            print(f"   Peer: {peer_len} (should be ≤500)")
            print(f"   InMail: {inmail_words} words (should be ≤150)")

def test_without_contact_person():
    """Test generation without contact person (should use generic placeholder)."""
    print("\n=== Test 3: Without Contact Person ===")
    
    cv_summary = "Software Engineer"
    job_details = {
        "Company Name": "Startup Inc",
        "Job Title": "Backend Developer",
        "Job Description": "Looking for a backend developer"
        # No Contact Person provided
    }
    
    mock_response = {
        "connection_request_hiring_manager": "Hi, I saw the Backend Developer role at Startup Inc. I'd love to connect!",
        "peer_networking": "Hi [Name], interested in learning about Startup Inc's engineering culture.",
        "inmail_message": "Dear Hiring Manager, I am interested in the Backend Developer position..."
    }
    
    with patch('services.linkedin_generator.generate_json_from_prompt', return_value=mock_response):
        result = generate_linkedin_messages(cv_summary, job_details)
        
        if result:
            print("✅ PASSED: Generated messages without contact person")
            print(f"   Uses generic placeholders: {result['peer_networking']}")
        else:
            print("❌ FAILED: Could not generate without contact person")

def test_missing_cv_summary():
    """Test error handling when CV summary is missing."""
    print("\n=== Test 4: Missing CV Summary ===")
    
    job_details = {
        "Company Name": "Test Co",
        "Job Title": "Developer",
        "Job Description": "Test role"
    }
    
    result = generate_linkedin_messages("", job_details)
    
    if result is None:
        print("✅ PASSED: Correctly returns None for missing CV summary")
    else:
        print("❌ FAILED: Should return None for missing CV summary")

def test_api_error_handling():
    """Test error handling when API fails."""
    print("\n=== Test 5: API Error Handling ===")
    
    cv_summary = "Developer"
    job_details = {
        "Company Name": "Test Co",
        "Job Title": "Developer",
        "Job Description": "Test"
    }
    
    with patch('services.linkedin_generator.generate_json_from_prompt', side_effect=Exception("API Error")):
        result = generate_linkedin_messages(cv_summary, job_details)
        
        if result is None:
            print("✅ PASSED: Correctly handles API errors")
        else:
            print("❌ FAILED: Should return None on API error")

def test_missing_json_keys():
    """Test handling of incomplete JSON response."""
    print("\n=== Test 6: Missing JSON Keys ===")
    
    cv_summary = "Developer"
    job_details = {
        "Company Name": "Test Co",
        "Job Title": "Developer",
        "Job Description": "Test"
    }
    
    # Mock response missing required keys
    mock_response = {
        "connection_request_hiring_manager": "Test message"
        # Missing peer_networking and inmail_message
    }
    
    with patch('services.linkedin_generator.generate_json_from_prompt', return_value=mock_response):
        result = generate_linkedin_messages(cv_summary, job_details)
        
        if result is None:
            print("✅ PASSED: Correctly rejects incomplete JSON")
        else:
            print("❌ FAILED: Should reject JSON with missing keys")

def run_all_tests():
    """Run all manual tests."""
    print("=" * 60)
    print("LinkedIn Generator Service - Manual Test Suite")
    print("=" * 60)
    
    test_basic_generation()
    test_character_limit_validation()
    test_without_contact_person()
    test_missing_cv_summary()
    test_api_error_handling()
    test_missing_json_keys()
    
    print("\n" + "=" * 60)
    print("Test suite completed")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
