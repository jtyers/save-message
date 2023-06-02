from __future__ import annotations
from email.message import EmailMessage
import logging

from save_message.model import MessageAction
from save_message.rules import SaveRule

logger = logging.getLogger(__name__)


class IgnoreRuleAction:
    def matches_message_action(self, action: MessageAction) -> bool:
        return action == MessageAction.IGNORE

    def perform_action(
        self,
        maildir,  # Maildir, but must avoid type (and pass in, not
        # inject), otherwise we get import cycles
        messageKey: str,
        message: EmailMessage,
        rule: SaveRule,
    ) -> None:
        logger.debug(
            "IgnoreRuleAction.perform_action: %s matches %s", messageKey, rule.matches
        )
        pass  # do nowt
