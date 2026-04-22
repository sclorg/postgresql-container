import shutil
import tempfile

import pytest

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib, PodmanCLIWrapper
from container_ci_suite.utils import ContainerTestLibUtils

from conftest import VARS, get_image_id, create_and_wait_for_container, check_pagila_db


class TestPostgreSQLMigration:
    """
    Test PostgreSQL container data migration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)
        self.registry_image = get_image_id(version=VARS.VERSION)
        self.migrate_volume_dir = tempfile.mkdtemp(prefix="/tmp/psql-migrate-volume")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {self.migrate_volume_dir}",
            ]
        )

        self.admin_password = "redhat"

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()
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
        if int(version_to_migrate) >= int(VARS.VERSION):
            pytest.skip(
                f"Migration path from {version_to_migrate} -> {VARS.VERSION} is not valid so skipping."
            )

        self.registry_image = get_image_id(version=version_to_migrate)
        if not PodmanCLIWrapper.podman_pull_image(
            image_name=self.registry_image, loops=3
        ):
            pytest.skip(
                f"{self.registry_image} image not found in registry so skipping migration test.."
            )
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
        self.db.image_name = get_image_id(version=version)
        cid_create, cip_create = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        file_path = Path(f"{VARS.TEST_DIR}/pagila/postgresql-container-pagila.sql")
        assert file_path.exists()
        psql_cmd = f"PGPASSWORD={self.admin_password} psql -h {cip_create}"
        PodmanCLIWrapper.call_podman_command(
            cmd=f"run --rm -i {VARS.IMAGE_NAME} bash -c '{psql_cmd}' < {file_path}",
        )
        check_pagila_db(cid=cid_create)
        return cip_create

    def migrate_image(self, cip: str):
        """
        Migrate the image.
        """
        self.db.image_name = VARS.IMAGE_NAME
        cid_file_name = "migrate-test"
        container_args = [
            f"-e POSTGRESQL_MIGRATION_REMOTE_HOST={cip}",
            f"-e POSTGRESQL_MIGRATION_ADMIN_PASSWORD={self.admin_password}",
        ]
        cid_migrate, _ = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        check_pagila_db(cid=cid_migrate)
