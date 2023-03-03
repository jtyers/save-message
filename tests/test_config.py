import pytest
import shutil
import tempfile

from tests.util import load_config_from_string

from save_message.model import Config
from save_message.model import ConfigMaildir
from save_message.model import MessageAction
from save_message.model import RuleMatch
from save_message.model import RuleSettings
from save_message.model import RuleSaveSettings
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
        default_settings:
            save_settings:
                path: /foo/bar
            action: IGNORE

        maildirs:
           - path: /mail
           - path: /mail-again

        save_rules:
            - matches:
              - subject: Foo*
                from_: bar*@example.com
              settings:
                action: KEEP

            - matches:
              - to: Me
              - from_: bar*@example.com
              settings:
                action: SAVE_AND_DELETE

            - matches:
              - subject: Bat*
                from_: bar*@example.com
              settings:
                action: IGNORE
                
            - matches:
              - subject: Bam*
                from_: bar*@example.com
              settings:
                action: DELETE
    """,
    )
    assert config == Config(
        maildirs=[
            ConfigMaildir(path="/mail"),
            ConfigMaildir(path="/mail-again"),
        ],
        default_settings=RuleSettings(
            save_settings=RuleSaveSettings(
                path="/foo/bar",
            ),
            action=MessageAction.IGNORE,
        ),
        save_rules=[
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Foo*",
                        from_="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.KEEP),
            ),
            SaveRule(
                matches=[
                    RuleMatch(to="Me"),
                    RuleMatch(from_="bar*@example.com"),
                ],
                settings=RuleSettings(action=MessageAction.SAVE_AND_DELETE),
            ),
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Bat*",
                        from_="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.IGNORE),
            ),
            SaveRule(
                matches=[
                    RuleMatch(
                        subject="Bam*",
                        from_="bar*@example.com",
                    )
                ],
                settings=RuleSettings(action=MessageAction.DELETE),
            ),
        ],
    )
