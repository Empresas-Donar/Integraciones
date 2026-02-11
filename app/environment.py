"""
Environment configuration and safety checks.
"""
import os
from pathlib import Path

# Only load dotenv if .env file exists (not needed in Cloud Run)
env_file = Path('.env')
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv()

ENV = os.getenv('ENV', 'development')
DATABASE_URL = os.getenv('DATABASE_URL', '')


def is_local_database(url: str) -> bool:
    """Check if database URL points to a local instance."""
    local_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
    return any(host in url for host in local_hosts)


def is_production() -> bool:
    """Check if running in production environment."""
    return ENV == 'production'


def validate_environment():
    """
    Safety check: prevent accidental production database access in development.
    Raises RuntimeError if attempting to connect to remote DB without production flag.
    """
    if not is_production() and not is_local_database(DATABASE_URL):
        raise RuntimeError(
            f"SAFETY CHECK: Attempting to connect to remote database in {ENV} environment. "
            "Set ENV=production or use a local DATABASE_URL in .env.local"
        )


# Run validation on import
validate_environment()
