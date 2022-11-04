import email
import io
import os
import tempfile


def as_file(s):
    """return the given string as a file object"""
    return io.StringIO(s)


def assert_file_has_content(filename, content):
    with open(filename, "r") as fm:
        file_content = fm.read()
        assert file_content.strip() == content.strip()


def create_message_string(
    template: str,
    to: str = "terftwminal@yahoo.com",
    from_: str = "Amazon Web Services <aws-verification@amazon.com>",
    date: str = "Sat, 11 Jun 2022 13:45:43 +0000",
    subject: str = "Your Request For Accessing AWS Resources Has Been Validated",
):
    # template should match one of the templates in the templates/ dir

    tpl = os.path.join(os.path.dirname(__file__), "templates", template + ".template")
    with open(tpl, "r") as f:
        return f.read().format(
            **dict(to=to, from_=from_, date=date, subject=subject, template=template)
        )


def create_message(**kwargs):
    # see message_from_string() for supported args
    return email.message_from_string(create_message_string(**kwargs))
