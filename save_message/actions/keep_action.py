from __future__ import annotations
from email.message import EmailMessage
import logging
from pydantic import BaseModel

from save_message.model import MessageAction
from save_message.rules import SaveRule
from save_message.save import MessageSaver

logger = logging.getLogger(__name__)


class KeepRuleActionResult(BaseModel):
    body_filename: str | None
    attachment_filenames: list[str]


class KeepRuleAction:
    def __init__(
        self,
        message_saver: MessageSaver,
    ):
        self.message_saver = message_saver

    def matches_message_action(self, action: MessageAction) -> bool:
        return action == MessageAction.KEEP

    def perform_action(
        self,
        maildir,  # Maildir, but must avoid type (and pass in, not
        # inject), otherwise we get import cycles
        messageKey: str,
        message: EmailMessage,
        rule: SaveRule,
    ) -> KeepRuleActionResult:
        logger.debug(
            "KeepRuleAction.perform_action: %s matches %s", messageKey, rule.matches
        )

        body_filename, attachment_filenames = self.message_saver.save_message(
            message, rule
        )

        return KeepRuleActionResult(
            body_filename=body_filename,
            attachment_filenames=attachment_filenames,
        )
