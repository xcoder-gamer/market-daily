import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from marketdaily import config  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    (tmp_path / "data").mkdir()
    src = Path(__file__).resolve().parent.parent / "data" / "holidays.json"
    (tmp_path / "data" / "holidays.json").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return config.Settings(root=tmp_path, site_url="https://example.org", base_path="")
