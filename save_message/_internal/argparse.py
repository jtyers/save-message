import argparse
import logging
from save_message._internal import cli_do

logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser(description="Maildir sorter and processor")
    parser.add_argument(
        "-c",
        "--cfg-file",
        help="Specify config file location",
        default="~/.config/save-message.yaml",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Be more verbose (x2 for more)",
    )

    parser.add_argument(
        "--force-deletes",
        action="store_true",
        default=False,
        help="Don't ask before deleting messages",
    )

    subparsers = parser.add_subparsers(help="sub-command help")

    do_search = subparsers.add_parser("search", help="Find messages")
    do_search.add_argument("--subject", help="Subject (can include wildcards)")
    do_search.add_argument("--to", help="To address (can include wildcards)")
    do_search.add_argument("--date", help="Date received")
    do_search.add_argument(
        "--from", dest="from_", help="From address (can include wildcards)"
    )
    do_search.set_defaults(func=cli_do.do_search)

    do_delete = subparsers.add_parser("delete", help="Delete messages")
    do_delete.add_argument("--subject", help="Subject (can include wildcards)")
    do_delete.add_argument("--to", help="To address (can include wildcards)")
    do_delete.add_argument("--date", help="Date received")
    do_delete.add_argument(
        "--from", dest="from_", help="From address (can include wildcards)"
    )
    do_delete.set_defaults(func=cli_do.do_delete)

    do_apply_rules = subparsers.add_parser(
        "apply-rules", help="Apply rules for messages"
    )
    do_apply_rules.add_argument("--subject", help="Subject (can include wildcards)")
    do_apply_rules.add_argument("--to", help="To address (can include wildcards)")
    do_apply_rules.add_argument("--date", help="Date received")
    do_apply_rules.add_argument(
        "--from", dest="from_", help="From address (can include wildcards)"
    )
    do_apply_rules.set_defaults(func=cli_do.do_apply_rules)

    do_test_rule = subparsers.add_parser("test-rule", help="Test a rule's matchers")
    do_test_rule.add_argument("--id", help="Rule ID to test")
    do_test_rule.set_defaults(func=cli_do.do_test_rule)

    return parser
