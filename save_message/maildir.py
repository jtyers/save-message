from argparse import Namespace
from datetime import datetime
from email import message_from_string
from email.message import EmailMessage
from email import message_from_binary_file
from email.policy import default
import logging
import mailbox
from mailbox import MaildirMessage
from typing import Generator

from save_message.matchers import rule_matches_to_matcher
from save_message.model import Config
from save_message.model import MessageAction
from save_message.model import RuleMatch
from save_message.rules import RulesMatcher
from save_message.actions.actions import MessageActions

logger = logging.getLogger(__name__)


def make_EmailMessage(f):
    # https://stackoverflow.com/a/57550079/1432488
    """Factory to create EmailMessage objects instead of MaildirMessage objects"""
    return message_from_binary_file(f, policy=default)


class Maildir:
    def __init__(
        self,
        path: str,
        args: Namespace,
        rules_matcher: RulesMatcher,
        message_actions: MessageActions,
    ):
        self.args = args
        self.rules_matcher = rules_matcher
        self.message_actions = message_actions

        self.maildir = mailbox.Maildir(
            dirname=path, create=False, factory=make_EmailMessage
        )

    def get(self, key: str):
        return self.maildir.get(key)

    def delete(self, key: str, force: bool = False):
        if force or self.args.force_deletes:
            self.maildir.remove(key)

        else:
            msg = self.get(key)

            print()
            print(msg["date"], msg["from"], msg["subject"])
            response = input("Really delete this message? (type YES to proceed) ")
            print()

            if response == "YES":
                self.maildir.remove(key)
                print("  deleted")
            else:
                print("  skipped delete")

    def apply_rules(self, key):
        self.message_actions.apply_rules(self, key)

    def search(
        self,
        subject: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        date: datetime | None = None,
    ) -> Generator[MaildirMessage, None, None]:
        counter = 0

        save_rule_matcher = rule_matches_to_matcher(
            [
                RuleMatch(
                    subject=subject,
                    from_=from_,
                    to=to,
                    date=date,
                )
            ]
        )

        for k, m in self.maildir.iteritems():
            try:
                if save_rule_matcher.matches(m):
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


class Maildirs:
    def __init__(
        self,
        config: Config,
        args: Namespace,
        rules_matcher: RulesMatcher,
        message_actions: MessageActions,
    ):
        self.config = config
        self.args = args
        self.rules_matcher = rules_matcher
        self.message_actions = message_actions

    def get_maildirs(self) -> list[Maildir]:
        return [
            Maildir(
                path=m.path,
                args=self.args,
                rules_matcher=self.rules_matcher,
                message_actions=self.message_actions,
            )
            for m in self.config.maildirs
        ]
