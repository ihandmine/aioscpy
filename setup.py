import os
import sys
from shutil import rmtree

from setuptools import setup, Command

# Package meta-data.
NAME = "aioscpy"
DESCRIPTION = "An asyncio + aiolibs crawler imitate scrapy framework"
URL = "https://github.com/ihandmine/aioscpy"
EMAIL = "handmine@outlook.com"
AUTHOR = "handmine"
REQUIRES_PYTHON = ">=3.7.0"
VERSION = "0.0.1"

here = os.path.abspath(os.path.dirname(__file__))
with open(f"{here}/README.md") as f:
    long_description = f.read()


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds...")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel distribution...")
        os.system("{0} setup.py sdist bdist_wheel".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine...")
        os.system("twine upload dist/*")

        sys.exit()


setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    packages=[NAME],
    install_requires=[
        "aiohttp",
        "anti-header"
    ],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_dir={NAME: NAME},
    include_package_data=True,
    url=URL,
    author_email=EMAIL,
    license="MIT",
    keywords="""
                crawler
                scrapy
                asyncio
                aiohttp
                anti-header
                anti-useragent
                python3
               """,
    python_requires=REQUIRES_PYTHON,
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Operating System :: Unix",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
    ],
    # Build and upload package: python3 setup.py upload
    cmdclass={"upload": UploadCommand},
)
