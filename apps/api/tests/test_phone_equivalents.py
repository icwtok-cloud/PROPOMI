"""Login de agencia: un mismo celular argentino se reconoce con o sin el 9 de móvil.

Run in the project environment with: pytest -q
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_propomi_suite.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ENV", "test")

from app.main import phone_equivalents


def test_mobile_with_nine_also_matches_without():
    assert phone_equivalents("+5491178222040") == ["+5491178222040", "+541178222040"]


def test_without_nine_also_matches_with():
    assert phone_equivalents("+541178222040") == ["+541178222040", "+5491178222040"]


def test_interior_area_code():
    assert phone_equivalents("+5493514567890") == ["+5493514567890", "+543514567890"]
    assert phone_equivalents("+543514567890") == ["+543514567890", "+5493514567890"]


def test_non_argentine_and_odd_lengths_untouched():
    assert phone_equivalents("+14155550123") == ["+14155550123"]
    assert phone_equivalents("+54911") == ["+54911"]
    assert phone_equivalents("") == [""]
