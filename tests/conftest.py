import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotel_dw.build import build  # noqa: E402


@pytest.fixture(scope="session")
def con():
    connection = build(":memory:")
    yield connection
    connection.close()


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]
