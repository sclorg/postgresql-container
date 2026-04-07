import re
import shutil
import tempfile

import pytest

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib, PodmanCLIWrapper
from container_ci_suite.engines.database import DatabaseWrapper
from container_ci_suite.utils import ContainerTestLibUtils

from conftest import VARS, get_image_id


class TestPostgreSQLMigration:
    """
    Test PostgreSQL container data migration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.migrate_db = ContainerTestLib(
            image_name=VARS.IMAGE_NAME, db_type="postgresql"
        )
        self.db_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")
        self.registry_image = get_image_id(version=VARS.VERSION)
        self.migrate_volume_dir = tempfile.mkdtemp(prefix="/tmp/psql-migrate-volume")
        self.admin_password = "redhat"

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.migrate_db.cleanup()
        shutil.rmtree(self.migrate_volume_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "version_to_migrate",
        VARS.MIGRATION_PATHS,
    )
    def test_migration_functionality(self, version_to_migrate):
        """
        Test migration functionality of the PostgreSQL container.
        Steps are:
        1. Create a container with the previous version and run pg_upgrade
        2. Create a container with the new version and run pg_upgrade with migration options
        3. Test if the database connection works
        """
        if VARS.OS == "fedora":
            pytest.skip("Skip migration test on fedora")
        assert ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {self.migrate_volume_dir}",
            ]
        )
        if int(version_to_migrate) >= int(VARS.VERSION):
            pytest.skip(f"Migration path from {version_to_migrate} -> {VARS.VERSION} is not valid so skipping.")

        self.registry_image = get_image_id(version=version_to_migrate)
        if not PodmanCLIWrapper.podman_pull_image(image_name=self.registry_image, loops=3):
            pytest.skip(f"{self.registry_image} image not found in registry so skipping migration test..")
        cip = self.start_database(version=version_to_migrate)
        self.migrate_image(cip=cip)

    def start_database(self, version) -> str:
        """
        Start the database container with the given version and create a table.
        """
        cid_file_name = f"start-db-{version}"

        container_args = [
            f"-e POSTGRESQL_ADMIN_PASSWORD={self.admin_password}",
            f"-v {self.migrate_volume_dir}:/var/lib/pgsql/data:Z",
        ]
        self.migrate_db.image_name = get_image_id(version=version)
        assert self.migrate_db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip_create, cid_create = self.migrate_db.get_cip_cid(cid_file_name=cid_file_name)
        assert cid_create and cip_create
        assert self.db_api.wait_for_database(
            container_id=cid_create, command="/usr/libexec/check-container"
        )
        file_path = Path(f"{VARS.TEST_DIR}/pagila/postgresql-container-pagila.sql")
        assert file_path.exists()
        psql_cmd = f"PGPASSWORD={self.admin_password} psql -h {cip_create}"
        PodmanCLIWrapper.call_podman_command(
            cmd=f"run --rm -i {VARS.IMAGE_NAME} bash -c '{psql_cmd}' < {file_path}",
        )
        self.check_pagila_db(cid=cid_create)
        return cip_create

    def migrate_image(self, cip: str):
        """
        Migrate the image.
        """
        self.migrate_db.image_name = VARS.IMAGE_NAME
        cid_file_name = "migrate-test"
        container_args = [
            f"-e POSTGRESQL_MIGRATION_REMOTE_HOST={cip}",
            f"-e POSTGRESQL_MIGRATION_ADMIN_PASSWORD={self.admin_password}",
        ]
        assert self.migrate_db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip_migrate, cid_migrate = self.migrate_db.get_cip_cid(cid_file_name=cid_file_name)
        assert cid_migrate and cip_migrate
        assert self.db_api.wait_for_database(
            container_id=cid_migrate, command="/usr/libexec/check-container"
        )
        self.check_pagila_db(cid=cid_migrate)

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
