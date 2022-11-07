import email
from email.message import EmailMessage
import os
import pytest
import shutil
import tempfile

from unittest.mock import MagicMock
from unittest.mock import patch

from .context import save_message  # noqa: F401
from tests.util import assert_file_has_content
from tests.util import create_message

from save_message.model import Config
from save_message.model import MessageAction
from save_message.model import RuleSaveSettings
from save_message.model import RuleSettings
from save_message.model import SaveRule
from save_message.save import get_header_preamble
from save_message.save import get_message_name
from save_message.save import MessagePartSaver
from save_message.save import MessageSaver


@pytest.fixture
def temp_save_dir() -> str:
    result = tempfile.mkdtemp()
    yield result

    # shutil.rmtree(result)


def do_test_message_saver(
    temp_save_dir: str,
    message: EmailMessage,
    check_eml_file: bool,
    check_part_files: dict = {},
    check_part_binary_files: dict = {},
    rule_settings: RuleSettings = None,
):
    """Run the test to save the given message, then verify the .eml file is present and correct, then verify particular payload files have been created.

    check_part_files should be a dict of filename -> payload (as str).

    If rule is specified, this will be the rule returned by RulesMatcher for
    the message.
    """
    # given
    # use real MessagePartSaver - we consciously test both here,
    # as comparing Message/EmailMessage instances in mocks is hard
    message_part_saver = MessagePartSaver(config=Config)

    config = MagicMock(spec=Config)
    default_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(path=temp_save_dir),
    )
    config.default_settings = default_settings

    rule = SaveRule(settings=rule_settings or default_settings)

    # when
    message_saver = MessageSaver(config, message_part_saver)
    message_saver.save_message(message, rule)

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
        if not payload:
            continue

        assert_file_has_content(
            os.path.join(message_save_dir, filename),
            payload,
        )

    for filename, payload in check_part_binary_files.items():
        if not payload:
            continue

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


def test_simple_text_body_no_atts_with_save_eml_rule(temp_save_dir):
    message = create_message(template="simple_text_only")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=True,
        ),
    )

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=True,
        check_part_files={
            f"{message_name}.txt": "\n".join(
                [
                    get_header_preamble(message),
                    message_parts[1].get_payload(decode=True).decode("utf-8"),
                ]
            ),
        },
        rule_settings=rule_settings,
    )


def test_simple_text_body_no_atts_with_save_eml_rule_and_no_save_body(temp_save_dir):
    message = create_message(template="simple_text_only")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=True,
            save_body=False,
        ),
    )

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=True,
        check_part_files={},
        rule_settings=rule_settings,
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


def test_html_body_ics_att_with_html_pdf_transform(temp_save_dir):
    html_pdf_transform_command = "prince $in -o $out"
    message = create_message(template="text_html_with_calendar_attachment")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=False,
            html_pdf_transform_command=html_pdf_transform_command,
        ),
    )

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=False,
        check_part_files={
            f"{message_name}.pdf": None,  ## None means don't check content
            "invite.ics": message_parts[5].get_payload(decode=True).decode("utf-8"),
        },
        rule_settings=rule_settings,
    )


def test_html_body_ics_att_no_save_body(temp_save_dir):
    message = create_message(template="text_html_with_calendar_attachment")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=False,
            save_body=False,
        ),
    )

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=False,
        check_part_files={
            "invite.ics": message_parts[5].get_payload(decode=True).decode("utf-8"),
        },
        rule_settings=rule_settings,
    )


def test_html_body_ics_att_with_html_pdf_transform_no_save_body(temp_save_dir):
    html_pdf_transform_command = "prince $in -o $out"
    message = create_message(template="text_html_with_calendar_attachment")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=False,
            html_pdf_transform_command=html_pdf_transform_command,
            save_body=False,
        ),
    )

    do_test_message_saver(
        temp_save_dir=temp_save_dir,
        message=message,
        check_eml_file=False,
        check_part_files={
            "invite.ics": message_parts[5].get_payload(decode=True).decode("utf-8"),
        },
        rule_settings=rule_settings,
    )


def test_html_body_attachments_glob(temp_save_dir):
    message = create_message(template="text_html_with_multiple_large_attachments")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=False,
            save_attachments="IMG_7806*",
        ),
    )

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
        },
        check_part_binary_files={
            "IMG_7806 1 .JPG": message_parts[4].get_payload(decode=True),
        },
        rule_settings=rule_settings,
    )


def test_html_body_attachments_glob_2(temp_save_dir):
    message = create_message(template="text_html_with_multiple_large_attachments")
    message_parts = list(message.walk())
    message_name = get_message_name(message)

    rule_settings = RuleSettings(
        action=MessageAction.SAVE_AND_DELETE,
        save_settings=RuleSaveSettings(
            path=temp_save_dir,
            save_eml=False,
            save_attachments="IMG_7808*",
        ),
    )

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
        },
        check_part_binary_files={
            "IMG_7808 1 .JPG": message_parts[6].get_payload(decode=True),
        },
        rule_settings=rule_settings,
    )
