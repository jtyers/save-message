from datetime import datetime
import pytest
import shutil
import tempfile

from .context import save_message  # noqa: F401
from tests.util import create_message
from tests.util import load_config_from_string

from save_message.matchers import MatcherSet
from save_message.matchers import SubjectMatcher
from save_message.matchers import FromMatcher
from save_message.matchers import DateMatcher
from save_message.matchers import ToMatcher
from save_message.matchers import Matcher
from save_message.matchers import save_rule_to_matcher_sets
from save_message.model import RuleMatch


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def do_matcher_set_test(expected: bool, matchers: list[Matcher], **msg_args):
    msg = create_message(template="simple_text_only", **msg_args)

    matcher_set = MatcherSet(matchers=matchers)

    assert matcher_set.matches(msg) == expected


def test_subject():
    do_matcher_set_test(
        subject="Foo bar",
        matchers=[SubjectMatcher(match_subject="Foo *r")],
        expected=True,
    )


def test_from_address():
    do_matcher_set_test(
        from_="Jonny T <jonny@example.com>",
        matchers=[FromMatcher(match_from="jonny@*.com")],
        expected=True,
    )


def test_to_address():
    do_matcher_set_test(
        to="Jonny T <jonny@example.com>",
        matchers=[ToMatcher(match_to="Jonny T <jonny@example.com>")],
        expected=True,
    )


def test_to_address_regex():
    do_matcher_set_test(
        to="Jonny T <jonny@example.com>",
        matchers=[ToMatcher(match_to="/^Jonny T /")],
        expected=True,
    )


def do_save_rule_to_matcher_sets_test(
    temp_save_dir, expected: list[MatcherSet], rule_matches: list[RuleMatch]
):
    result = save_rule_to_matcher_sets(rule_matches)
    assert result == expected


def test_subject_save_rule(temp_save_dir):
    do_save_rule_to_matcher_sets_test(
        temp_save_dir,
        rule_matches=[
            RuleMatch(subject="Foo*"),
        ],
        expected=[MatcherSet(matchers=[SubjectMatcher(match_subject="Foo*")])],
    )


def test_all_fields_save_rule(temp_save_dir):
    now = datetime.now()

    do_save_rule_to_matcher_sets_test(
        temp_save_dir,
        rule_matches=[
            RuleMatch(
                subject="Foo*",
                to="test@example.com",
                from_="*@from.com",
                date=now.strftime("%c"),
            ),
        ],
        expected=[
            MatcherSet(
                matchers=[
                    SubjectMatcher(match_subject="Foo*"),
                    ToMatcher(match_to="test@example.com"),
                    FromMatcher(match_from="*@from.com"),
                    DateMatcher(match_date=now.strftime("%c")),
                ]
            )
        ],
    )
