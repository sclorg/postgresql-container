import os
import re
import sys
import time

from pathlib import Path
from collections import namedtuple

from container_ci_suite.utils import check_variables
from container_ci_suite.container_lib import ContainerTestLib, DatabaseWrapper
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper


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
        "MIGRATION_PATHS",
        "UPGRADE_PATH_DICT",
        "SQL_CMDS",
        "DB_TYPE",
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
SQL_CMDS = {
    "select count(*) from information_schema.triggers;": "16",
    "select count(*) from staff;": "2",
    "select * from information_schema.tables;": "28",
}
RHEL9 = ["13", "15", "16", "18"]
RHEL10 = ["16", "18"]
UPGRADE_PATH_DICT = {
    "rhel8": ["12", "13", "15", "16"],
    "rhel9": RHEL9,
    "c9s": RHEL9,
    "rhel10": RHEL10,
    "c10s": RHEL10,
    "fedora": ["15", "16", "18"],
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
    MIGRATION_PATHS=MIGRATION_PATHS,
    UPGRADE_PATH_DICT=UPGRADE_PATH_DICT,
    SQL_CMDS=SQL_CMDS,
    DB_TYPE="postgresql",
)


def get_upgrade_path():
    """
    Get the upgrade path of the PostgreSQL container.
    """
    upgrade_path = UPGRADE_PATH_DICT[VARS.OS]
    if VARS.VERSION not in upgrade_path:
        return None
    current_index = upgrade_path.index(VARS.VERSION)
    if current_index == 0:
        return None
    return upgrade_path[current_index - 1]


def get_image_id(version):
    """
    Get the image ID of the PostgreSQL container.
    """
    if VARS.OS.startswith("rhel"):
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
    Check the database out+put if the data is inserted correctly
    by running a SELECT statement.
    """
    dw_api.run_sql_command(
        container_ip=cip,
        username=username,
        password=password,
        container_id=VARS.IMAGE_NAME,
        database=database,
        sql_cmd='-At -c "CREATE TABLE tbl (a integer, b integer);"',
    )

    dw_api.run_sql_command(
        container_ip=cip,
        username=username,
        password=password,
        container_id=VARS.IMAGE_NAME,
        database=database,
        sql_cmd=[
            '-At -c "INSERT INTO tbl VALUES (1, 2);"',
            '-At -c "INSERT INTO tbl VALUES (3, 4);"',
            '-At -c "INSERT INTO tbl VALUES (5, 6);"',
        ],
    )
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
    for expected_row in expected_db_output:
        assert re.search(expected_row, output), (
            f"Row {expected_row} not found in {output}"
        )


def create_and_wait_for_container(
    db: ContainerTestLib,
    cid_file_name: str,
    container_args: list[str],
    command: str,
) -> tuple[str, str]:
    """
    Create a container and wait for it to be ready.
    Args:
        db: ContainerTestLib instance
        cid_file_name: Name of the container ID file
        container_args: List of container arguments
        command: Command to run in the container
    Steps:
    1. Create the container
    2. Get the container ID and IP
    3. Wait for the database to be ready if required by wait_for_database flag
    4. Return the container ID and IP
    """
    assert db.create_container(
        cid_file_name=cid_file_name,
        container_args=container_args,
        command=command,
    )
    cip, cid = db.get_cip_cid(cid_file_name=cid_file_name)
    assert cid and cip
    dw_api = db.db_lib
    assert dw_api is not None
    dw_api.db_type = VARS.DB_TYPE
    assert dw_api.wait_for_database(
        container_id=cid, command="/usr/libexec/check-container"
    )
    return cid, cip


def build_s2i_app(app_path: Path) -> ContainerTestLib:
    """
    Build a S2I app.
    Args:
        app_path: Path to the app
    Returns:
        ContainerTestLib instance
    """
    container_lib = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)
    app_name = app_path.name
    container_test_lib_app = container_lib.build_as_df(
        app_path=app_path,
        s2i_args="--pull-policy=never",
        src_image=VARS.IMAGE_NAME,
        dst_image=f"{VARS.IMAGE_NAME}-{app_name}",
    )
    return container_test_lib_app


def check_pagila_db(cid):
    """
    Check the pagila database.
    """
    for sql, expected_count in VARS.SQL_CMDS.items():
        cmd = f'psql -tA -c "{sql}"'
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd=cmd,
        )
        if "information_schema.tables" in sql:
            table_count = [x for x in output.split("\n") if "|public|" in x]
            assert len(table_count) == int(expected_count)
        else:
            assert re.search(expected_count, output)


def is_db_ready(dw_api: DatabaseWrapper, cid: str) -> bool:
    """
    Check if the database is ready.
    """
    is_ready: bool = False
    for _ in range(5):
        # Let's check if the database is ready by running a simple query.
        # Sometimes check-container can return before the database is fully ready to accept connections.
        if not dw_api.wait_for_database(
            container_id=cid,
            command='psql -h localhost -tA -c "select 1;"',
        ):
            time.sleep(5)
            continue
        is_ready = True
        break
    return is_ready


def check_table_output_in_db(cid: str):
    """
    Check the database output.
    """
    output = PodmanCLIWrapper.podman_exec_shell_command(
        cid_file_name=cid, cmd='psql -tA -c "CREATE TABLE blah (id int);"'
    )
    output = PodmanCLIWrapper.podman_exec_shell_command(
        cid_file_name=cid,
        cmd='psql -tA -c "INSERT INTO blah VALUES (100), (200), (300);"',
    )
    output = PodmanCLIWrapper.podman_exec_shell_command(
        cid_file_name=cid,
        cmd='psql -h localhost -At -c "SELECT * FROM blah ORDER BY id;"',
    )
    expected_rows = [
        "100",
        "200",
        "300",
    ]
    for expected_row in expected_rows:
        assert re.search(expected_row, output), (
            f"Row {expected_row} not found in {output}"
        )
