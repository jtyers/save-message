import email
import os
import pytest
import shutil
import tempfile

from unittest.mock import MagicMock
from unittest.mock import call

from .context import save_message  # noqa: F401
from tests.util import assert_file_has_content
from tests.util import as_file
from tests.util import create_message_string

from save_message.model import Config
from save_message.rules import RulesMatcher
from save_message.save import get_message_name
from save_message.save import MessagePartSaver
from save_message.save import MessageSaver


@pytest.fixture
def temp_save_dir():
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def do_test_message_saver(
    temp_save_dir, expected_part_indexes: list, **create_message_args
):
    # given
    # use real MessagePartSaver - we consciously test both here,
    # as comparing Message/EmailMessage instances in mocks is hard
    message_part_saver = MessagePartSaver(config=Config)

    config = MagicMock(spec=Config)
    config.default_save_to = temp_save_dir

    rules_matcher = MagicMock(spec=RulesMatcher)

    message_string = create_message_string(template="simple_text_only")
    message = email.message_from_string(message_string)
    message_as_file = as_file(message_string)

    # when
    message_saver = MessageSaver(config, message_part_saver, rules_matcher)
    message_saver.save_message(message_as_file)

    # then

    # print([(x.get_payload(), x.get_content_type()) for x in message.walk()])
    # print(os.listdir(temp_save_dir))
    # print(os.listdir(temp_save_dir + "/" + os.listdir(temp_save_dir)[0]))

    message_name = get_message_name(message)
    message_save_dir = os.path.join(temp_save_dir, message_name)

    assert_file_has_content(
        os.path.join(message_save_dir, message_name + ".eml"),
        message_string,
    )

    assert_file_has_content(
        os.path.join(message_save_dir, message_name + "-02.txt"),
        "\n".join(
            [f"{h}: {message[h.lower()]}" for h in ["Date", "From", "To", "Subject"]]
            + ["", list(message.walk())[1].get_payload(decode=True).decode("utf-8")]
        ),
    )
