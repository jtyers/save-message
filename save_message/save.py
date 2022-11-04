from datetime import datetime
from email.message import EmailMessage
from email.message import MIMEPart
import email
import email.policy
from io import TextIOWrapper
import mimetypes
import logging
import os
import re
import subprocess
import tempfile

from save_message.config import DEFAULT_SAVE_TO
from save_message.rules import RulesMatcher
from save_message.model import Config

logger = logging.getLogger(__name__)


def sanitize_to_filename(s):
    """Really simple string sanitizer that strips all non-alphanumerics/spaces
    from the string before saving, so it is very filesystem safe."""
    result = re.sub(r"[^\w\s-]", " ", s)
    result = re.sub(r"\s+", " ", result)
    return result


def guess_ext_for_part(part):
    ext = mimetypes.guess_extension(part.get_content_type())
    if not ext:
        # Use a generic bag-of-bits extension
        ext = ".bin"

    return ext


def get_filename_for_part(message_name: str, part: MIMEPart, counter: int):
    filename = part.get_filename()

    if filename:
        if "." in filename:
            ext = filename[filename.index(".") :]
            filename = sanitize_to_filename(filename[: filename.index(".")]) + ext

        else:
            ext = guess_ext_for_part(part)
            filename = sanitize_to_filename(filename) + ext

    else:
        ext = guess_ext_for_part(part)
        filename = f"{message_name}-{counter:02d}{ext}"

    return filename, ext


def get_message_name(msg):
    subject = sanitize_to_filename(msg["subject"])

    from_parts = email.utils.parseaddr(msg["from"])
    date = datetime.strptime(msg["date"], "%a, %d %b %Y %H:%M:%S %z")

    name_from = from_parts[0] or from_parts[1]
    name_date = date.strftime("%b%y")

    return f"{name_from} {subject} {name_date}"


class MessagePartSaver:
    """Saves messages, optionally with some transformations, to a configured
    destination."""

    def __init__(self, config: Config):
        self.config = config

    def save_part(
        self,
        msg: EmailMessage,
        part: MIMEPart,
        message_name: str,
        dest_dir: str,
        counter: int,
    ):
        # multipart/* are just containers
        if part.get_content_maintype() == "multipart":
            return

        filename, ext = get_filename_for_part(message_name, part, counter)

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
        if ext == "html" and self.config.body.convert_html_to_pdf:
            dest_pdffilename = dest_filename[: -len(ext)] + ".pdf"
            subprocess.run(["prince", dest_filename, "-o", dest_pdffilename])


class MessageSaver:
    """Saves messages, optionally with some transformations, to a configured
    destination."""

    def __init__(
        self,
        config: Config,
        message_part_saver: MessagePartSaver,
        rules_matcher: RulesMatcher,
    ):
        self.config = config
        self.message_part_saver = message_part_saver
        self.rules_matcher = rules_matcher

    def save_message(self, msg: EmailMessage, prompt_save_dir_command: str = None):
        """Save the message in `input_file`, using rules to determine
        where to save. If prompt_save_dir_command is specified, that is treated
        as a command to run to determine the save location instead (generally it's
        expected that this command would prompt the user for a choice, e.g. via `fzf`).
        """

        # create a temporary file and save incoming data to it; the file is
        # opened with w+b, meaning write and read is possible, so we can then
        # re-feed the file to the email parser, and then write it all to a new
        # file in the output directory once we know what that directory is called
        #####   with tempfile.TemporaryFile(mode="w+") as fp:
        #####       for line in input_file:
        #####           fp.write(line)

        #####       fp.seek(0)
        #####       msg = email.message_from_file(fp, policy=email.policy.default)
        # verbose_msg(msg)

        message_name = get_message_name(msg)

        matching_rules = self.rules_matcher.match_save_rule_or_prompt(
            msg, prompt_save_dir_command
        )
        logger.debug("matching_rules: %s", matching_rules)
        rule = None

        if len(matching_rules) > 0:
            # find the first match with save_to specified
            rule = list(filter(lambda x: x.save_to, matching_rules))[0]

            dest_dir = os.path.join(rule.save_to, message_name)
        else:
            dest_dir = os.path.join(
                self.config.default_save_to or DEFAULT_SAVE_TO, message_name
            )

        dest_dir = os.path.expanduser(os.path.expandvars(dest_dir))

        logger.info("saving to %s", dest_dir)
        os.makedirs(dest_dir, exist_ok=True)

        counter = 1
        for part in msg.walk():
            self.message_part_saver.save_part(
                msg=msg,
                part=part,
                message_name=message_name,
                counter=counter,
                dest_dir=dest_dir,
            )
            counter += 1

        # finally, write the entire message to a file in the new directory
        message_file_name = f"{message_name}.eml"
        with open(os.path.join(dest_dir, message_file_name), "wb") as f:
            f.write(msg.as_bytes())
            logger.debug("saved %s", message_file_name)
