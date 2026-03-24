import re
import tempfile
import time
import pytest

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib, PodmanCLIWrapper
from container_ci_suite.engines.database import DatabaseWrapper
from container_ci_suite.utils import ContainerTestLibUtils

from conftest import VARS, get_upgrade_path, get_image_id


class TestPostgreSQLUpgrade:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.upgrade_db = ContainerTestLib(
            image_name=VARS.IMAGE_NAME, db_type="postgresql"
        )
        self.db_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")
        self.admin_password = "redhat"

    @pytest.mark.parametrize(
        "upgrade_type, datadir",
        [
            ("hardlink", "empty"),
            ("copy", "empty"),
            ("hardlink", "pagila"),
            ("copy", "pagila"),
        ]
    )
    def test_upgrade_functionality(self, upgrade_type, datadir):
        """
        Test upgrade functionality of the PostgreSQL container.
        Steps are:
        1. Create a container with the previous version and run pg_upgrade
        2. Create a container with the new version and run pg_upgrade
        3. Test if the database connection works
        """
        self.datadir = datadir
        self.upgrade_volume_dir = tempfile.mkdtemp(prefix=f"/tmp/psql-upgrade-{upgrade_type}-{datadir}")
        prev_version = get_upgrade_path()
        assert prev_version, "Previous version not found"
        assert PodmanCLIWrapper.podman_pull_image(image_name=get_image_id(prev_version))
        # Override the image name to previous version
        self.upgrade_db.image_name = get_image_id(prev_version)
        self.create_database_in_prev_version()
        self.upgrade_image(upgrade_type=upgrade_type)
        self.upgrade_image(upgrade_type=upgrade_type, bool_test_upgrade=False)

    def create_database_in_prev_version(self):
        """
        Create a database in the old version.
        """
        cid_file_name = "create-db-test"
        assert ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:rwx {self.upgrade_volume_dir}",
            ]
        )
        container_args = [
            f"-e POSTGRESQL_ADMIN_PASSWORD={self.admin_password}",
            f"-v {self.upgrade_volume_dir}:/var/lib/pgsql/data:Z",
        ]

        assert self.upgrade_db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip_create, cid_create = self.upgrade_db.get_cip_cid(
            cid_file_name=cid_file_name
        )
        assert cid_create and cip_create
        assert self.db_api.wait_for_database(
            container_id=cid_create, command="/usr/libexec/check-container"
        )
        is_db_ready = False
        for _ in range(5):
            output = PodmanCLIWrapper.podman_logs(container_id=cid_create)
            print(output)
            if "accepting connections" in output:
                is_db_ready = True
                break
            time.sleep(5)
        assert is_db_ready, "Database is not ready after waiting for 25 seconds"
        if self.datadir == "empty":
            sql_cmd = "CREATE TABLE blah (id int);"
            output = PodmanCLIWrapper.podman_exec_shell_command(
                cid_file_name=cid_create,
                cmd=f"psql -tA -c \"{sql_cmd}\"",
            )
            assert "CREATE TABLE" in output
            sql_cmd = "INSERT INTO blah VALUES (1), (2), (3);"
            output = PodmanCLIWrapper.podman_exec_shell_command(
                cid_file_name=cid_create,
                cmd=f"psql -tA -c \"{sql_cmd}\"",
            )
            self.check_db_output(cid=cid_create)
        else:
            file_path = Path(f"{VARS.TEST_DIR}/pagila/postgresql-container-pagila.sql")
            assert file_path.exists()
            psql_cmd = f"PGPASSWORD={self.admin_password} psql -h {cip_create}"
            PodmanCLIWrapper.call_podman_command(
                cmd=f"run --rm -i {VARS.IMAGE_NAME} bash -c '{psql_cmd}' < {file_path}",
            )
            self.check_pagila_db(cid=cid_create)
        # PodmanCLIWrapper.call_podman_command(cmd=f"stop {cid_create}")
        # PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid_create}")

    def upgrade_image(self, upgrade_type: str, bool_test_upgrade: bool = True):
        """
        Upgrade the image.
        """
        self.upgrade_db.image_name = VARS.IMAGE_NAME
        cid_file_name = f"upg-test-{upgrade_type}-{self.datadir}"
        container_args = [
            f"-e POSTGRESQL_ADMIN_PASSWORD={self.admin_password}",
            f"-v {self.upgrade_volume_dir}:/var/lib/pgsql/data:Z",
        ]
        if bool_test_upgrade:
            container_args.append(f"-e POSTGRESQL_UPGRADE={upgrade_type}")
        assert self.upgrade_db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip_upg, cid_upg = self.upgrade_db.get_cip_cid(cid_file_name=cid_file_name)
        assert cip_upg and cid_upg
        assert self.db_api.wait_for_database(
            container_id=cid_upg, command="/usr/libexec/check-container"
        )
        # Let's wait couple seconds
        time.sleep(5)
        is_db_ready = False
        for _ in range(5):
            output = PodmanCLIWrapper.podman_logs(container_id=cid_upg)
            if "accepting connections" in output:
                is_db_ready = True
                break
            time.sleep(5)
        assert is_db_ready, "Database is not ready after waiting for 25 seconds"
        assert output
        if self.datadir == "empty":
            self.check_db_output(cid=cid_upg)
        else:
            self.check_pagila_db(cid=cid_upg)

    def check_db_output(self, cid):
        """
        Check the database output.
        """
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd="psql -h localhost -At -c \"SELECT * FROM blah ORDER BY id;\""
        )
        rows = [
            "1",
            "2",
            "3",
        ]
        for row in rows:
            assert re.search(row, output), f"Row {row} not found in {output}"
        PodmanCLIWrapper.call_podman_command(cmd=f"stop {cid}")
        PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid}")

    def check_pagila_db(self, cid):
        """
        Check the pagila database.
        """
        for sql, expected_count in VARS.SQL_CMDS.items():
            cmd = f"psql -tA -c \"{sql}\""
            output = PodmanCLIWrapper.podman_exec_shell_command(
                cid_file_name=cid,
                cmd=cmd,
            )
            if "information_schema.tables" in sql:
                # For tables we will check the count of tables in public schema as
                # there are some additional tables in information_schema after migration
                table_count = [x for x in output.split('\n') if "|public|" in x]
                assert len(table_count) == int(expected_count)
            else:
                assert re.search(expected_count, output)
        PodmanCLIWrapper.call_podman_command(cmd=f"stop {cid}")
        PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid}")
