from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.model import SaveRule


def test_save_rule_matches_glob_subject():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject=f"{subject}*", save_to="/")

    assert rule.matches(msg)


def test_save_rule_matches_regex_subject():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="/^my .+t$/", save_to="/")

    assert rule.matches(msg)


def test_save_rule_matches_glob_subject_fail():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="my sub*z", save_to="/")

    assert not rule.matches(msg)


def test_save_rule_matches_regex_subject_fail():
    subject = "my subject"
    msg = create_message(template="simple_text_only", subject=subject)
    rule = SaveRule(match_subject="/^my .+z$/", save_to="/")

    assert not rule.matches(msg)
