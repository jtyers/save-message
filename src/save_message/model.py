import email
import email.policy
import fnmatch
import re
from typing import List

from pydantic import BaseModel


def match_field(match_rule, value):
    """Find an individual value against a filter. Handles glob or regex filters."""
    if match_rule[0] == "/" and match_rule[-1] == "/":
        return re.match(match_rule[1:-1], value) is not None

    else:
        return fnmatch.fnmatch(value, match_rule)


class SaveRule(BaseModel):
    # match on the subject, from and to fields
    # Match values are treated as globs and passed to fnmatch, unless the
    # match value is enclosed in forward slashes, in which case it's treated
    # as a regex.
    match_subject: str = None
    match_from: str = None
    match_to: str = None

    # The location to save the message to, which should be a folder. Environment
    # variables can be used here. The location must already exist.
    save_to: str

    def matches(self, msg):
        result = True

        from_parts = email.utils.parseaddr(msg["from"])
        to_parts = email.utils.parseaddr(msg["to"])

        tries = {
            self.match_subject: [msg["subject"]],
            self.match_from: [
                from_parts[1],
                msg["from"],
            ],  # match on email addr only first
            self.match_to: [to_parts[1], msg["to"]],  # match on email addr only first
        }

        for _try, values in tries.items():
            if not _try:
                continue

            any_match = False
            for value in values:
                if match_field(_try, value):
                    any_match = True
                    break

            if not any_match:
                result = False

        return result


class ConfigBody(BaseModel):
    convert_html_to_pdf: bool = False


class Config(BaseModel):
    default_save_to: str = None
    body: ConfigBody = None

    save_rules: List[SaveRule] = []
