"""
Test configuration.

GWP and validator tests use no database.
Calculation tests use the real DATABASE_URL from .env.
"""
import pytest
