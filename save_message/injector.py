import logging
import pinject

from save_message.config import load_config


logger = logging.getLogger(__name__)


class SaveMessageBindingSpec(pinject.BindingSpec):
    def __init__(self, args):
        self.config = load_config(args.cfg_file)
        self.args = args

    def configure(self, bind):
        bind("config", to_instance=self.config)
        bind("args", to_instance=self.args)
