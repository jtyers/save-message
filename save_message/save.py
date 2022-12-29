import contextlib
from datetime import datetime
from email.message import EmailMessage
from email.message import MIMEPart
import email
import email.policy
from fnmatch import fnmatch
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
from save_message.model import RuleSaveSettings
from save_message.model import SaveRule
from save_message.model import merge_models

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


def get_message_name(msg, fmt: str):
    subject = sanitize_to_filename(msg["subject"])

    from_parts = email.utils.parseaddr(msg["from"])
    to_parts = email.utils.parseaddr(msg["to"])
    date = datetime.strptime(msg["date"], "%a, %d %b %Y %H:%M:%S %z")

    from_name = from_parts[0] or from_parts[1]
    from_addr = from_parts[1]
    to_name = to_parts[0] or to_parts[1]
    to_addr = to_parts[1]
    month_year = date.strftime("%b%y")
    day_month_year = date.strftime("%d%b%y")

    return fmt.format(
        subject=subject,
        from_name=from_name,
        from_addr=from_addr,
        to_name=to_name,
        to_addr=to_addr,
        month_year=month_year,
        date=day_month_year,
    )


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

        if os.path.exists(dest_path):
            raise ValueError(f"path {dest_path} exists, aborting")

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

            if os.path.exists(input_filename):
                raise ValueError(f"path {input_filename} exists, aborting")

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
    ):
        self.config = config
        self.message_part_saver = message_part_saver

    def save_message(self, msg: EmailMessage, rule: SaveRule):
        """Save the message in `input_file`, using rules to determine
        where to save. The rule is the rule whose actions should
        be applied; default_settings.save_settings are also taken  (from
        Config) into account.

        """
        merged_save_settings = merge_models(
            self.config.default_settings.save_settings, rule.settings.save_settings
        )
        message_name = get_message_name(msg, fmt=merged_save_settings.message_name)
        logger.debug("merged_save_settings=%s", merged_save_settings)

        dest_dir = os.path.join(merged_save_settings.path, message_name)
        dest_dir = os.path.expanduser(os.path.expandvars(dest_dir))

        logger.info("dest_dir=%s", dest_dir)
        os.makedirs(dest_dir, exist_ok=False)

        counter = 1

        if merged_save_settings.save_body:
            logger.debug("saving message body")
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
                        save_settings=merged_save_settings,
                    )
                    saved = True
                    break

            if not saved:
                raise ValueError(
                    f"could not find message body in a preferred format, the available body part content types are {body_parts.keys()}"
                )

        def part_is_matching_attachment(part):
            # we've seen some messages where part.is_attachment(), but it is clearly an attachment,
            # so we re-define an attachment as a part with a filename, even if it is not claiming
            # to be an attachment
            is_attachment = part.is_attachment() or part.get_filename()

            if merged_save_settings.save_attachments == "*":
                result = is_attachment

            else:
                result = is_attachment and fnmatch(
                    part.get_filename(), merged_save_settings.save_attachments
                )

            # logger.debug(
            #     "part_is_matching_attachment(save_attachments=%s part.is_attachment=%s part.get_filename=%s is_attachment=%s) = %s",
            #     merged_save_settings.save_attachments,
            #     part.is_attachment(),
            #     part.get_filename(),
            #     is_attachment,
            #     result,
            # )
            return result

        if merged_save_settings.save_attachments:
            for part in filter(
                part_is_matching_attachment,
                msg.walk(),
            ):
                logger.debug("saving attachment %s", part.get_filename())
                self.__save_part__(
                    msg=msg,
                    part=part,
                    dest_dir=dest_dir,
                    counter=counter,
                    msg_name_as_filename=False,
                    save_settings=merged_save_settings,
                )
                counter += 1

        if merged_save_settings.save_eml:
            logger.debug("saving message EML")
            # finally, write the entire message to a file in the new directory
            message_file_name = f"{message_name}.eml"
            message_path = os.path.join(dest_dir, message_file_name)

            if os.path.exists(message_path):
                raise ValueError(f"path {message_path} exists, aborting")

            with open(message_path, "wb") as f:
                f.write(msg.as_bytes())
                logger.debug("saved %s", message_file_name)

        # Once all files are written we examine whether
        # flatten_single_file_messages is enabled, and decide to flatten
        # based on the contents of dest_dir.
        if merged_save_settings.flatten_single_file_messages:
            saved_files = os.listdir(dest_dir)
            new_dest_dir = os.path.expanduser(
                os.path.expandvars(merged_save_settings.path)
            )

            if len(saved_files) == 1:
                logger.debug("flattening save dir into single file")
                # if a single file, then move to parent dir with same ext
                ext = saved_files[0][saved_files[0].rindex(".") :]

                message_single_file_name = f"{message_name}{ext}"
                shutil.move(
                    os.path.join(dest_dir, saved_files[0]),
                    os.path.join(new_dest_dir, message_single_file_name),
                )
                shutil.rmtree(dest_dir)

    def __save_part__(
        self,
        msg,
        part,
        dest_dir,
        msg_name_as_filename: bool,
        save_settings: RuleSaveSettings,
        counter=None,
    ):
        msg_name = get_message_name(msg, save_settings.message_name)
        filename, ext = get_filename_for_part(
            msg_name, part, counter, msg_name_as_filename=msg_name_as_filename
        )
        dest_path = os.path.join(dest_dir, filename)

        if (
            part.get_content_type() == "text/html"
            and save_settings.html_pdf_transform_command
        ):
            dest_path = dest_path[: dest_path.rindex(".")] + ".pdf"

            # ["prince", input_filename, "-o", dest_path]
            self.message_part_saver.save_html_part_to_pdf(
                msg=msg,
                part=part,
                dest_path=dest_path,
                html_pdf_transform_command=save_settings.html_pdf_transform_command,
            )
        else:
            self.message_part_saver.save_part(
                msg=msg,
                part=part,
                dest_path=dest_path,
            )
