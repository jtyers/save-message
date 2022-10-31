#!/usr/bin/python3

import argparse
import colorama
import logging
import os
import re
import sys
import tempfile

from save_message.config import load_config

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger(__name__)


def create_parser():
    # this method exists only so I can fold it and save some scrolling in my IDE...
    parser = argparse.ArgumentParser(description="save-message")
    parser.add_argument(
        "-c",
        "--cfg-file",
        help="Specify config file location",
        default="~/.config/save-message.yaml",
    )
    parser.add_argument(
        "--add-save-rule",
        action="store_true",
        help="Build a new save rule based on the given message's headers and open the config file in $EDITOR",
    )
    parser.add_argument(
        "-s", "--save-message", action="store_true", help="Save the given message"
    )
    parser.add_argument(
        "-P",
        "--prompt-save-dir-command",
        help="Save the message to a directory via the given command (e.g. `fzf`). The command will be run through the shell and should output the chosen directory on stdout. A non-zero exit code from the command, or blank output, will cause the script to abort.",
    )
    parser.add_argument(
        "-m",
        "--mkdirs",
        action="store_true",
        help="Create any non-existent directories",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Don't do anything, just log what we'd do",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Be more verbose (x2 for more)",
    )
    parser.add_argument(
        "input_files", nargs="*", help="Specify messages to add or save", default=["-"]
    )

    return parser


def verbose_msg(msg):
    s = f"""Incoming message:
  From: {msg['from']}
  Subject: {msg['subject']}"""
    logger.debug(s)


if __name__ == "__main__":
    colorama.init()

    parser = create_parser()
    args = parser.parse_args()

    if args.verbose == 0:
        level = logging.INFO
        global_level = logging.INFO
    if args.verbose == 1:
        level = logging.DEBUG
        global_level = logging.INFO
    if args.verbose >= 2:
        level = logging.DEBUG
        global_level = logging.INFO

    logger.basicConfig(stream=sys.stderr, format=LOG_FORMAT, level=level, force=True)
    logging.basicConfig(
        stream=sys.stderr, format=LOG_FORMAT, level=global_level, force=True
    )

    action = "save-message"
    if args.add_save_rule:
        action = "add-save-rule"

    config = load_config()

    if action == "save-message":
        tempfile.mkstemp(prefix="save-message-")

        for input_file in args.input_files:
            if input_file == "-":
                logger.debug("reading from stdin")
                save_message(
                    sys.stdin, prompt_save_dir_command=args.prompt_save_dir_command
                )
            else:
                logger.debug("reading from %s", input_file)
                with open(input_file, "r") as fi:
                    save_message(
                        fi, prompt_save_dir_command=args.prompt_save_dir_command
                    )

    elif action == "add-save-rule":
        add_save_rule(
            os.path.expanduser(os.path.expandvars(args.cfg_file)), args.input_files
        )
