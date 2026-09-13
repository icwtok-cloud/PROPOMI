import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi_suite.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")
