import logging

from save_message.maildir import Maildir

logger = logging.getLogger(__name__)


def do_delete(args):
    maildir: Maildir = args.og.provide(Maildir)

    for k, m in maildir.search(
        subject=args.subject, from_=args.from_, to=args.to, date=args.date
    ):
        logger.info(f'deleting: {m["date"], m["from"], m["subject"]}')
        maildir.delete(k)


def do_apply_rules(args):
    maildir: Maildir = args.og.provide(Maildir)

    for k, m in maildir.search(
        subject=args.subject, from_=args.from_, to=args.to, date=args.date
    ):
        logger.info(f'apply_rules: {m["date"], m["from"], m["subject"]}')
        maildir.apply_rules(k)


def do_search(args):
    maildir: Maildir = args.og.provide(Maildir)

    for k, m in maildir.search(
        subject=args.subject, from_=args.from_, to=args.to, date=args.date
    ):
        logger.info(f'found: {k}: {m["date"], m["from"], m["subject"]}')
