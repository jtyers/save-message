from unittest.mock import MagicMock
from unittest.mock import patch

from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.matchers import Matcher
from save_message.matchers import OrMatcher
from save_message.model import Config
from save_message.model import RuleSettings
from save_message.model import SaveRule
from save_message.rules import RulesMatcher


def new_matching_matcher():
    r = MagicMock(spec=Matcher)
    r.matches.return_value = True
    return r


def new_non_matching_matcher():
    r = MagicMock(spec=Matcher)
    r.matches.return_value = False
    return r


def do_match_save_rule_test(
    mock_rule_matches_to_matcher,
    rule_matchers_result,
    default_settings=None,
    expected_save_rule=None,
):
    config = MagicMock(spec=Config)
    save_rule = sr()
    config.save_rules = [save_rule]

    if default_settings:
        config.default_settings = default_settings

    mock_rule_matches_to_matcher.return_value = rule_matchers_result

    msg = create_message(template="simple_text_only")
    rules_matcher = RulesMatcher(config)
    result = rules_matcher.match_save_rule(msg)

    assert result == (expected_save_rule or save_rule)


def sr():
    return SaveRule.construct(matches=[])


@patch("save_message.rules.rule_matches_to_matcher")
def test_match(mock_rule_matches_to_matcher):
    do_match_save_rule_test(
        mock_rule_matches_to_matcher,
        OrMatcher(
            [
                new_matching_matcher(),
                new_non_matching_matcher(),
                new_non_matching_matcher(),
            ]
        ),
    )


@patch("save_message.rules.rule_matches_to_matcher")
def test_no_match_returns_default_settings(
    mock_rule_matches_to_matcher,
):
    default_settings = MagicMock(spec=RuleSettings)
    do_match_save_rule_test(
        mock_rule_matches_to_matcher,
        OrMatcher(
            [
                new_non_matching_matcher(),
                new_non_matching_matcher(),
            ]
        ),
        default_settings=default_settings,
        expected_save_rule=SaveRule(settings=default_settings, matches=[]),
    )


# @patch("subprocess.run")
# def test_match_with_prompt(subprocess_run: MagicMock):
#     config = MagicMock(spec=Config)
#     config.save_rules = [
#         new_matching_matcher_set(),
#         new_non_matching_matcher(),
#         new_non_matching_matcher(),
#     ]
#
#     msg = create_message(template="simple_text_only")
#
#     prompt_response = "foo"
#
#     subprocess_run.return_value = CompletedProcess(
#         stdout=prompt_response, args=[], returncode=0
#     )
#
#     rules_matcher = RulesMatcher(config)
#     result = rules_matcher.match_save_rule_or_prompt(
#         msg, prompt_save_dir_command="echo"
#     )
#
#     assert result == SaveRule(
#         settings=RuleSettings(
#             action=MessageAction.SAVE_AND_DELETE,
#             save_settings=RuleSaveSettings(path=prompt_response),
#         )
#     )
#
#
# @patch("subprocess.run")
# def test_match_with_prompt_multiline_only_uses_first_line_of_output(
#     subprocess_run: MagicMock,
# ):
#     config = MagicMock(spec=Config)
#     config.save_rules = [
#         new_matching_matcher_set(),
#         new_non_matching_matcher(),
#         new_non_matching_matcher(),
#     ]
#
#     msg = create_message(template="simple_text_only")
#
#     prompt_response = """foo
# bar"""
#
#     subprocess_run.return_value = CompletedProcess(
#         stdout=prompt_response, args=[], returncode=0
#     )
#
#     rules_matcher = RulesMatcher(config)
#     result = rules_matcher.match_save_rule_or_prompt(
#         msg, prompt_save_dir_command="echo"
#     )
#
#     assert result == SaveRule(
#         settings=RuleSettings(
#             action=MessageAction.SAVE_AND_DELETE,
#             save_settings=RuleSaveSettings(path="foo"),
#         )
#     )
#
#
# @patch("subprocess.run")
# def test_match_with_prompt_no_output_raises(subprocess_run: MagicMock):
#     config = MagicMock(spec=Config)
#     config.save_rules = [MagicMock(spec=SaveRule)]
#
#     msg = create_message(template="simple_text_only")
#
#     prompt_response = ""
#
#     subprocess_run.return_value = CompletedProcess(
#         stdout=prompt_response, args=[], returncode=0
#     )
#
#     try:
#         rules_matcher = RulesMatcher(config)
#         rules_matcher.match_save_rule_or_prompt(msg, prompt_save_dir_command="echo")
#         assert False  # should have raised ValueError
#
#     except ValueError as ex:
#         assert str(ex) == "no output returned from prompt_save_dir_command"
