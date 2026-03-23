import os
import sys

from pathlib import Path
from collections import namedtuple

from container_ci_suite.utils import check_variables

if not check_variables():
    sys.exit(1)

TEST_DIR = Path(__file__).parent.absolute()
Vars = namedtuple(
    "Vars",
    [
        "OS",
        "VERSION",
        "IMAGE_NAME",
        "TEST_DIR",
        "TAG",
        "TEST_APP",
        "VERY_LONG_IDENTIFIER",
    ],
)
VERSION = os.getenv("VERSION")
OS = os.getenv("TARGET").lower()
TEST_APP = TEST_DIR / "test-app"
VERY_LONG_IDENTIFIER = "very_long_identifier_" + "x" * 40
VARS = Vars(
    OS=OS,
    VERSION=VERSION,
    IMAGE_NAME=os.getenv("IMAGE_NAME"),
    TEST_DIR=TEST_DIR,
    TAG=OS.replace("rh", "-", 1),
    TEST_APP=TEST_APP,
    VERY_LONG_IDENTIFIER=VERY_LONG_IDENTIFIER,
)


def get_previous_major_version():
    """
    Get the previous major version of the PostgreSQL container.
    """
    version_dict = {
        "13": "12",
        "15": "13",
        "16": "15",
    }
    return version_dict.get(VARS.VERSION)


def get_upgrade_path():
    """
    Get the upgrade path of the PostgreSQL container.
    """
    upgrade_path = {
        "rhel8": "none 12 13 15 16 none",
        "rhel9": "none 13 15 16 18 none",
        "rhel10": "none 16 18 none",
        "fedora": "none 15 16 18 none",
    }
    for version in upgrade_path.keys():
        if version == VARS.VERSION:
            break
        prev = version
    if prev == "none":
        return None
    return prev


def get_image_id(version):
    """
    Get the image ID of the PostgreSQL container.
    """
    ns = {
        "rhel8": f"registry.redhat.io/rhel8/postgresql-{version}",
        "rhel9": f"registry.redhat.io/rhel9/postgresql-{version}",
        "rhel10": f"registry.redhat.io/rhel10/postgresql-{version}",
        "c9s": f"quay.io/sclorg/postgresql-{version}-c9s",
        "c10s": f"quay.io/sclorg/postgresql-{version}-c10s",
    }
    return ns[VARS.OS]
