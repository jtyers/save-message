import email
from email.message import EmailMessage
import os
import subprocess

from save_message.config import load_config


def assert_file_has_content(filename, content, binary=False):
    with open(f"{filename}.desired", "wb" if binary else "w") as fdm:
        fdm.write(content)

    p = subprocess.run(
        ["diff", filename, f"{filename}.desired"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )

    if not p.stdout == "":
        raise AssertionError(f"file {os.path.basename(filename)} differs:\n{p.stdout}")


def create_message_string(
    template: str,
    to: str = "terftwminal@yahoo.com",
    from_: str = "Amazon Web Services <aws-verification@amazon.com>",
    date: str = "Sat, 11 Jun 2022 13:45:43 +0000",
    subject: str = "Your Request For Accessing AWS Resources Has Been Validated",
) -> EmailMessage:
    # template should match one of the templates in the templates/ dir

    tpl = os.path.join(os.path.dirname(__file__), "templates", template + ".template")
    with open(tpl, "r") as f:
        return f.read().format(
            **dict(to=to, from_=from_, date=date, subject=subject, template=template)
        )


def create_message(template: str, **kwargs) -> EmailMessage:
    # see message_from_string() for supported args
    return email.message_from_string(
        create_message_string(template, **kwargs), policy=email.policy.default
    )


def load_config_from_string(temp_save_dir, input_):
    filename = os.path.join(temp_save_dir, "config.yaml")
    with open(filename, "w") as c:
        c.write(input_)

    return load_config(filename)
