from datetime import datetime
from dateutil.parser import parse
from email.header import Header
from email.utils import parseaddr
import fnmatch
from mailbox import MaildirMessage
import re

from save_message.model import RuleMatch


class Matcher:
    def matches(self, msg: MaildirMessage) -> bool:
        pass


class WildcardMatcher(Matcher):
    def __init__(self, match_criteria):
        # general approach is to cache as much as possible here, so
        # matching is fast, as a single matcher may be tested against
        # many hundreds of messages
        self.match_criteria = match_criteria
        self.is_regex = self.match_criteria[0] == "/" and self.match_criteria[-1] == "/"
        self.pattern = (
            re.compile(self.match_criteria[1:-1])
            if self.is_regex
            else re.compile(fnmatch.translate(self.match_criteria))
        )

    def __repr__(self):
        return f"WildcardMatcher(match_criteria={self.match_criteria})"

    def __matches_value__(self, value: str) -> bool:
        if value is None:
            return False

        if type(value) is Header:
            value = str(value)

        return self.pattern.match(value) is not None


class SubjectMatcher(WildcardMatcher):
    def __init__(self, match_subject):
        super().__init__(match_subject)

    def __repr__(self):
        return f"SubjectMatcher(to={self.match_criteria})"

    def matches(self, msg: MaildirMessage) -> bool:
        return self.__matches_value__(msg["subject"])

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is SubjectMatcher
            and other.match_criteria == self.match_criteria
        )


class FromMatcher(WildcardMatcher):
    def __init__(self, match_from):
        super().__init__(match_from)

    def __repr__(self):
        return f"FromMatcher(to={self.match_criteria})"

    def matches(self, msg: MaildirMessage) -> bool:
        from_parts = parseaddr(msg["from"])
        return self.__matches_value__(from_parts[1]) or self.__matches_value__(
            msg["from"]
        )

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is FromMatcher
            and other.match_criteria == self.match_criteria
        )


class ToMatcher(WildcardMatcher):
    def __init__(self, match_to):
        super().__init__(match_to)

    def __repr__(self):
        return f"ToMatcher(to={self.match_criteria})"

    def matches(self, msg: MaildirMessage) -> bool:
        to_parts = parseaddr(msg["to"])
        return self.__matches_value__(to_parts[1]) or self.__matches_value__(msg["to"])

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is ToMatcher
            and other.match_criteria == self.match_criteria
        )


class DateMatcher(Matcher):
    def __init__(self, match_date: datetime):
        self.match_date = parse(match_date)

    def __repr__(self):
        return f"DateMatcher(match_date={self.match_date})"

    def matches(self, msg: MaildirMessage) -> bool:
        msg_date = parse(msg["date"])

        return self.match_date == msg_date

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is DateMatcher
            and other.match_date == self.match_date
        )


class AndMatcher(Matcher):
    def __init__(
        self,
        matchers: list[Matcher] = [],
    ):
        self.matchers = list(matchers)

    def __repr__(self):
        return f"AndMatcher(matchers={self.matchers})"

    def matches(self, msg):
        for matcher in self.matchers:
            if not matcher.matches(msg):
                return False

        return True

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is AndMatcher
            and other.matchers == self.matchers
        )


class OrMatcher(Matcher):
    def __init__(
        self,
        matchers: list[Matcher] = [],
    ):
        self.matchers = list(matchers)

    def __repr__(self):
        return f"OrMatcher(matchers={self.matchers})"

    def matches(self, msg):
        for matcher in self.matchers:
            if matcher.matches(msg):
                return True

        return False

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is OrMatcher
            and other.matchers == self.matchers
        )


def rule_matches_to_matcher(rule_matches: list[RuleMatch]) -> Matcher:
    """Creates a matcher that matches on the rules given in the
    list of RuleMatches. Each RuleMatch is treated as an OR, and
    the attributes in each RuleMatch are ANDed together."""
    or_matcher_matches = []

    for rule_match in rule_matches:
        matchers = []

        if rule_match.subject:
            matchers.append(SubjectMatcher(match_subject=rule_match.subject))
        if rule_match.to:
            matchers.append(ToMatcher(match_to=rule_match.to))
        if rule_match.from_:
            matchers.append(FromMatcher(match_from=rule_match.from_))
        if rule_match.date:
            matchers.append(DateMatcher(match_date=rule_match.date))

        or_matcher_matches.append(AndMatcher(matchers))

    return OrMatcher(or_matcher_matches)