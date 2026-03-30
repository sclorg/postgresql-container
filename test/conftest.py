import os
import re
import sys
import urllib3


from pathlib import Path
from collections import namedtuple

from container_ci_suite.utils import check_variables

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        "PREVIOUS_VERSION",
        "PAGILA",
        "MIGRATION_PATHS",
        "UPGRADE_PATH_DICT",
        "SQL_CMDS",
    ],
)
VERSION = os.getenv("VERSION")
OS = os.getenv("TARGET").lower()
TEST_APP = TEST_DIR / "test-app"
VERY_LONG_IDENTIFIER = "very_long_identifier_" + "x" * 40
MIGRATION_PATHS = ["12", "13", "15", "16", "18"]
PREVIOUS_VERSION_DICT = {
    "13": "12",
    "15": "13",
    "16": "15",
    "18": "16",
}
PAGILA = ["pagila-schema.sql", "pagila-data.sql", "pagila-insert-data.sql"]
SQL_CMDS = {
    "select count(*) from information_schema.triggers;": "16",
    "select count(*) from staff;": "2",
    "select * from information_schema.tables;": "28",
}
RHEL9 = "none 13 15 16 18 none"
RHEL10 = "none 16 18 none"
UPGRADE_PATH_DICT = {
    "rhel8": "none 12 13 15 16 18 none",
    "rhel9": RHEL9,
    "c9s": RHEL9,
    "rhel10": RHEL10,
    "c10s": RHEL10,
    "fedora": "none 15 16 18 none",
}
VARS = Vars(
    OS=OS,
    VERSION=VERSION,
    IMAGE_NAME=os.getenv("IMAGE_NAME"),
    TEST_DIR=TEST_DIR,
    TAG=OS.replace("rh", "-", 1),
    TEST_APP=TEST_APP,
    VERY_LONG_IDENTIFIER=VERY_LONG_IDENTIFIER,
    PREVIOUS_VERSION=PREVIOUS_VERSION_DICT.get(VERSION),
    PAGILA=PAGILA,
    MIGRATION_PATHS=MIGRATION_PATHS,
    UPGRADE_PATH_DICT=UPGRADE_PATH_DICT,
    SQL_CMDS=SQL_CMDS,
)


def get_upgrade_path():
    """
    Get the upgrade path of the PostgreSQL container.
    """
    for version in UPGRADE_PATH_DICT[VARS.OS].split():
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
    if VARS.OS in ["rhel8", "rhel9", "rhel10"]:
        return f"registry.redhat.io/{VARS.OS}/postgresql-{version}"
    return f"quay.io/sclorg/postgresql-{version}-{VARS.OS}"


def check_db_output(
    dw_api,
    cip,
    username,
    password,
    database,
):
    """
    Check the database output if the data is inserted correctly
    by running a SELECT statement.
    """
    output = dw_api.run_sql_command(
        container_ip=cip,
        username=username,
        password=password,
        container_id=VARS.IMAGE_NAME,
        database=database,
        sql_cmd='-At -c "SELECT * FROM tbl;"',
    )
    expected_db_output = [
        "1|2",
        "3|4",
        "5|6",
    ]
    for row in expected_db_output:
        assert re.search(row, output), f"Row {row} not found in {output}"
