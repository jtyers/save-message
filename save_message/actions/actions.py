from email.message import EmailMessage
import logging
from typing import Any

from save_message.model import MessageAction
from save_message.rules import RulesMatcher
from save_message.rules import SaveRule
from save_message.actions.save_and_delete_action import SaveAndDeleteRuleAction
from save_message.actions.keep_action import KeepRuleAction
from save_message.actions.ignore_action import IgnoreRuleAction
from save_message.actions.delete_action import DeleteRuleAction

logger = logging.getLogger(__name__)


class RuleAction:
    """Interface that denotes an action we can take in response to a SaveRule.
    Actions need a MessageAction enum entry defined for them, which we use in
    the config to identify a particular action.
    """

    def matches_message_action(self, action: MessageAction) -> bool:
        """Should return True if this RuleAction can handle the given MessageAction."""
        pass

    def perform_action(
        self,
        messageKey: str,
        message: EmailMessage,
        rule: SaveRule,
    ) -> Any:
        """Performs the action against the given message."""
        pass


class MessageActions:
    def __init__(
        self,
        save_and_delete_rule_action: SaveAndDeleteRuleAction,
        keep_rule_action: KeepRuleAction,
        ignore_rule_action: IgnoreRuleAction,
        delete_rule_action: DeleteRuleAction,
        rules_matcher: RulesMatcher,
    ):
        self.actions = [
            save_and_delete_rule_action,
            keep_rule_action,
            ignore_rule_action,
            delete_rule_action,
        ]
        self.rules_matcher = rules_matcher

    def apply_rules(self, maildir, key: str):
        msg = maildir.get(key)
        assert isinstance(msg, EmailMessage)

        rule = self.rules_matcher.match_save_rule(msg)

        for action in self.actions:
            if action.matches_message_action(rule.settings.action):
                return action.perform_action(maildir, key, msg, rule)

        raise ValueError(f"unhandled MessageAction {rule.settings.action}")
