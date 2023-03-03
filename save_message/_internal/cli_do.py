import logging
import traceback

from save_message.maildir import Maildir
from save_message.maildir import Maildirs
from save_message.maildir import MaildirMessage
from save_message.save import MessageSaveException
from save_message.rules import RulesMatcher


logger = logging.getLogger(__name__)


def do_delete(args):
    maildirs: list[Maildir] = args.og.provide(Maildirs).get_maildirs()

    for maildir in maildirs:
        for k, m in maildir.search(
            subject=args.subject, from_=args.from_, to=args.to, date=args.date
        ):
            logger.info(f'deleting: {k}: {m["date"], m["from"], m["subject"]}')
            maildir.delete(k)


def do_apply_rules(args):
    maildirs: list[Maildir] = args.og.provide(Maildirs).get_maildirs()
    exceptions: list[tuple[str, MaildirMessage, Exception]] = []

    for maildir in maildirs:
        for k, m in maildir.search(
            subject=args.subject, from_=args.from_, to=args.to, date=args.date
        ):
            try:
                logger.info(f'apply_rules: {k}: {m["date"], m["from"], m["subject"]}')
                maildir.apply_rules(k)

            except Exception as ex:
                exceptions.append((k, m, ex))

    if exceptions:
        print("")
        print("The following messages encountered errors:")

        for k, m, ex in exceptions:
            if isinstance(ex, MessageSaveException):
                print(ex.message_name)

            else:
                print(m["date"], m["from"], m["subject"])

            for line in traceback.format_exception(None, ex, ex.__traceback__):
                print("  " + line)


def do_test_rule(args):
    maildirs: list[Maildir] = args.og.provide(Maildirs).get_maildirs()
    rules_matcher = args.og.provide(RulesMatcher)
    rule_id = args.id

    for maildir in maildirs:
        for k, m in maildir.search():
            rule = rules_matcher.match_save_rule(m)
            if rule.id == rule_id:
                logger.info(
                    f'test_rules: rule {rule.id} matches {m["date"], m["from"], m["subject"]}'
                )


def do_search(args):
    maildirs: list[Maildir] = args.og.provide(Maildirs).get_maildirs()

    for maildir in maildirs:
        for k, m in maildir.search(
            subject=args.subject, from_=args.from_, to=args.to, date=args.date
        ):
            logger.info(f'found: {k}: {m["date"], m["from"], m["subject"]}')
