import os
import pytest
import shutil
import tempfile

from save_message.config import load_config
from save_message.model import Config
from save_message.model import SaveRule


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def test_config(temp_save_dir):
    input = """
    default_save_to: /foo/bar
    """
    filename = os.path.join(temp_save_dir, "config.yaml")
    with open(filename, "w") as c:
        c.write(input)

    config = load_config(filename)
    assert config == Config(default_save_to="/foo/bar")
