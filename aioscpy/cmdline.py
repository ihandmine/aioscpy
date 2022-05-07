import sys
import os
import argparse
import cProfile
import inspect
import pkg_resources

import aioscpy
from aioscpy.inject import walk_modules
from aioscpy.commands import ASCommand, ASHelpFormatter
from aioscpy.exceptions import UsageError
from aioscpy.utils.tools import get_project_settings
from aioscpy.utils.common import inside_project
from aioscpy import call_grace_instance


def _iter_command_classes(module_name):
    # TODO: add `name` attribute to commands and and merge this function with
    for module in walk_modules(module_name):
        for obj in vars(module).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, ASCommand)
                and obj.__module__ == module.__name__
                and not obj == ASCommand
            ):
                yield obj


def _get_commands_from_module(module, inproject):
    d = {}
    for cmd in _iter_command_classes(module):
        if inproject or not cmd.requires_project:
            cmdname = cmd.__module__.split('.')[-1]
            d[cmdname] = cmd()
    return d


def _get_commands_from_entry_points(inproject, group='aioscpy.commands'):
    cmds = {}
    for entry_point in pkg_resources.iter_entry_points(group):
        obj = entry_point.load()
        if inspect.isclass(obj):
            cmds[entry_point.name] = obj()
        else:
            raise Exception(f"Invalid entry point {entry_point.name}")
    return cmds


def _get_commands_dict(settings, inproject):
    cmds = _get_commands_from_module('aioscpy.commands', inproject)
    cmds.update(_get_commands_from_entry_points(inproject))
    cmds_module = settings['COMMANDS_MODULE']
    if cmds_module:
        cmds.update(_get_commands_from_module(cmds_module, inproject))
    return cmds


def _pop_command_name(argv):
    i = 0
    for arg in argv[1:]:
        if not arg.startswith('-'):
            del argv[i]
            return arg
        i += 1


def _print_header(settings, inproject):
    version = aioscpy.__version__
    if inproject:
        print(f"aioscpy {version} - project: {settings['BOT_NAME']}\n")
    else:
        print(f"aioscpy {version} - no active project\n")


def _print_commands(settings, inproject):
    _print_header(settings, inproject)
    print("Usage:")
    print("  aioscpy <command> [options] [args]\n")
    print("Available commands:")
    cmds = _get_commands_dict(settings, inproject)
    for cmdname, cmdclass in sorted(cmds.items()):
        print(f"  {cmdname:<13} {cmdclass.short_desc()}")
    if not inproject:
        print()
        print("  [ more ]      More commands available when run from project directory")
    print()
    print('Use "aioscpy <command> -h" to see more info about a command')


def _print_unknown_command(settings, cmdname, inproject):
    _print_header(settings, inproject)
    print(f"Unknown command: {cmdname}\n")
    print('Use "aioscpy" to see available commands')


def _run_print_help(parser, func, *a, **kw):
    try:
        func(*a, **kw)
    except UsageError as e:
        if str(e):
            parser.error(str(e))
        if e.print_help:
            parser.print_help()
        sys.exit(2)


def execute(argv=None, settings=None):
    if argv is None:
        argv = sys.argv

    if settings is None:
        settings = get_project_settings()
        # set EDITOR from environment if available
        try:
            editor = os.environ['EDITOR']
        except KeyError:
            pass
        else:
            settings['EDITOR'] = editor

    inproject = inside_project()
    cmds = _get_commands_dict(settings, inproject)
    cmdname = _pop_command_name(argv)
    if not cmdname:
        _print_commands(settings, inproject)
        sys.exit(0)
    elif cmdname not in cmds:
        _print_unknown_command(settings, cmdname, inproject)
        sys.exit(2)

    cmd = cmds[cmdname]
    parser = argparse.ArgumentParser(formatter_class=ASHelpFormatter,
                                     usage=f"aioscpy {cmdname} {cmd.syntax()}",
                                     conflict_handler='resolve',
                                     description=cmd.long_desc())
    settings.setdict(cmd.default_settings, priority='command')
    cmd.settings = settings
    cmd.add_options(parser)
    opts, args = parser.parse_known_args(args=argv[1:])
    _run_print_help(parser, cmd.process_options, args, opts)

    if getattr(cmd, "requires_process"):
        # cmd.crawler_process = CrawlerProcess(settings)
        cmd.crawler_process = call_grace_instance("crawler_process", settings)
    _run_print_help(parser, _run_command, cmd, args, opts)
    sys.exit(cmd.exitcode)


def _run_command(cmd, args, opts):
    if opts.profile:
        _run_command_profiled(cmd, args, opts)
    else:
        cmd.run(args, opts)


def _run_command_profiled(cmd, args, opts):
    if opts.profile:
        sys.stderr.write(f"aioscpy: writing cProfile stats to {opts.profile!r}\n")
    loc = locals()
    p = cProfile.Profile()
    p.runctx('cmd.run(args, opts)', globals(), loc)
    if opts.profile:
        p.dump_stats(opts.profile)


if __name__ == '__main__':
    execute()

