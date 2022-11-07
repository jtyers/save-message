from email.message import EmailMessage
import email
import email.policy
from enum import Enum
import fnmatch
import re
from typing import List

from pydantic import BaseModel


def match_field(match_rule: str, value: str) -> bool:
    """Find an individual value against a filter. Handles glob or regex filters."""
    if match_rule[0] == "/" and match_rule[-1] == "/":
        return re.match(match_rule[1:-1], value) is not None

    else:
        return fnmatch.fnmatch(value, match_rule)


class MessageAction(str, Enum):
    # keep  (save the message but keep in inbox)
    KEEP = "KEEP"

    # ignore  (do not save, leave in inbox)
    IGNORE = "IGNORE"

    # delete  (do not save, delete from inbox)
    DELETE = "DELETE"

    # save_and_delete  (save, delete from inbox)
    SAVE_AND_DELETE = "SAVE_AND_DELETE"


class RuleSaveSettings(BaseModel):
    # The location to save the message to, which should be a folder. Environment
    # variables can be used here. The location must already exist.
    path: str = None

    # If True, save full messages (as .eml files) in addition to
    # body/attachment saving.
    save_eml: bool = False

    # If True, save the message's body (either HTML or txt) under the save path
    save_body: bool = True

    # The attachments to save. Can either be a glob or, if the first
    # and last characters are forward-slashes, a regex.
    save_attachments: str | None = "*"

    # If set, this should be a command which reads an HTML file from the
    # path $in and writes a PDF to the path $out.
    html_pdf_transform_command: str = None

    # If set, where a message has just one file to save (after processing
    # save_body and save_attachments), save that file directly under 'path'
    # rather than in a directory for the message
    flatten_single_file_messages: bool = False


class RuleSettings(BaseModel):
    # action to take for matching messages
    action: MessageAction

    # settings for saving (if action includes this)
    save_settings: RuleSaveSettings = None


class SaveRule(BaseModel):
    # match on the subject, from and to fields
    # Match values are treated as globs and passed to fnmatch, unless the
    # match value is enclosed in forward slashes, in which case it's treated
    # as a regex.
    match_subject: str = None
    match_from: str = None
    match_to: str = None

    settings: RuleSettings

    def matches(self, msg: EmailMessage):
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
                if not value:
                    continue
                if match_field(_try, value):
                    any_match = True
                    break

            if not any_match:
                result = False

        return result


class ConfigBody(BaseModel):
    convert_html_to_pdf: bool = False


class ConfigMaildir(BaseModel):
    path: str


class Config(BaseModel):
    default_settings: RuleSettings = None

    maildir: ConfigMaildir

    body: ConfigBody = None

    save_rules: List[SaveRule] = []
