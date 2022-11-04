from unittest.mock import MagicMock
from unittest.mock import patch

from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.model import Config
from save_message.model import SaveRule
from save_message.rules import RulesMatcher

from subprocess import CompletedProcess


def new_matching_rule():
    r = MagicMock(spec=SaveRule)
    r.matches.return_value = True
    return r


def new_non_matching_rule():
    r = MagicMock(spec=SaveRule)
    r.matches.return_value = False
    return r


def test_match_without_prompt():
    config = Config()
    config.save_rules = [
        new_matching_rule(),
        new_non_matching_rule(),
        new_non_matching_rule(),
    ]

    msg = create_message(template="simple_text_only")

    rules_matcher = RulesMatcher(config)
    result = rules_matcher.match_save_rule_or_prompt(msg)

    assert result == config.save_rules[0]


@patch("subprocess.run")
def test_match_with_prompt(subprocess_run: MagicMock):
    config = Config()
    config.save_rules = [
        new_matching_rule(),
        new_non_matching_rule(),
        new_non_matching_rule(),
    ]

    msg = create_message(template="simple_text_only")

    prompt_response = "foo"

    subprocess_run.return_value = CompletedProcess(
        stdout=prompt_response, args=[], returncode=0
    )

    rules_matcher = RulesMatcher(config)
    result = rules_matcher.match_save_rule_or_prompt(
        msg, prompt_save_dir_command="echo"
    )

    assert result == SaveRule(save_to=prompt_response)


@patch("subprocess.run")
def test_match_with_prompt_multiline_only_uses_first_line_of_output(
    subprocess_run: MagicMock,
):
    config = Config()
    config.save_rules = [
        new_matching_rule(),
        new_non_matching_rule(),
        new_non_matching_rule(),
    ]

    msg = create_message(template="simple_text_only")

    prompt_response = """foo
bar"""

    subprocess_run.return_value = CompletedProcess(
        stdout=prompt_response, args=[], returncode=0
    )

    rules_matcher = RulesMatcher(config)
    result = rules_matcher.match_save_rule_or_prompt(
        msg, prompt_save_dir_command="echo"
    )

    assert result == SaveRule(save_to="foo")


@patch("subprocess.run")
def test_match_with_prompt_no_output_raises(subprocess_run: MagicMock):
    config = Config()
    config.save_rules = [
        new_matching_rule(),
        new_non_matching_rule(),
        new_non_matching_rule(),
    ]

    msg = create_message(template="simple_text_only")

    prompt_response = ""

    subprocess_run.return_value = CompletedProcess(
        stdout=prompt_response, args=[], returncode=0
    )

    try:
        rules_matcher = RulesMatcher(config)
        rules_matcher.match_save_rule_or_prompt(msg, prompt_save_dir_command="echo")
        assert False  # should have raised ValueError

    except ValueError as ex:
        assert str(ex) == "no output returned from prompt_save_dir_command"
