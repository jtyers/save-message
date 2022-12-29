import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from .context import save_message  # noqa: F401

from save_message.model import MessageAction
from save_message.model import RuleSettings
from save_message.model import SaveRule
from save_message.rules import RulesMatcher
from save_message.save import MessageSaver
from save_message import maildir


@pytest.fixture
@patch("mailbox.Maildir")
def maildir_(md):
    config = MagicMock()
    args = MagicMock()
    rules_matcher = MagicMock(spec=RulesMatcher)
    message_saver = MagicMock(spec=MessageSaver)

    return maildir.Maildir(
        config=config,
        args=args,
        rules_matcher=rules_matcher,
        message_saver=message_saver,
    )


@patch("save_message.maildir.input")
def do_delete_test(
    input_: MagicMock,
    maildir_,
    input_response: str,
    should_delete: bool,
    force_deletes: bool = False,
    force: bool = False,
):
    key = "key-123456abc"
    message = {
        "date": "yesterday",
        "from": "jonny@example.com",
        "subject": "My test message",
    }

    maildir_.maildir.get.return_value = message
    maildir_.args.force_deletes = force_deletes

    input_.return_value = input_response

    maildir_.delete(key, force=force)

    if not (force or force_deletes):
        # get() only called when we ask user for input
        maildir_.maildir.get.assert_called_with(key)

    if should_delete:
        maildir_.maildir.remove.assert_called_with(key)
    else:
        maildir_.maildir.remove.assert_not_called


def test_delete_with_prompt(maildir_):
    do_delete_test(
        maildir_=maildir_,
        input_response="YES",
        should_delete=True,
    )


def test_delete_with_prompt_cancelling(maildir_):
    do_delete_test(
        maildir_=maildir_,
        input_response="no",
        should_delete=False,
    )


def test_delete_with_force_deletes(maildir_):
    do_delete_test(
        maildir_=maildir_,
        force_deletes=True,
        input_response=None,
        should_delete=True,
    )


def test_delete_with_force(maildir_):
    do_delete_test(
        maildir_=maildir_,
        force=True,
        input_response=None,
        should_delete=True,
    )


@patch("save_message.maildir.message_from_string")
@patch("save_message.maildir.default")
def do_apply_rules_test(
    default,
    message_from_string,
    maildir_,
    rule: SaveRule,
    should_save: bool,
    should_delete: bool,
):
    key = "key-123456abc"
    message = {
        "date": "yesterday",
        "from": "jonny@example.com",
        "subject": "My test message",
    }
    email_message = {
        "em_date": "yesterday",
        "em_from": "jonny@example.com",
        "em_subject": "My test message",
    }
    message_from_string.return_value = email_message

    maildir_.maildir.get.return_value = message
    maildir_.rules_matcher.match_save_rule.return_value = rule

    maildir_.delete = MagicMock()

    maildir_.apply_rules(key)

    maildir_.maildir.get.assert_called_with(key)
    message_from_string.assert_called_with(str(message), policy=default)

    if should_delete:
        maildir_.delete.assert_called_with(key)
    else:
        maildir_.delete.assert_not_called

    if should_save:
        maildir_.message_saver.save_message.assert_called_with(email_message, rule)
    else:
        maildir_.message_saver.save_message.assert_not_called


def test_apply_rules_with_keep_action(maildir_):
    rule = MagicMock(spec=SaveRule)
    rule.settings = MagicMock(spec=RuleSettings)
    rule.settings.action = MessageAction.KEEP
    rule.matches = MagicMock()

    do_apply_rules_test(
        maildir_=maildir_, rule=rule, should_delete=False, should_save=True
    )
