import email
import email.policy
import logging
import os
import shlex
import subprocess
import sys

import ruamel.yaml

from save_message.config import DEFAULT_SAVE_TO
from save_message.model import SaveRule

logger = logging.getLogger(__name__)


def match_save_rule_or_prompt(msg, prompt_save_dir_command=None):
    """Find all save rules in the config that match the given message, or run prompt_save_dir_command
    instead if specified."""

    if prompt_save_dir_command:
        logger.debug("running %s", shlex.split(prompt_save_dir_command))
        output = subprocess.run(
            prompt_save_dir_command,
            text=True,
            check=True,
            shell=True,
            stdout=subprocess.PIPE,
            # capture_output=True,
            # leave stdin and stderr non-piped so they are passed to the terminal (needed for fzf)
        )
        logger.debug("done")

        # stdout, stderr = output.communicate()

        # print(output.stderr, file=sys.stderr)

        lines = output.stdout.split("\n")
        if len(lines) == 0:
            raise ValueError("no output returned from prompt_save_dir_command")

        logger.debug(" -> %s", lines)
        output_dir = lines[0]
        if not output_dir.strip():
            raise ValueError("no output returned from prompt_save_dir_command")

        return [SaveRule(save_to=output_dir)]

    else:
        result = []
        for s in config.save_rules:
            if s.matches(msg):
                result.append(s)

        return result


def add_save_rule(cfg_file, input_files):
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

        verbose_msg(msg)
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
