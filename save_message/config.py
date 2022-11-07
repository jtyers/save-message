import os
import re
import yaml

from save_message.model import Config
from save_message.model import MessageAction


# CONFIG_FILE = os.path.expanduser("~/.config/save-message.yaml")
DEFAULT_SAVE_TO = os.path.expanduser("~/saved-mail")


def create_MessageAction(loader, node):
    value = loader.construct_scalar(node)
    # value = re.sub(r"[\s-]+", "_", value)
    return MessageAction[value.upper()]


def load_config(config_file):
    c = os.path.expanduser(config_file)

    yaml.add_constructor("message_action", create_MessageAction)
    yaml.add_implicit_resolver(
        "!message_action",
        re.compile(
            "|".join(
                [
                    x.lower()
                    for x in [
                        MessageAction.KEEP,
                        MessageAction.DELETE,
                        MessageAction.SAVE_AND_DELETE,
                        MessageAction.IGNORE,
                    ]
                ]
            )
        ),
    )

    with open(c, "r") as f:
        cfg = yaml.safe_load(f)
        return Config(**cfg)
