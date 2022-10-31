#!/usr/bin/python3

import argparse
from datetime import datetime
import colorama
import email
import email.policy
import fnmatch
import logging
import mimetypes
from pydantic import BaseModel
import os
import re
import ruamel.yaml
import shlex
import subprocess
import sys
import tempfile
from typing import List
import yaml

DEFAULT_SAVE_TO = os.path.expanduser("~/saved-mail")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

config_file = os.path.expanduser("~/.config/save-message.yaml")

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


class SaveRule(BaseModel):
    # match on the subject, from and to fields
    # Match values are treated as globs and passed to fnmatch, unless the
    # match value is enclosed in forward slashes, in which case it's treated
    # as a regex.
    match_subject: str = None
    match_from: str = None
    match_to: str = None

    # The location to save the message to, which should be a folder. Environment
    # variables can be used here. The location must already exist.
    save_to: str

    def matches(self, msg):
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
                if match_field(_try, value):
                    any_match = True
                    break

            if not any_match:
                result = False

        return result


class ConfigBody(BaseModel):
    convert_html_to_pdf: bool = False


class Config(BaseModel):
    default_save_to: str = None
    body: ConfigBody = None

    save_rules: List[SaveRule] = []


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


def match_field(match_rule, value):
    """Find an individual value against a filter. Handles glob or regex filters."""
    if match_rule[0] == "/" and match_rule[-1] == "/":
        return re.match(match_rule[1:-1], value) != None

    else:
        return fnmatch.fnmatch(value, match_rule)


def load_config():
    if not os.path.exists(config_file):
        return Config()
    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

        if not cfg:
            return Config()
        return Config(**cfg)


def sanitize_to_filename(s):
    """Really simple string sanitizer that strips all non-alphanumerics/spaces
    from the string before saving, so it is very filesystem safe."""
    result = re.sub(r"[^\w\s-]", " ", s)
    result = re.sub(r"\s+", " ", result)
    return result


def verbose_msg(msg):
    s = f"""Incoming message:
  From: {msg['from']}
  Subject: {msg['subject']}"""
    logger.debug(s)


def guess_ext_for_part(part):
    ext = mimetypes.guess_extension(part.get_content_type())
    if not ext:
        # Use a generic bag-of-bits extension
        ext = ".bin"

    return ext


def save_part(msg, part, message_name, dest_dir, counter):
    # multipart/* are just containers
    if part.get_content_maintype() == "multipart":
        return

    filename = part.get_filename()
    if filename:
        filename = sanitize_to_filename(filename)

        if "." in filename:
            ext = filename[filename.index(".")]
        else:
            ext = guess_ext_for_part(part)
            filename = filename + ext

    else:
        ext = guess_ext_for_part(part)
        filename = f"{message_name}-{counter:03d}{ext}"

    counter += 1
    dest_filename = os.path.join(dest_dir, filename)
    with open(dest_filename, "wb") as fp2:
        # if this part is not an attachment, it is the body of the message, so
        # we prepend some headers to give context
        if not part.is_attachment() and part.get_content_maintype() == "text":
            for h in ["Date", "From", "To", "Subject"]:
                fp2.write(f"{h}: {msg[h.lower()]}\n".encode())
            fp2.write("\n".encode())

        fp2.write(part.get_payload(decode=True))

        logger.debug("saved %s", filename)

    # same as above, but if it was HTML and convert_html_to_pdf is on, convert
    # the HTML to PDF and save that alongside, using prince
    if ext == "html" and config.body.convert_html_to_pdf:
        dest_pdffilename = dest_filename[: -len(ext)] + ".pdf"
        subprocess.run(["prince", dest_filename, "-o", dest_pdffilename])


def save_message(input_file, prompt_save_dir_command=None):
    """Save the message in `input_file`, using rules to determine
    where to save. If prompt_save_dir_command is specified, that is treated
    as a command to run to determine the save location instead (generally it's
    expected that this command would prompt the user for a choice, e.g. via `fzf`).
    """

    # create a temporary file and save incoming data to it; the file is
    # opened with w+b, meaning write and read is possible, so we can then
    # re-feed the file to the email parser, and then write it all to a new
    # file in the output directory once we know what that directory is called
    with tempfile.TemporaryFile(mode="w+") as fp:
        for line in input_file:
            fp.write(line)

        fp.seek(0)
        msg = email.message_from_file(fp, policy=email.policy.default)
        verbose_msg(msg)

        subject = sanitize_to_filename(msg["subject"])

        from_parts = email.utils.parseaddr(msg["from"])
        date = datetime.strptime(msg["date"], "%a, %d %b %Y %H:%M:%S %z")

        name_from = from_parts[0] or from_parts[1]
        name_date = date.strftime("%b%y")
        message_name = f"{name_from} {subject} {name_date}"

        matching_rules = match_save_rule_or_prompt(msg, prompt_save_dir_command)
        logger.debug("matching_rules: %s", matching_rules)
        rule = None

        if len(matching_rules) > 0:
            # find the first match with save_to specified
            rule = list(filter(lambda x: x.save_to, matching_rules))[0]

            dest_dir = os.path.join(rule.save_to, message_name)
        else:
            dest_dir = os.path.join(
                config.default_save_to or DEFAULT_SAVE_TO, message_name
            )

        dest_dir = os.path.expanduser(os.path.expandvars(dest_dir))

        logger.info("saving to %s", dest_dir)
        os.makedirs(dest_dir, exist_ok=True)

        counter = 1
        for part in msg.walk():
            save_part(
                msg=msg,
                part=part,
                message_name=message_name,
                counter=counter,
                dest_dir=dest_dir,
            )

        # finally, re-read the raw input and write it to a file in the new directory
        fp.seek(0)
        message_file_name = f"{message_name}.eml"
        with open(os.path.join(dest_dir, message_file_name), "w") as f:
            for line in fp:
                f.write(line)
            logger.debug("saved %s", message_file_name)


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
