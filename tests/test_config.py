import os
import pytest
import shutil
import tempfile

from save_message.config import load_config
from save_message.model import Config
from save_message.model import ConfigMaildir
from save_message.model import MessageAction
from save_message.model import RuleSettings
from save_message.model import SaveRule


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def test_config(temp_save_dir):
    input = """
    default_save_to: /foo/bar

    maildir:
        path: /mail

    save_rules:
        - match_subject: Foo*
          match_from: bar*@example.com
          settings:
            action: KEEP

        - match_subject: Baz*
          match_from: bar*@example.com
          settings:
            action: SAVE_AND_DELETE

        - match_subject: Bat*
          match_from: bar*@example.com
          settings:
            action: IGNORE
            
        - match_subject: Bam*
          match_from: bar*@example.com
          settings:
            action: DELETE
    """
    filename = os.path.join(temp_save_dir, "config.yaml")
    with open(filename, "w") as c:
        c.write(input)

    config = load_config(filename)
    assert config == Config(
        maildir=ConfigMaildir(path="/mail"),
        default_save_to="/foo/bar",
        save_rules=[
            SaveRule(
                match_subject="Foo*",
                match_from="bar*@example.com",
                settings=RuleSettings(action=MessageAction.KEEP),
            ),
            SaveRule(
                match_subject="Baz*",
                match_from="bar*@example.com",
                settings=RuleSettings(action=MessageAction.SAVE_AND_DELETE),
            ),
            SaveRule(
                match_subject="Bat*",
                match_from="bar*@example.com",
                settings=RuleSettings(action=MessageAction.IGNORE),
            ),
            SaveRule(
                match_subject="Bam*",
                match_from="bar*@example.com",
                settings=RuleSettings(action=MessageAction.DELETE),
            ),
        ],
    )
