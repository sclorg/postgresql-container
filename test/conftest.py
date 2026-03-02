import os
import sys
import tempfile

from pathlib import Path
from collections import namedtuple

from container_ci_suite.utils import check_variables
from container_ci_suite.utils import ContainerTestLibUtils

if not check_variables():
    sys.exit(1)

TAGS = {
    "rhel8": "-el8",
    "rhel9": "-el9",
    "rhel10": "-el10",
}
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
VERY_LONG_IDENTIFIER = (
    "very_long_identifier_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)
VARS = Vars(
    OS=OS,
    VERSION=VERSION,
    IMAGE_NAME=os.getenv("IMAGE_NAME"),
    TEST_DIR=Path(__file__).parent.absolute(),
    TAG=TAGS.get(OS),
    TEST_APP=TEST_APP,
    VERY_LONG_IDENTIFIER=VERY_LONG_IDENTIFIER,
)


def get_previous_major_version():
    version_dict = {
        "13": "12",
        "15": "13",
        "16": "15",
    }
    return version_dict.get(VARS.VERSION)


def get_upgrade_path():
    upgrade_path = {
        "rhel8": "none 12 13 15 16 none",
        "rhel9": "none 13 15 16 none",
        "rhel10": "none 13 15 16 none",
        "fedora": "none 12 13 14 15 16 none",
    }
    for version in upgrade_path.keys():
        if version == VARS.VERSION:
            break
        prev = version
    if prev == "none":
        return None
    return prev


def get_image_id(version):
    ns = {
        "rhel8": f"registry.redhat.io/rhel8/postgresql-{version}",
        "rhel9": f"registry.redhat.io/rhel9/postgresql-{version}",
        "rhel10": f"registry.redhat.io/rhel10/postgresql-{version}",
        "c9s": f"quay.io/sclorg/postgresql-{version}-c9s",
        "c10s": f"quay.io/sclorg/postgresql-{version}-c10s",
    }
    return ns[VARS.OS]


def create_postgresql_volume_dir():
    """
    Create a PostgreSQL volume directory and set the permissions to 26:-wx.
    """
    volume_dir = tempfile.mkdtemp(prefix="/tmp/psql-volume-dir")
    ContainerTestLibUtils.commands_to_run(
        commands_to_run=[
            f"setfacl -m u:26:-wx {volume_dir}",
        ]
    )
    return volume_dir


def create_postgresql_temp_file():
    """
    Create a PostgreSQL temporary file and set the permissions to 26:rw-.
    """
    temp_file = tempfile.mktemp(prefix="/tmp/psql-temp-file")
    ContainerTestLibUtils.commands_to_run(
        commands_to_run=[
            f"setfacl -m u:26:rw- {temp_file}",
        ]
    )
    return temp_file
