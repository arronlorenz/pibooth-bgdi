# -*- coding: utf-8 -*-

"""Script to display the configuration of the printer.
"""

import sys
import json
import cups
from pibooth.utils import LOGGER, configure_logging
from pibooth.config import PiConfigParser
from pibooth.plugins import create_plugin_manager


def main():
    """Application entry point.
    """
    configure_logging()
    plugin_manager = create_plugin_manager()
    config = PiConfigParser("~/.config/pibooth/pibooth.cfg", plugin_manager)

    conn = cups.Connection()
    requested = config.get('PRINTER', 'printer_name')

    if not requested or requested.lower() == 'default':
        name = conn.getDefault()
        if not name and conn.getPrinters():
            name = next(iter(conn.getPrinters()))  # Take first one
    elif requested in conn.getPrinters():
        name = requested
    else:
        name = None

    if not name:
        # The error-path branch used to call name.lower() after name was
        # set to None, which crashed on a Pi with no CUPS printers.
        # Report against the user-requested string instead.
        if not requested or requested.lower() == 'default':
            LOGGER.warning("No printer configured in CUPS (see http://localhost:631)")
        else:
            LOGGER.warning("No printer named '%s' in CUPS (see http://localhost:631)", requested)
        return
    else:
        LOGGER.info("Connected to printer '%s'", name)

    f = conn.getPPD(name)
    ppd = cups.PPD(f)
    groups = ppd.optionGroups
    options = []
    for group in groups:
        group_name = "{} - {}".format(group.name, group.text)
        for opt in group.options:
            option = {'group': group_name}
            values = list(map(lambda x: x["choice"], opt.choices))
            texts = list(map(lambda x: x["text"], opt.choices))
            option['keyword'] = opt.keyword
            option['value'] = opt.defchoice
            option['description'] = opt.text
            if values != texts:
                option['choices'] = dict([(v, texts[values.index(v)]) for v in values])
            else:
                option['choices'] = values
            options.append(option)

    if '--json' in sys.argv:
        print(json.dumps(dict([(option['keyword'], option['value']) for option in options])))
    else:
        for option in options:
            print("{} = {}".format(option['keyword'], option['value']))
            print("     Description: {}".format(option['description']))
            if isinstance(option['choices'], dict):
                choices = ["{} = {}".format(value, descr) for value, descr in option['choices'].items()]
                print("     Choices:     {}".format(choices[0]))
                for choice in choices[1:]:
                    print("                  {}".format(choice))
            else:
                print("     Choices:     {}".format(", ".join(option['choices'])))

            print()


if __name__ == "__main__":
    main()
