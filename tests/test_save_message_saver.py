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

#  import contextlib
#
#  @contextlib.contextmanager
#  def file_hanlder(file_name,file_mode):
#      file = open(file_name,file_mode)
#      yield file
#      file.close()


@pytest.fixture
def temp_save_dir():
    result = tempfile.mkdtemp()
    yield result

    shutil.rmtree(result)


def test_do_test_message_saver(temp_save_dir):
    # given
    # use real MessagePartSaver - we consciously test both here,
    # as comparing Message/EmailMessage instances in mocks is hard
    message_part_saver = MessagePartSaver(config=Config)

    config = MagicMock(spec=Config)
    config.default_save_to = temp_save_dir

    rules_matcher = MagicMock(spec=RulesMatcher)

    message_string = create_message_string(template="simple_text_only")
    message = email.message_from_string(message_string, policy=email.policy.default)

    # when
    message_saver = MessageSaver(config, message_part_saver, rules_matcher)
    message_saver.save_message(message)

    # then

    # print([(x.get_payload(), x.get_content_type()) for x in message.walk()])
    # print(os.listdir(temp_save_dir))
    # print(os.listdir(temp_save_dir + "/" + os.listdir(temp_save_dir)[0]))

    message_name = get_message_name(message)
    message_save_dir = os.path.join(temp_save_dir, message_name)

    with open(os.path.join(message_save_dir, message_name + ".eml"), "r") as wf:
        written_message = email.message_from_file(wf, policy=email.policy.default)
        for k, v in written_message.items():
            # these headers get reformatted/changed for some reason
            if k in ["Received"]:
                continue

            assert message[k].strip() == v.strip()

        assert [p.get_payload(decode=True) for p in message.walk()] == [
            p.get_payload(decode=True) for p in written_message.walk()
        ]

    assert_file_has_content(
        os.path.join(message_save_dir, message_name + "-02.txt"),
        "\n".join(
            [f"{h}: {message[h.lower()]}" for h in ["Date", "From", "To", "Subject"]]
            + ["", list(message.walk())[1].get_payload(decode=True).decode("utf-8")]
        ),
    )
