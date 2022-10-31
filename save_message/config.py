import os
import yaml

from save_message.model import Config


CONFIG_FILE = os.path.expanduser("~/.config/save-message.yaml")
DEFAULT_SAVE_TO = os.path.expanduser("~/saved-mail")


def load_config(config_file):
    if not os.path.exists(config_file):
        return Config()
    with open(config_file, "r") as f:
        cfg = yaml.safe_load(f)

        if not cfg:
            return Config()
        return Config(**cfg)
