import email
from email.message import EmailMessage
import os
import pytest
import shutil
import tempfile

from unittest.mock import MagicMock

from .context import save_message  # noqa: F401
from tests.util import assert_file_has_content
from tests.util import create_message

from save_message.model import Config
from save_message.rules import RulesMatcher
from save_message.save import get_header_preamble
from save_message.save import get_message_name
from save_message.save import MessagePartSaver
from save_message.save import MessageSaver

#  import contextlib
#
#  @contextlib.contextmanager
#  def file_hanlder(file_name,file_mode):
#      file = open(file_name,file_mode)
#      yield file
#      file.close()


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def do_test_message_saver(
    temp_save_dir: str,
    message: EmailMessage,
    check_eml_file: bool,
    check_part_files: dict = {},
    check_part_binary_files: dict = {},
):
    """Run the test to save the given message, then verify the .eml file is present and correct, then verify particular payload files have been created.

    check_part_files should be a dict of filename -> payload (as str)."""
    # given
    # use real MessagePartSaver - we consciously test both here,
    # as comparing Message/EmailMessage instances in mocks is hard
    message_part_saver = MessagePartSaver(config=Config)

    config = MagicMock(spec=Config)
    config.default_save_to = temp_save_dir

    rules_matcher = MagicMock(spec=RulesMatcher)

    # when
    message_saver = MessageSaver(config, message_part_saver, rules_matcher)
    message_saver.save_message(message)

    # then

    message_name = get_message_name(message)
    message_save_dir = os.path.join(temp_save_dir, message_name)
    message_eml_file = os.path.join(message_save_dir, f"{message_name}.eml")

    if check_eml_file:
        with open(message_eml_file, "r") as wf:
            written_message = email.message_from_file(wf, policy=email.policy.default)
            for k, v in written_message.items():
                # these headers get reformatted/changed for some reason
                if k in ["Received", "Authentication-Results", "DKIM-Signature"]:
                    continue

                assert message[k].strip() == v.strip()

            assert [p.get_payload(decode=True) for p in message.walk()] == [
                p.get_payload(decode=True) for p in written_message.walk()
            ]

    # now check the full list of files is what we expect (we do this before
    # checking payloads as its helpful to get this error earlier)
    expected_files = list(check_part_files.keys()) + list(
        check_part_binary_files.keys()
    )
    if check_eml_file:
        expected_files.append(f"{message_name}.eml")
    expected_files.sort()

    actual_files = os.listdir(message_save_dir)
    actual_files.sort()

    assert actual_files == expected_files

    # finally, check file contents for each file specified, first in
    # text mode then in binary mode
    for filename, payload in check_part_files.items():
        assert_file_has_content(
            os.path.join(message_save_dir, filename),
            payload,
        )

    for filename, payload in check_part_binary_files.items():
        assert_file_has_content(
            os.path.join(message_save_dir, filename),
            payload,
            binary=True,
        )


def test_simple_text_body_no_atts(temp_save_dir):
    message = create_message(template="simple_text_only")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=False,
        check_part_files={
            f"{message_name}.txt": "\n".join(
                [
                    get_header_preamble(message),
                    message_parts[1].get_payload(decode=True).decode("utf-8"),
                ]
            ),
        },
    )


def test_html_body_ics_att(temp_save_dir):
    message = create_message(template="text_html_with_calendar_attachment")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=False,
        check_part_files={
            f"{message_name}.html": "\n".join(
                [
                    get_header_preamble(message, html=True),
                    message_parts[3].get_payload(decode=True).decode("utf-8"),
                ]
            ),
            "invite.ics": message_parts[5].get_payload(decode=True).decode("utf-8"),
        },
    )
