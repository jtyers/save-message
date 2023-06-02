from datetime import datetime
from datetime import timedelta
from dateutil.parser import parse
from email.header import Header
from email.message import EmailMessage
from email.utils import parseaddr
from mailbox import MaildirMessage
import pudb
import re
import pytimeparse

from save_message.model import RuleMatch


def replace_all_items(s: str, replacements: dict) -> str:
    if replacements:
        for k, v in replacements.items():
            s = s.replace(k, v)

    return s


class Matcher:
    def matches(self, msg: MaildirMessage) -> bool:
        pass


class WildcardMatcher(Matcher):
    def __init__(
        self,
        match_criteria: str,
        replacements: dict = {},
        re_flags: int = 0,
        use_search: bool = False,
    ):
        """
        Create a WildcardMatcher.

        match_criteria should be the criteria specified to match, as a string.
        It can either be an exact match, a glob or a regex (must be enclosed
        in forward slashes).

        replacements, if specified, are a dict of replacements to perform
        on subject lines before matching.

        re_flags is the flags you want to use when creating patterns. You need
        to use bitwise OR to combine multiple flags (see re docs).

        use_search, if True, will cause re.search(), rather than the default
        re.match(), to be called. Search will find matches anywhere in the string, while match only matches from the start of the string.
        """
        # general approach is to cache as much as possible here, so
        # matching is fast, as a single matcher may be tested against
        # many hundreds of messages

        self.match_criteria = match_criteria
        self.use_search = use_search
        self.is_regex = self.match_criteria[0] == "/" and self.match_criteria[-1] == "/"

        if self.is_regex:
            self.pattern = re.compile(self.match_criteria[1:-1], flags=re_flags)

        else:
            # convert the fnmatch expression into a regex;
            self.pattern = re.compile(
                replace_all_items(
                    re.escape(self.match_criteria),
                    {
                        "\\*": ".+",
                        "\\?": ".",
                    },
                ),
                flags=re_flags,
            )

        self.replacements = replacements

    def __repr__(self):
        return f"WildcardMatcher(match_criteria={self.match_criteria})"

    def __matches_value__(self, value: str) -> bool:
        # pudb.set_trace()

        if value is None:
            return False

        if type(value) is Header:
            value = str(value)

        if self.replacements:
            for k, v in self.replacements.items():
                value = re.sub(k, v, value)

        if self.use_search:
            return self.pattern.search(value) is not None
        else:
            return self.pattern.match(value) is not None


class SubjectMatcher(WildcardMatcher):
    def __init__(self, match_subject):
        super().__init__(
            match_subject,
            replacements={
                "\n.*": "",  # strip newlines
            },
        )

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


class BodyMatcher(WildcardMatcher):
    def __init__(self, match_body: str):
        super().__init__(
            match_body,
            re_flags=re.MULTILINE,
            use_search=True,
        )

    def __repr__(self):
        return f"BodyMatcher(to={self.match_criteria})"

    def matches(self, msg: EmailMessage) -> bool:
        # First collate the 'body parts', i.e. non-attachments, which
        # make up the body of the messge. We aim to save only one of
        # these
        body_parts = {
            x.get_content_type(): x
            for x in filter(lambda x: not x.is_attachment(), msg.walk())
        }

        # lifted from save.MessageSaver/MessagePartSaver
        for preferred_content_type in ["text/html", "text/plain"]:
            if preferred_content_type in body_parts.keys():
                part = body_parts[preferred_content_type]

                payload = part.get_payload(decode=True)
                return self.__matches_value__(payload.decode())

        # if we get here, no payloads  matched our desired mime types, so no match
        return False

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is BodyMatcher
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
        if isinstance(match_date, datetime):
            self.match_date = match_date
        else:
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


class AgeMatcher(Matcher):
    def __init__(self, spec: str):
        print(spec, pytimeparse.parse(spec))
        self.match_date = datetime.now() - timedelta(seconds=pytimeparse.parse(spec))

    def __repr__(self):
        return f"AgeMatcher(match_date={self.match_date})"

    def matches(self, msg: MaildirMessage) -> bool:
        msg_date = parse(msg["date"])

        # need to compare timestamps, otherwise we get
        # "can't compare offset-aware and offset-naive datetimes"
        return self.match_date.timestamp() >= msg_date.timestamp()

    def __eq__(self, other) -> bool:
        return (
            other is not None
            and type(other) is AgeMatcher
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
        if rule_match.age:
            matchers.append(AgeMatcher(spec=rule_match.age))
        if rule_match.body:
            matchers.append(BodyMatcher(match_body=rule_match.body))

        or_matcher_matches.append(AndMatcher(matchers))

    return OrMatcher(or_matcher_matches)
