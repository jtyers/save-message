import logging
import pinject

from save_message.config import load_config
from save_message.config import CONFIG_FILE


logger = logging.getLogger(__name__)


class SaveMessageBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        bind(
            "config",
            to_instance=load_config(CONFIG_FILE),
        )

        # bind("task_service", to_class=TaskServiceClient)
