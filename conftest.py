"""
Comprehensive pytest configuration and fixtures for the testing framework.

This module provides:
- Pytest configuration and hooks
- WebDriver fixtures for Selenium testing
- API client fixtures
- Logging configuration
- Test data management
- Database fixtures and utilities
"""

import pytest
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Generator, Optional

# Selenium WebDriver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# API testing
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Database
import sqlite3
import json


# ============================================================================
# Logging Configuration
# ============================================================================

def configure_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure logging for tests."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"test_run_{timestamp}.log"
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Initialize logger
logger = configure_logging(os.getenv("LOG_LEVEL", "INFO"))


# ============================================================================
# Pytest Configuration and Hooks
# ============================================================================

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--browser",
        action="store",
        default="chrome",
        help="Browser to use for testing (chrome, firefox, edge)",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8000",
        help="Base URL for API and web testing",
    )
    parser.addoption(
        "--db-path",
        action="store",
        default="test.db",
        help="Path to test database",
    )
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "webdriver: mark test as requiring webdriver")
    config.addinivalue_line("markers", "api: mark test as API testing")
    config.addinivalue_line("markers", "database: mark test as requiring database")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip slow tests if not requested."""
    if config.getoption("--slow"):
        return
    skip_slow = pytest.mark.skip(reason="need --slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


# ============================================================================
# WebDriver Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def browser_type(request) -> str:
    """Get browser type from command line option."""
    return request.config.getoption("--browser").lower()


@pytest.fixture(scope="session")
def headless_mode(request) -> bool:
    """Get headless mode from command line option."""
    return request.config.getoption("--headless")


def _create_chrome_driver(headless: bool):
    """Create Chrome WebDriver instance."""
    options = ChromeOptions()
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Disable notifications and popups
    prefs = {"profile.default_content_setting_values.notifications": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    logger.info("Chrome WebDriver initialized")
    return driver


def _create_firefox_driver(headless: bool):
    """Create Firefox WebDriver instance."""
    options = FirefoxOptions()
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    
    driver = webdriver.Firefox(options=options)
    logger.info("Firefox WebDriver initialized")
    return driver


def _create_edge_driver(headless: bool):
    """Create Edge WebDriver instance."""
    from selenium.webdriver.edge.options import Options as EdgeOptions
    
    options = EdgeOptions()
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Edge(options=options)
    logger.info("Edge WebDriver initialized")
    return driver


@pytest.fixture(scope="function")
def webdriver_instance(browser_type: str, headless_mode: bool):
    """Create and manage WebDriver instance."""
    if browser_type == "chrome":
        driver = _create_chrome_driver(headless_mode)
    elif browser_type == "firefox":
        driver = _create_firefox_driver(headless_mode)
    elif browser_type == "edge":
        driver = _create_edge_driver(headless_mode)
    else:
        raise ValueError(f"Unsupported browser: {browser_type}")
    
    driver.implicitly_wait(10)
    yield driver
    
    # Cleanup
    try:
        driver.quit()
        logger.info(f"{browser_type.capitalize()} WebDriver closed")
    except Exception as e:
        logger.error(f"Error closing WebDriver: {e}")


@pytest.fixture(scope="function")
def webdriver_wait(webdriver_instance):
    """WebDriverWait instance with 10 second timeout."""
    return WebDriverWait(webdriver_instance, 10)


# ============================================================================
# API Client Fixtures
# ============================================================================

class APIClient:
    """HTTP client for API testing with retry logic."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = self._create_session()
        self.logger = logging.getLogger(__name__)
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            backoff_factor=1,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.info(f"GET {url}")
        return self.session.get(url, timeout=self.timeout, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """POST request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.info(f"POST {url}")
        return self.session.post(url, json=data, timeout=self.timeout, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """PUT request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.info(f"PUT {url}")
        return self.session.put(url, json=data, timeout=self.timeout, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """DELETE request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.info(f"DELETE {url}")
        return self.session.delete(url, timeout=self.timeout, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """PATCH request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.info(f"PATCH {url}")
        return self.session.patch(url, json=data, timeout=self.timeout, **kwargs)
    
    def close(self):
        """Close the session."""
        self.session.close()


@pytest.fixture(scope="function")
def api_client(request) -> APIClient:
    """API client fixture with base URL from command line."""
    base_url = request.config.getoption("--base-url")
    client = APIClient(base_url)
    yield client
    client.close()


# ============================================================================
# Database Fixtures
# ============================================================================

class DatabaseManager:
    """SQLite database manager for tests."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> sqlite3.Connection:
        """Create database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        return cursor
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch a single row."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Fetch all rows."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
    
    def create_table(self, table_name: str, schema: Dict[str, str]):
        """Create a table."""
        columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.execute(query)
        self.logger.info(f"Table {table_name} created or verified")
    
    def insert(self, table_name: str, data: Dict[str, Any]):
        """Insert data into table."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data.values()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute(query, tuple(data.values()))
        self.logger.info(f"Data inserted into {table_name}")
    
    def delete_all(self, table_name: str):
        """Delete all rows from table."""
        query = f"DELETE FROM {table_name}"
        self.execute(query)
        self.logger.info(f"All data deleted from {table_name}")
    
    def drop_table(self, table_name: str):
        """Drop a table."""
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.execute(query)
        self.logger.info(f"Table {table_name} dropped")


@pytest.fixture(scope="function")
def database(request) -> DatabaseManager:
    """Database fixture."""
    db_path = request.config.getoption("--db-path")
    db = DatabaseManager(db_path)
    yield db
    
    # Cleanup: optionally remove database file after tests
    # if os.path.exists(db_path):
    #     os.remove(db_path)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get path to test data directory."""
    test_data = Path("tests/test_data")
    test_data.mkdir(parents=True, exist_ok=True)
    return test_data


@pytest.fixture(scope="function")
def sample_user_data() -> Dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "testuser@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture(scope="function")
def sample_api_response() -> Dict[str, Any]:
    """Sample API response data."""
    return {
        "status": "success",
        "code": 200,
        "data": {
            "id": 1,
            "name": "Sample Item",
            "description": "A sample item for testing",
            "created_at": datetime.now().isoformat(),
        },
        "message": "Request processed successfully",
    }


@pytest.fixture(scope="function")
def load_json_fixture(test_data_dir: Path):
    """Load JSON fixture files."""
    def _load(filename: str) -> Dict[str, Any]:
        file_path = test_data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {file_path}")
        with open(file_path, "r") as f:
            return json.load(f)
    return _load


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def capture_screenshot(webdriver_instance):
    """Capture screenshot on test failure."""
    def _capture(filename: str = None):
        screenshot_dir = Path("screenshots")
        screenshot_dir.mkdir(exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
            filename = f"screenshot_{timestamp}.png"
        
        filepath = screenshot_dir / filename
        webdriver_instance.save_screenshot(str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        return filepath
    
    return _capture


@pytest.fixture(scope="function")
def cleanup_files():
    """Cleanup temporary files created during tests."""
    files_to_cleanup = []
    
    def _add_file(filepath: str):
        files_to_cleanup.append(filepath)
    
    yield _add_file
    
    for filepath in files_to_cleanup:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up file: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up file {filepath}: {e}")


# ============================================================================
# Session and Test Hooks
# ============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add custom logging and information on test failure."""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        logger.error(f"FAILED: {item.nodeid}")
        logger.error(f"Error: {report.longrepr}")


def pytest_sessionstart(session):
    """Log test session start."""
    logger.info("=" * 80)
    logger.info(f"Test session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


def pytest_sessionfinish(session, exitstatus):
    """Log test session end."""
    logger.info("=" * 80)
    logger.info(f"Test session finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
