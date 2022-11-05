from datetime import datetime
from dateutil.parser import parse
from email.header import Header
from email.utils import parseaddr
import fnmatch
import logging
import mailbox
from mailbox import MaildirMessage
import re
from typing import Generator

from save_message.model import Config

logger = logging.getLogger(__name__)


class WildcardMatcher:
    def __init__(self, match_criteria):
        self.match_criteria = match_criteria
        self.is_regex = self.match_criteria[0] == "/" and self.match_criteria[-1] == "/"
        self.pattern = re.compile(self.match_criteria[1:-1]) if self.is_regex else None

    def __matches_value__(self, value: str) -> bool:
        if value is None:
            return False

        if type(value) is Header:
            value = str(value)

        if self.is_regex:
            return self.pattern.match(value) is not None

        else:
            return fnmatch.fnmatch(value, self.match_criteria)


class SubjectMatcher(WildcardMatcher):
    def __init__(self, match_subject):
        super().__init__(match_subject)

    def matches(self, msg: MaildirMessage) -> bool:
        return self.__matches_value__(msg["subject"])


class FromMatcher(WildcardMatcher):
    def __init__(self, match_from):
        super().__init__(match_from)

    def matches(self, msg: MaildirMessage) -> bool:
        from_parts = parseaddr(msg["from"])
        return self.__matches_value__(from_parts[1]) or self.__matches_value__(
            msg["from"]
        )


class ToMatcher(WildcardMatcher):
    def __init__(self, match_to):
        super().__init__(match_to)

    def matches(self, msg: MaildirMessage) -> bool:
        to_parts = parseaddr(msg["to"])
        return self.__matches_value__(to_parts[1]) or self.__matches_value__(msg["to"])


class DateMatcher:
    def __init__(self, match_date: str):
        self.match_date = parse(match_date)

    def matches(self, msg: MaildirMessage) -> bool:
        msg_date = parse(msg["date"])

        return self.match_date == msg_date


class Matchers:
    def __init__(
        self,
        match_subject=None,
        match_from=None,
        match_to=None,
        match_date=None,
    ):
        self.matchers = []

        if match_subject:
            self.matchers.append(SubjectMatcher(match_subject))
        if match_from:
            self.matchers.append(FromMatcher(match_from))
        if match_to:
            self.matchers.append(ToMatcher(match_to))
        if match_date:
            self.matchers.append(DateMatcher(match_date))

    def matches(self, msg):
        for matcher in self.matchers:
            if not matcher.matches(msg):
                return False

        return True


class Maildir:
    def __init__(self, config: Config):
        self.config = config
        self.maildir = mailbox.Maildir(dirname=config.maildir.path, create=False)

    def delete(self, key):
        self.maildir.remove(key)

    def search(
        self,
        subject: str = None,
        from_: str = None,
        to: str = None,
        date: datetime = None,
    ) -> Generator[MaildirMessage, None, None]:
        counter = 0

        matchers = Matchers(
            match_subject=subject,
            match_from=from_,
            match_to=to,
            match_date=date,
        )

        for k, m in self.maildir.iteritems():
            try:
                if matchers.matches(m):
                    # em = message_from_string(str(m), policy=default)
                    yield (k, m)

                counter += 1

                if counter % 100 == 0:
                    logger.debug("scanned %d messages", counter)

            except Exception as ex:
                logger.error(
                    "error processing message: type=%s date='%s' "
                    + "from='%s' to='%s' subject='%s' ex='%s'",
                    type(m),
                    m["date"],
                    m["from"],
                    m["to"],
                    m["subject"],
                    ex,
                )

                # raise ex