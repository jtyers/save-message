from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.model import MessageAction
from save_message.model import RuleSettings
from save_message.model import RuleSaveSettings
from save_message.model import SaveRule

settings = RuleSettings(
    action=MessageAction.SAVE_AND_DELETE, save_settings=RuleSaveSettings(path="/")
)


def test_save_rule_matches_glob_subject():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject=f"{subject}*", settings=settings)

    assert rule.matches(msg)


def test_save_rule_matches_regex_subject():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="/^my .+t$/", settings=settings)

    assert rule.matches(msg)


def test_save_rule_matches_glob_subject_fail():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="my sub*z", settings=settings)

    assert not rule.matches(msg)


def test_save_rule_matches_regex_subject_fail():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="/^my .+z$/", settings=settings)

    assert not rule.matches(msg)
