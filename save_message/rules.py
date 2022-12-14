from email.message import EmailMessage
import email.policy
import logging
import os
import subprocess
import sys

import ruamel.yaml

from save_message.config import Config
from save_message.config import DEFAULT_SAVE_TO
from save_message.matchers import rule_matches_to_matcher
from save_message.model import SaveRule

logger = logging.getLogger(__name__)


class RulesMatcher:
    """Manages matching messages to the loaded rules"""

    def __init__(self, config: Config):
        self.config = config

    def match_save_rule(self, msg: EmailMessage) -> SaveRule:
        """Find the first save_rule in the config that matches the given
        message. If prompt_save_dir_command is given, we instead generate
        a new (otherwise blank) SaveRule with the save_dir set to the
        output from that command, and return it."""

        #         if prompt_save_dir_command:
        #             logger.debug("running %s", shlex.split(prompt_save_dir_command))
        #             output = subprocess.run(
        #                 prompt_save_dir_command,
        #                 text=True,
        #                 check=True,
        #                 shell=True,
        #                 stdout=subprocess.PIPE,
        #                 # capture_output=True,
        #                 # leave stdin and stderr non-piped so they are passed to
        #                 # the terminal (needed for fzf)
        #             )
        #             logger.debug("done")
        #
        #             lines = output.stdout.split("\n")
        #             if len(lines) == 0:
        #                 raise ValueError("no output returned from prompt_save_dir_command")
        #
        #             logger.debug(" -> %s", lines)
        #             output_dir = lines[0]
        #             if not output_dir.strip():
        #                 raise ValueError("no output returned from prompt_save_dir_command")
        #
        #             return SaveRule(
        #                 settings=RuleSettings(
        #                     action=MessageAction.SAVE_AND_DELETE,
        #                     save_settings=RuleSaveSettings(path=output_dir),
        #                 )
        #             )
        #
        for save_rule in self.config.save_rules:
            save_rule_matcher = rule_matches_to_matcher(save_rule.matches)
            if save_rule_matcher.matches(msg):
                return save_rule

        return SaveRule(settings=self.config.default_settings, matches=[])


class RulesAdder:
    def add_save_rule(self, cfg_file: str, input_files: list[str]):
        yaml = ruamel.yaml.YAML()

        yaml.indent(mapping=4, sequence=4, offset=2)
        yaml.default_flow_style = False
        yaml.preserve_quotes = True

        with open(cfg_file, "r") as fc:
            new_config = yaml.load(fc)

        for input_file in input_files:
            if input_file == "-":
                msg = email.message_from_file(sys.stdin, policy=email.policy.default)
            else:
                with open(input_file, "r") as fm:
                    msg = email.message_from_file(fm, policy=email.policy.default)

            # verbose_msg(msg)
            new_config["save_rules"].append(
                {
                    "match_subject": str(msg["subject"]),
                    "match_to": str(msg["to"]),
                    "match_from": str(msg["from"]),
                    "save_to": DEFAULT_SAVE_TO,
                }
            )

        with open(cfg_file, "w") as fc:
            yaml.dump(new_config, fc)

        editor = os.environ.get("EDITOR") or "vi"

        subprocess.run([editor, cfg_file], check=True)
