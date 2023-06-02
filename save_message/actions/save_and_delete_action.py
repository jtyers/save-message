from __future__ import annotations
from email.message import EmailMessage
import logging
from pydantic import BaseModel

from save_message.model import MessageAction
from save_message.rules import SaveRule
from save_message.actions.keep_action import KeepRuleAction
from save_message.actions.delete_action import DeleteRuleAction

logger = logging.getLogger(__name__)


class SaveAndDeleteRuleActionResult(BaseModel):
    body_filename: str | None
    attachment_filenames: list[str]


class SaveAndDeleteRuleAction:
    def __init__(
        self,
        keep_rule_action: KeepRuleAction,
        delete_rule_action: DeleteRuleAction,
    ):
        self.keep_rule_action = keep_rule_action
        self.delete_rule_action = delete_rule_action

    def matches_message_action(self, action: MessageAction) -> bool:
        return action == MessageAction.SAVE_AND_DELETE

    def perform_action(
        self,
        maildir,  # Maildir, but must avoid type (and pass in, not
        # inject), otherwise we get import cycles
        messageKey: str,
        message: EmailMessage,
        rule: SaveRule,
    ) -> SaveAndDeleteRuleActionResult:
        logger.debug(
            "SaveAndDeleteRuleAction.perform_action: %s matches %s",
            messageKey,
            rule.matches,
        )

        keep_result = self.keep_rule_action.perform_action(
            maildir,
            messageKey,
            message,
            rule,
        )

        self.delete_rule_action.perform_action(
            maildir,
            messageKey,
            message,
            rule,
        )

        return SaveAndDeleteRuleActionResult(
            body_filename=keep_result.body_filename,
            attachment_filenames=keep_result.attachment_filenames,
        )
