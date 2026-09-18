import pytest

from app.core.config import settings
from app.perception.engine import perception_engine


def test_perception_cache_reuse_flag_exists():
    assert settings.perception_cache is True
    perception_engine.reset()
    assert perception_engine._cache == {}
