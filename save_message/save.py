import contextlib
from datetime import datetime
from email.message import EmailMessage
from email.message import MIMEPart
import email
import email.policy
import mimetypes
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile

from save_message.rules import RulesMatcher
from save_message.model import Config
from save_message.model import SaveRule

logger = logging.getLogger(__name__)


def get_header_preamble(message: EmailMessage, html: bool = False) -> str:
    if html:
        lines = [
            f"<p>{h}: {message[h.lower()]}</p>"
            for h in ["Date", "From", "To", "Subject"]
        ]
    else:
        lines = [
            f"{h}: {message[h.lower()]}" for h in ["Date", "From", "To", "Subject"]
        ]

    return "\n".join(lines) + "\n"


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


def get_filename_for_part(
    message_name: str, part: MIMEPart, counter: int, msg_name_as_filename: bool = False
):
    if msg_name_as_filename:
        part_filename = part.get_filename()

        if part_filename and "." in part_filename:
            ext = part_filename[part_filename.index(".") :]
        else:
            ext = guess_ext_for_part(part)
        filename = f"{message_name}{ext}"

    else:
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


@contextlib.contextmanager
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


class MessagePartSaver:
    """Saves messages, optionally with some transformations, to a configured
    destination."""

    def __init__(self, config: Config):
        self.config = config

    def save_part(
        self,
        msg: EmailMessage,
        part: MIMEPart,
        dest_path: str,
    ):
        """Save a message MIME part to a file.

        @param msg The EmailMessage the part came from
        @param part The part whose payload we are saving
        @param dest_path The filename to write the payload to
        """
        # multipart/* are just containers
        if part.get_content_maintype() == "multipart":
            return

        with open(dest_path, "wb") as fp2:
            # if this part is not an attachment, it is the body of the message, so
            # we prepend some headers to give context
            if not part.is_attachment() and part.get_content_maintype() == "text":
                preamble = get_header_preamble(
                    msg, html=part.get_content_type() == "text/html"
                )
                fp2.write(preamble.encode())
                fp2.write("\n".encode())

            fp2.write(part.get_payload(decode=True))

            logger.debug("saved %s", os.path.basename(dest_path))

    def save_html_part_to_pdf(
        self,
        msg: EmailMessage,
        part: MIMEPart,
        dest_path: str,
        html_pdf_transform_command: str,
    ):
        assert part.get_content_type() == "text/html"

        with temp_save_dir() as td:
            input_filename = os.path.join(td, "inputmsg")

            with open(input_filename, "wb") as f:
                f.write(part.get_payload(decode=True))

            subprocess.run(
                shlex.split(
                    html_pdf_transform_command.replace(
                        "$in", f'"{input_filename}"'
                    ).replace("$out", f'"{dest_path}"')
                ),
                check=True,
            )


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
        message_name = get_message_name(msg)

        rule = self.rules_matcher.match_save_rule_or_prompt(
            msg, prompt_save_dir_command
        )
        logger.debug("matching_rule: %s", rule)

        dest_dir = os.path.join(rule.settings.save_to, message_name)
        dest_dir = os.path.expanduser(os.path.expandvars(dest_dir))

        logger.info("saving to %s", dest_dir)
        os.makedirs(dest_dir, exist_ok=True)

        counter = 1

        # First collate the 'body parts', i.e. non-attachments, which
        # make up the body of the messge. We aim to save only one of
        # these
        body_parts = {
            x.get_content_type(): x
            for x in filter(lambda x: not x.is_attachment(), msg.walk())
        }

        saved = False
        for preferred_content_type in ["text/html", "text/plain"]:
            if preferred_content_type in body_parts.keys():
                self.__save_part__(
                    msg=msg,
                    part=body_parts[preferred_content_type],
                    dest_dir=dest_dir,
                    msg_name_as_filename=True,
                    rule=rule,
                )
                saved = True
                break

        if not saved:
            raise ValueError(
                f"could not find message body in a preferred format, the available body part content types are {body_parts.keys()}"
            )

        for part in filter(lambda x: x.is_attachment(), msg.walk()):
            self.__save_part__(
                msg=msg,
                part=part,
                dest_dir=dest_dir,
                counter=counter,
                msg_name_as_filename=False,
                rule=rule,
            )
            counter += 1

        if rule.settings.save_eml:
            # finally, write the entire message to a file in the new directory
            message_file_name = f"{message_name}.eml"
            with open(os.path.join(dest_dir, message_file_name), "wb") as f:
                f.write(msg.as_bytes())
                logger.debug("saved %s", message_file_name)

    def __save_part__(
        self,
        msg,
        part,
        dest_dir,
        msg_name_as_filename: bool,
        rule: SaveRule,
        counter=None,
    ):
        msg_name = get_message_name(msg)
        filename, ext = get_filename_for_part(
            msg_name, part, counter, msg_name_as_filename=msg_name_as_filename
        )
        dest_path = os.path.join(dest_dir, filename)

        if (
            part.get_content_type() == "text/html"
            and rule.settings.html_pdf_transform_command
        ):
            dest_path = dest_path[: dest_path.rindex(".")] + ".pdf"

            # ["prince", input_filename, "-o", dest_path]
            self.message_part_saver.save_html_part_to_pdf(
                msg=msg,
                part=part,
                dest_path=dest_path,
                html_pdf_transform_command=rule.settings.html_pdf_transform_command,
            )
        else:
            self.message_part_saver.save_part(
                msg=msg,
                part=part,
                dest_path=dest_path,
            )
