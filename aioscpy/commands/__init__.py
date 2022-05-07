import os
import argparse
from typing import Any, Dict


from aioscpy.utils.common import arglist_to_dict
from aioscpy.exceptions import UsageError


class ASCommand:

    requires_project = False
    crawler_process = None
    requires_process = True

    # default settings to be used for this command instead of global defaults
    default_settings: Dict[str, Any] = {}

    exitcode = 0

    def __init__(self):
        self.settings = None  # set in aioscpy.cmdline

    def set_crawler(self, crawler):
        if hasattr(self, '_crawler'):
            raise RuntimeError("crawler already set")
        self._crawler = crawler

    def syntax(self):
        """
        Command syntax (preferably one-line). Do not include command name.
        """
        return ""

    def short_desc(self):
        """
        A short description of the command
        """
        return ""

    def long_desc(self):
        """A long description of the command. Return short description when not
        available. It cannot contain newlines since contents will be formatted
        by optparser which removes newlines and wraps text.
        """
        return self.short_desc()

    def help(self):
        """An extensive help for the command. It will be shown when using the
        "help" command. It can contain newlines since no post-formatting will
        be applied to its contents.
        """
        return self.long_desc()

    def add_options(self, parser):
        """
        Populate option parse with options available for this command
        """
        group = parser.add_argument_group(title='Global Options')
        group.add_argument("--logfile", metavar="FILE",
                           help="log file. if omitted stderr will be used")
        group.add_argument("-L", "--loglevel", metavar="LEVEL", default=None,
                           help=f"log level (default: {self.settings['LOG_LEVEL']})")
        group.add_argument("--nolog", action="store_true",
                           help="disable logging completely")
        group.add_argument("--profile", metavar="FILE", default=None,
                           help="write python cProfile stats to FILE")
        group.add_argument("--pidfile", metavar="FILE",
                           help="write process ID to FILE")
        group.add_argument("-s", "--set", action="append", default=[], metavar="NAME=VALUE",
                           help="set/override setting (may be repeated)")

    def process_options(self, args, opts):
        try:
            self.settings.setdict(arglist_to_dict(opts.set),
                                  priority='cmdline')
        except ValueError:
            raise UsageError("Invalid -s value, use -s NAME=VALUE", print_help=False)

        if opts.logfile:
            self.settings.set('LOG_ENABLED', True, priority='cmdline')
            self.settings.set('LOG_FILE', opts.logfile, priority='cmdline')

        if opts.loglevel:
            self.settings.set('LOG_ENABLED', True, priority='cmdline')
            self.settings.set('LOG_LEVEL', opts.loglevel, priority='cmdline')

        if opts.nolog:
            self.settings.set('LOG_ENABLED', False, priority='cmdline')

        if opts.pidfile:
            with open(opts.pidfile, "w") as f:
                f.write(str(os.getpid()) + os.linesep)

    def run(self, args, opts):
        """
        Entry point for running commands
        """
        raise NotImplementedError


class BaseRunSpiderCommand(ASCommand):
    """
    Common class used to share functionality between the crawl, parse and runspider commands
    """
    def add_options(self, parser):
        ASCommand.add_options(self, parser)
        parser.add_argument("-a", dest="spargs", action="append", default=[], metavar="NAME=VALUE",
                            help="set spider argument (may be repeated)")
        parser.add_argument("-o", "--output", metavar="FILE", action="append",
                            help="append scraped items to the end of FILE (use - for stdout)")
        parser.add_argument("-O", "--overwrite-output", metavar="FILE", action="append",
                            help="dump scraped items into FILE, overwriting any existing file")
        parser.add_argument("-t", "--output-format", metavar="FORMAT",
                            help="format to use for dumping items")

    def process_options(self, args, opts):
        ASCommand.process_options(self, args, opts)
        try:
            opts.spargs = arglist_to_dict(opts.spargs)
        except ValueError:
            raise UsageError("Invalid -a value, use -a NAME=VALUE", print_help=False)


class ASHelpFormatter(argparse.HelpFormatter):
    """
    Help Formatter for scrapy command line help messages.
    """
    def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
        super().__init__(prog, indent_increment=indent_increment,
                         max_help_position=max_help_position, width=width)

    def _join_parts(self, part_strings):
        parts = self.format_part_strings(part_strings)
        return super()._join_parts(parts)

    def format_part_strings(self, part_strings):
        """
        Underline and title case command line help message headers.
        """
        if part_strings and part_strings[0].startswith("usage: "):
            part_strings[0] = "Usage\n=====\n  " + part_strings[0][len('usage: '):]
        headings = [i for i in range(len(part_strings)) if part_strings[i].endswith(':\n')]
        for index in headings[::-1]:
            char = '-' if "Global Options" in part_strings[index] else '='
            part_strings[index] = part_strings[index][:-2].title()
            underline = ''.join(["\n", (char * len(part_strings[index])), "\n"])
            part_strings.insert(index + 1, underline)
        return part_strings
