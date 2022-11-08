import os
import pytest
import shutil
import tempfile

from tests.util import load_config_from_string

from save_message.model import Config
from save_message.model import ConfigMaildir
from save_message.model import MessageAction
from save_message.model import RuleMatch
from save_message.model import RuleSettings
from save_message.model import SaveRule


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def test_config(temp_save_dir):
    config = load_config_from_string(
        temp_save_dir,
        """
        default_save_to: /foo/bar

        maildir:
            path: /mail

        save_rules:
            - matches:
              - subject: Foo*
                from_addr: bar*@example.com
              settings:
                action: KEEP

            - matches:
              - to_name: Me
              - from_addr: bar*@example.com
              settings:
                action: SAVE_AND_DELETE

            - matches:
              - subject: Bat*
                from_name: bar*@example.com
              settings:
                action: IGNORE
                
            - matches:
              - subject: Bam*
                from_addr: bar*@example.com
              settings:
                action: DELETE
    """,
    )
    assert config == Config(
        maildir=ConfigMaildir(path="/mail"),
        default_save_to="/foo/bar",
        save_rules=[
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Foo*",
                        from_addr="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.KEEP),
            ),
            SaveRule(
                matches=[
                    RuleMatch(to_name="Me"),
                    RuleMatch(from_addr="bar*@example.com"),
                ],
                settings=RuleSettings(action=MessageAction.SAVE_AND_DELETE),
            ),
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Bat*",
                        from_name="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.IGNORE),
            ),
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Bam*",
                        from_addr="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.DELETE),
            ),
        ],
    )
