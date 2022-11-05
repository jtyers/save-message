#!/usr/bin/python3

import colorama
import logging
import sys

from pinject import new_object_graph

from save_message.injector import SaveMessageBindingSpec
from save_message._internal.argparse import create_parser

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

logger = logging.getLogger("save_message")


if __name__ == "__main__":
    colorama.init()  # TODO possibly remove this lib

    parser = create_parser()
    args = parser.parse_args()

    # set og on args so the 'do' functions can access it easily
    args.og = new_object_graph(binding_specs=[SaveMessageBindingSpec(args)])

    if args.verbose == 0:
        level = logging.INFO
        global_level = logging.INFO
    if args.verbose == 1:
        level = logging.DEBUG
        global_level = logging.INFO
    if args.verbose >= 2:
        level = logging.DEBUG
        global_level = logging.INFO

    logger.setLevel(level)
    logging.basicConfig(
        stream=sys.stderr, format=LOG_FORMAT, level=global_level, force=True
    )

    args.func(args)
