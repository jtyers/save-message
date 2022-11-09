from datetime import datetime
import pytest
import shutil
import tempfile

from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.matchers import AndMatcher
from save_message.matchers import OrMatcher
from save_message.matchers import SubjectMatcher
from save_message.matchers import FromMatcher
from save_message.matchers import DateMatcher
from save_message.matchers import ToMatcher
from save_message.matchers import Matcher
from save_message.matchers import rule_matches_to_matcher
from save_message.model import RuleMatch


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def do_or_matcher_test(expected: bool, matchers: list[Matcher], **msg_args):
    msg = create_message(template="simple_text_only", **msg_args)

    matcher_set = OrMatcher(matchers=matchers)

    assert matcher_set.matches(msg) == expected


def test_subject():
    do_or_matcher_test(
        subject="Foo bar",
        matchers=[SubjectMatcher(match_subject="Foo *r")],
        expected=True,
    )


def test_from_address():
    do_or_matcher_test(
        from_="Jonny T <jonny@example.com>",
        matchers=[FromMatcher(match_from="jonny@*.com")],
        expected=True,
    )


def test_to_address():
    do_or_matcher_test(
        to="Jonny T <jonny@example.com>",
        matchers=[ToMatcher(match_to="Jonny T <jonny@example.com>")],
        expected=True,
    )


def test_to_address_regex():
    do_or_matcher_test(
        to="Jonny T <jonny@example.com>",
        matchers=[ToMatcher(match_to="/^Jonny T /")],
        expected=True,
    )


def do_rule_matches_to_matcher(
    temp_save_dir, expected: Matcher, rule_matches: list[RuleMatch]
):
    result = rule_matches_to_matcher(rule_matches)
    assert result == expected


def test_subject_save_rule(temp_save_dir):
    do_rule_matches_to_matcher(
        temp_save_dir,
        rule_matches=[
            RuleMatch(subject="Foo*"),
        ],
        expected=OrMatcher(
            matchers=[AndMatcher([SubjectMatcher(match_subject="Foo*")])]
        ),
    )


def test_all_fields_save_rule(temp_save_dir):
    now = datetime.now()

    do_rule_matches_to_matcher(
        temp_save_dir,
        rule_matches=[
            RuleMatch(
                subject="Foo*",
                to="test@example.com",
                from_="*@from.com",
                date=now.strftime("%c"),
            ),
        ],
        expected=OrMatcher(
            matchers=[
                AndMatcher(
                    [
                        SubjectMatcher(match_subject="Foo*"),
                        ToMatcher(match_to="test@example.com"),
                        FromMatcher(match_from="*@from.com"),
                        DateMatcher(match_date=now.strftime("%c")),
                    ]
                )
            ]
        ),
    )
