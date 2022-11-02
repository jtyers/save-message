from email.message import MIMEPart
from unittest.mock import MagicMock
from unittest.mock import patch

from .context import save_message  # noqa: F401
from tests.util import create_message

from save_message.save import get_filename_for_part
from save_message.save import MessagePartSaver

from subprocess import CompletedProcess


def run_get_filename_for_part_test(
    message_name, part_name, part_content_type, counter, expected
):
    part = MagicMock(spec=MIMEPart)
    part.get_filename.return_value = part_name
    part.get_content_type.return_value = part_content_type
    part.get_content_maintype.return_value = part_content_type.split("/")[0]

    assert get_filename_for_part(message_name, part, counter) == expected


def test_get_filename_for_part_text_file():
    run_get_filename_for_part_test(
        "my-message",
        "my-part",
        "text/plain",
        1,
        expected="my-part.txt",
    )


def test_get_filename_for_part_html_file():
    run_get_filename_for_part_test(
        "my-message",
        "my-part",
        "text/html",
        1,
        expected="my-part.html",
    )


def test_get_filename_for_part_honours_existing_extensions():
    run_get_filename_for_part_test(
        "my-message",
        "my-part.pdf",
        "text/html",
        1,
        expected="my-part.pdf",
    )


def test_get_filename_for_part_unknown_type_goes_to_bin():
    run_get_filename_for_part_test(
        "my-message",
        "my-part",
        "foo/bar",
        1,
        expected="my-part.bin",
    )


def test_get_filename_for_part_no_filename_uses_counter():
    run_get_filename_for_part_test(
        "my-message",
        None,
        "text/plain",
        10,
        expected="my-message-10.txt",
    )
