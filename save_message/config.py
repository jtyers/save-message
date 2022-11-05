import os
import yaml

from save_message.model import Config


# CONFIG_FILE = os.path.expanduser("~/.config/save-message.yaml")
DEFAULT_SAVE_TO = os.path.expanduser("~/saved-mail")


def load_config(config_file):
    c = os.path.expanduser(config_file)

    with open(c, "r") as f:
        cfg = yaml.safe_load(f)
        return Config(**cfg)
