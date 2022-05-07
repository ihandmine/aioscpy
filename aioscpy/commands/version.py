import aioscpy
from aioscpy.commands import ASCommand


class Command(ASCommand):

    default_settings = {'LOG_ENABLED': False,
                        'SPIDER_LOADER_WARN_ONLY': True}
    requires_process = False

    def syntax(self):
        return "[-v]"

    def short_desc(self):
        return "Print aioscpy version"

    def add_options(self, parser):
        ASCommand.add_options(self, parser)
        parser.add_argument("--verbose", "-v", dest="verbose", action="store_true",
                            help="also display twisted/python/platform info (useful for bug reports)")

    def run(self, args, opts):
        # if opts.verbose:
        #     versions = scrapy_components_versions()
        #     width = max(len(n) for (n, _) in versions)
        #     for name, version in versions:
        #         print(f"{name:<{width}} : {version}")
        # else:
        print(f"AIOSPCY {aioscpy.__version__}")
