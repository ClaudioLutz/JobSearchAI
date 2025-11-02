# Testing Guide - JobSearchAI

Comprehensive testing documentation for the JobSearchAI project.

## Overview

This project implements a comprehensive automated testing strategy covering:
- **185+ test cases** across critical system components
- **Unit tests** for models, services, and utilities
- **Integration tests** for end-to-end workflows
- **Edge case testing** for robustness
- **Performance tests** for validation speed

## Test Organization

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_user.py                   # User model tests (25 tests)
├── test_application_context.py    # ApplicationContext tests (23 tests)
├── test_queue_bridge.py           # QueueBridge service tests (22 tests)
├── test_email_sender.py           # Email sending tests (10 tests)
├── test_email_quality.py          # Email quality checks (33 tests)
├── test_validation.py             # Application validation (27 tests)
├── test_url_utils.py              # URL utilities (45 tests)
└── test_integration.py            # End-to-end workflows (20 tests)
```

## Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_application_context.py -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=. --cov-report=html
```

### Run Tests in Parallel
```bash
python -m pytest tests/ -n auto
```

### Run Only Fast Tests
```bash
python -m pytest tests/ -m "not slow"
```

## Test Categories

### 1. Model Tests

#### User Model (`test_user.py`)
Tests user authentication, password management, and database operations:
- User creation and initialization
- Password hashing and verification
- User lookup by username/email
- Uniqueness constraints
- Flask-Login integration
- Password security (salting, hashing)

**Example:**
```python
def test_password_hashing(app, db_session):
    user = User(username='testuser', email='test@example.com')
    user.set_password('MySecret123!')
    
    assert user.password_hash != 'MySecret123!'
    assert user.check_password('MySecret123!') is True
```

#### ApplicationContext Model (`test_application_context.py`)
Tests data transformation and validation:
- Context creation with required/optional fields
- Field validation (missing, invalid, multiple errors)
- Transformation to queue application format
- UUID generation and uniqueness
- Edge cases (Unicode, very long content)

**Example:**
```python
def test_transformation_unique_ids():
    context = ApplicationContext(...)
    
    ids = set()
    for _ in range(10):
        queue_app = context.to_queue_application()
        ids.add(queue_app['id'])
    
    assert len(ids) == 10  # All unique
```

### 2. Service Tests

#### QueueBridge Service (`test_queue_bridge.py`)
Tests data aggregation and queue operations:
- Service initialization with various configurations
- Data aggregation from multiple sources
- Context building from match/letter/scraped data
- Sending applications to queue
- Batch operations and dry-run mode
- Duplicate detection
- Atomic file writing
- Error handling

**Example:**
```python
def test_send_multiple_to_queue(temp_workspace):
    bridge = QueueBridgeService(root_path=str(temp_workspace))
    
    contexts = [create_context() for _ in range(3)]
    result = bridge.send_multiple_to_queue(contexts)
    
    assert result['queued'] == 3
    assert result['failed'] == 0
```

### 3. Utility Tests

#### Email Quality Checker (`test_email_quality.py`)
Tests email address quality assessment:
- Generic email detection (jobs@, hr@, careers@)
- Personal email identification
- Confidence scoring
- Recommendations
- Edge cases (invalid formats, Unicode domains)

#### URL Utilities (`test_url_utils.py`)
Tests URL normalization and comparison:
- Relative to full URL conversion
- URL normalization for comparison
- Job ID extraction
- URL matching (protocol-agnostic, www-handling)
- Malformed URL cleanup
- Real-world scenarios (ostjob.ch)

#### Validation (`test_validation.py`)
Tests application data validation:
- Required field validation
- Email format validation
- Minimum length requirements
- Completeness scoring
- Subject line generation
- Validation summaries

### 4. Integration Tests

#### End-to-End Workflows (`test_integration.py`)
Tests complete application workflows:
- Queue → Validate → Send pipeline
- Validation failures preventing sends
- Send failures moving to failed folder
- Error scenarios (network, authentication, malformed data)
- Batch operations with partial failures
- Performance benchmarks

**Example:**
```python
def test_complete_workflow_success(mock_smtp, temp_dir, sample_app):
    # Create application in pending
    pending_file = temp_dir / 'pending' / 'app.json'
    save_json(pending_file, sample_app)
    
    # Validate
    validator = ApplicationValidator()
    assert validator.validate_application(sample_app)['is_valid']
    
    # Send
    email_sender = EmailSender()
    success, msg = email_sender.send_application(...)
    assert success is True
    
    # Move to sent
    move_to_sent(pending_file)
    assert not pending_file.exists()
```

## Test Fixtures

### Shared Fixtures (`conftest.py`)

#### Application Fixtures
```python
@pytest.fixture
def app():
    """Flask application with test configuration"""
    
@pytest.fixture
def client(app):
    """Test client for making requests"""
    
@pytest.fixture
def db_session(app):
    """Database session with transaction rollback"""
```

#### Data Fixtures
```python
@pytest.fixture
def sample_match():
    """Sample job match data"""
    
@pytest.fixture
def sample_letter():
    """Sample motivation letter data"""
    
@pytest.fixture
def sample_scraped_data():
    """Sample scraped job posting data"""
    
@pytest.fixture
def sample_queue_application():
    """Sample queue application"""
```

#### Workspace Fixtures
```python
@pytest.fixture
def temp_workspace():
    """Temporary directory with job_matches structure"""
    
@pytest.fixture
def create_test_files(temp_workspace):
    """Factory to create test JSON/HTML files"""
```

#### Mock Fixtures
```python
@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Mock Gmail environment variables"""
```

## Writing New Tests

### Test Structure Template

```python
class TestFeatureName:
    """Test suite for Feature X"""
    
    def test_basic_functionality(self):
        """Test basic happy path"""
        # Arrange
        input_data = create_test_data()
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_error_handling(self):
        """Test error conditions"""
        with pytest.raises(ExpectedException):
            function_that_should_fail()
    
    def test_edge_case(self):
        """Test boundary conditions"""
        # Test with empty, None, very large, Unicode, etc.
```

### Best Practices

1. **Use Descriptive Names**
   ```python
   # Good
   def test_validation_fails_when_email_missing():
   
   # Bad
   def test_val1():
   ```

2. **Test One Thing Per Test**
   ```python
   # Good - focused test
   def test_user_creation():
       user = User(username='test', email='test@example.com')
       assert user.username == 'test'
   
   # Bad - testing multiple things
   def test_user():
       user = User(...)
       assert user.username == 'test'
       assert user.check_password('pass')
       assert user.to_dict()['email'] == 'test@example.com'
   ```

3. **Use Fixtures for Setup**
   ```python
   @pytest.fixture
   def configured_service():
       service = MyService()
       service.configure(test_settings)
       return service
   
   def test_service_operation(configured_service):
       result = configured_service.do_something()
       assert result.success
   ```

4. **Test Both Success and Failure**
   ```python
   def test_validation_success():
       assert validator.validate(valid_data)['is_valid']
   
   def test_validation_failure():
       assert not validator.validate(invalid_data)['is_valid']
   ```

5. **Use Parametrize for Multiple Cases**
   ```python
   @pytest.mark.parametrize("email,expected", [
       ("valid@example.com", True),
       ("invalid-email", False),
       ("", False),
   ])
   def test_email_validation(email, expected):
       assert validate_email(email) == expected
   ```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for models and utilities
- **Integration Tests**: All critical workflows
- **Edge Cases**: Unicode, empty data, very large inputs
- **Error Handling**: Network failures, invalid data, missing credentials

## Current Coverage

### By Module

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| models/user.py | 25 | 95% | ✅ |
| models/application_context.py | 23 | 100% | ✅ |
| services/queue_bridge.py | 22 | 90% | ✅ |
| utils/email_sender.py | 10 | 85% | ✅ |
| utils/email_quality.py | 33 | 100% | ✅ |
| utils/validation.py | 27 | 95% | ✅ |
| utils/url_utils.py | 45 | 100% | ✅ |

### Total: 185+ passing tests

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure project root is in PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Database Errors**
   ```bash
   # Tests use in-memory SQLite, no setup needed
   # If issues persist, check models/__init__.py
   ```

3. **Mock Issues**
   ```bash
   # Ensure mocks are properly configured
   # Check conftest.py for fixture definitions
   ```

4. **Slow Tests**
   ```bash
   # Run only fast tests
   pytest tests/ -m "not slow"
   ```

## Future Enhancements

- [ ] Add performance benchmarks
- [ ] Implement mutation testing
- [ ] Add property-based testing with Hypothesis
- [ ] Create visual regression tests for UI
- [ ] Add load testing for email sending
- [ ] Implement contract testing for APIs

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Guide](https://coverage.readthedocs.io/)

## Support

For questions or issues with tests:
1. Check this documentation
2. Review existing tests for examples
3. Run tests with `-vv` for detailed output
4. Check test logs in `.pytest_cache/`

---
Last Updated: 2025-10-24
Test Count: 185+ passing
