import logging
import pinject

logger = logging.getLogger(__name__)


class SaveMessageBindingSpec(pinject.BindingSpec):
    def configure(self, bind):
        pass
        # bind(
        #    "endpoint",
        #    to_instance=get_aaas_api_endpoint(),
        # )
        # bind("task_service", to_class=TaskServiceClient)
