from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.model import MessageAction
from save_message.model import RuleSettings
from save_message.model import RuleSaveSettings
from save_message.model import SaveRule
from save_message.model import merge_models


def test_rule_settings_merge():
    settings_0 = RuleSettings(action=MessageAction.IGNORE)

    settings_1 = RuleSettings(
        action=MessageAction.KEEP,
        save_settings=RuleSaveSettings(
            path="/", save_body=False, save_attachments="*.jpg"
        ),
    )

    settings_2 = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(path="/2", save_eml=True),
    )

    assert merge_models(settings_0) == settings_0
    assert merge_models(settings_0, settings_1) == RuleSettings(
        action=MessageAction.KEEP,
        save_settings=RuleSaveSettings(
            path="/", save_body=False, save_attachments="*.jpg"
        ),
    )
    assert merge_models(settings_1, settings_2) == RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path="/2", save_body=False, save_eml=True, save_attachments="*.jpg"
        ),
    )

    assert merge_models(settings_0, settings_1, settings_2) == RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path="/2", save_body=False, save_eml=True, save_attachments="*.jpg"
        ),
    )

    assert merge_models(None, None) == None

    assert merge_models(settings_0, None) == settings_0

    assert merge_models(None, settings_1) == settings_1
