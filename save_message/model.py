from datetime import datetime
from email.message import EmailMessage
import email
import email.policy
from enum import Enum
import fnmatch
import re
from typing import List

from pydantic import BaseModel


# https://stackoverflow.com/a/7205107
def deep_merge_dicts(a, b, path=None):
    """Deep-merge two dicts together. b will be merged into a, thus keys
    in b take precedence, and a will be mutated. a is also returned."""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def merge_models(*args):
    """Merge multiple instances of the same type together. Intended to work
    for any list of Pydantic-modelled instances.

    Properties set in the last-specified instance will take
    precedence. This function uses pydantic's __fields_set__
    to determine the values of fields for each instance."""

    for arg in args:
        assert hasattr(arg, "__fields_set__") or arg is None

    # find the first non-None argument
    first = None
    largs = list(args)
    while first is None and len(largs) > 0:
        first = largs.pop(0)

    # if first is none, we must've exhausted the
    # list, which means all args were None
    if first is None:
        return None

    first_dict = dict(first)
    new_type = type(first)
    new_props = dict(first)

    if len(args) > 1:
        for arg in args:
            if arg is None:
                continue

            assert type(arg) == new_type
            arg_dict = dict(arg)

            for field in arg.__fields_set__:
                # for this field, merge it with the current value
                # in new_props, or first's value if not present
                cur = new_props.get(field, first_dict.get(field))

                if hasattr(cur, "__fields_set__"):
                    new_props[field] = merge_models(cur, arg_dict[field])

                else:
                    new_props[field] = getattr(arg, field)

    return first.copy(update=new_props)


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
    class Config:
        extra = "forbid"

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
    html_pdf_transform_command: str | None = None

    # If set, where a message has just one file to save (after processing
    # save_body and save_attachments), save that file directly under 'path'
    # rather than in a directory for the message
    flatten_single_file_messages: bool = False

    # How to name the message. This sets the name of the directory the
    # message's files are saved in, and the name of body-part files. If
    # flattening is enabled, this determines the name of the single file.
    # Available fields are {from_name}, {from_addr}, {to_name}, {to_addr},
    #   {subject}, {month_year}, {date} (day, month, year)
    message_name: str = "{from_name} {subject} {month_year}"


class RuleSettings(BaseModel):
    class Config:
        extra = "forbid"

    # action to take for matching messages
    action: MessageAction

    # for DELETE and SAVE_AND_DELETE actions, whether to prompt the user
    # before delete
    delete_confirmation: bool = True

    # settings for saving (if action includes this)
    save_settings: RuleSaveSettings = None


class RuleMatch(BaseModel):
    class Config:
        extra = "forbid"

    # match on the subject, from and to fields
    # Match values are treated as globs and passed to fnmatch, unless the
    # match value is enclosed in forward slashes, in which case it's treated
    # as a regex.
    subject: str = None
    from_: str = None
    to: str = None
    date: str = None


class SaveRule(BaseModel):
    class Config:
        extra = "forbid"

    # match on the subject, from and to fields
    # Match values are treated as globs and passed to fnmatch, unless the
    # match value is enclosed in forward slashes, in which case it's treated
    # as a regex.
    match_subject: str = None
    match_from: str = None
    match_to: str = None

    matches: list[RuleMatch]

    settings: RuleSettings


#     def matches(self, msg: EmailMessage):
#         result = True
#
#         from_parts = email.utils.parseaddr(msg["from"])
#         to_parts = email.utils.parseaddr(msg["to"])
#
#         tries = {
#             self.match_subject: [msg["subject"]],
#             self.match_from: [
#                 from_parts[1],
#                 msg["from"],
#             ],  # match on email addr only first
#             self.match_to: [to_parts[1], msg["to"]],  # match on email addr only first
#         }
#
#         for _try, values in tries.items():
#             if not _try:
#                 continue
#
#             any_match = False
#             for value in values:
#                 if not value:
#                     continue
#                 if match_field(_try, value):
#                     any_match = True
#                     break
#
#             if not any_match:
#                 result = False
#
#         return result


class ConfigBody(BaseModel):
    class Config:
        extra = "forbid"

    # convert_html_to_pdf: bool = False
    pass


class ConfigMaildir(BaseModel):
    class Config:
        extra = "forbid"

    path: str


class Config(BaseModel):
    class Config:
        extra = "forbid"

    default_settings: RuleSettings = None

    maildir: ConfigMaildir

    body: ConfigBody = None

    save_rules: List[SaveRule] = []
