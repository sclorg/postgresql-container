import shutil
import tempfile
import time
import pytest

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib, PodmanCLIWrapper
from container_ci_suite.utils import ContainerTestLibUtils

from conftest import (
    VARS,
    get_upgrade_path,
    get_image_id,
    create_and_wait_for_container,
    check_pagila_db,
    is_db_ready,
    check_table_output_in_db,
)


class TestPostgreSQLUpgrade:
    """
    Test PostgreSQL container Upgrade functionality.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)
        self.admin_password = "redhat"
        self.upgrade_volume_dir = tempfile.mkdtemp(prefix="/tmp/psql-upgrade")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:rwx {self.upgrade_volume_dir}",
            ]
        )

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()
        shutil.rmtree(self.upgrade_volume_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "upgrade_type, datadir",
        [
            ("hardlink", "empty"),
            ("copy", "empty"),
            ("hardlink", "pagila"),
            ("copy", "pagila"),
        ],
    )
    def test_upgrade_functionality(self, upgrade_type, datadir):
        """
        Test upgrade functionality of the PostgreSQL container.
        Steps are:
        1. Create a container with the previous version
        2. Create a container with the new version
        3. Test if the database connection works on upgraded database version
        """
        if VARS.OS == "fedora":
            pytest.skip(
                "Skip upgrade test on Fedora. Only CentOS Stream and RHELs are supported."
            )
        self.datadir = datadir
        prev_version = get_upgrade_path()
        if not prev_version:
            pytest.skip(
                f"Skipping for {VARS.OS} and version {VARS.VERSION}. No upgrade path found."
            )
        self.registry_image = get_image_id(version=prev_version)
        if not PodmanCLIWrapper.podman_pull_image(
            image_name=self.registry_image, loops=3
        ):
            pytest.skip(
                f"{self.registry_image} image not found in registry so skipping migration test.."
            )
        # Override the image name to previous version
        self.db.image_name = self.registry_image
        self.create_database_in_prev_version()
        self.upgrade_image(upgrade_type=upgrade_type)
        self.upgrade_image(upgrade_type=upgrade_type, bool_test_upgrade=False)

    def create_database_in_prev_version(self):
        """
        Create a database in the old version.
        Steps are:
        1. Create a container with the previous version and run pg_upgrade
        2. Test if the database connection works
        3. If datadir is empty, create a simple table and insert some data.
        If datadir is pagila, add the pagila example database
        """
        cid_file_name = "create-db-test"
        container_args = [
            f"-e POSTGRESQL_ADMIN_PASSWORD={self.admin_password}",
            f"-v {self.upgrade_volume_dir}:/var/lib/pgsql/data:Z",
        ]

        cid_create, cip_create = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        # Let's wait couple seconds
        time.sleep(5)
        assert is_db_ready(dw_api=self.db.db_lib, cid=cid_create)
        if self.datadir == "empty":
            check_table_output_in_db(cid=cid_create)
            PodmanCLIWrapper.call_podman_command(cmd=f"stop {cid_create}")
            PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid_create}")
        else:
            file_path = Path(f"{VARS.TEST_DIR}/pagila/postgresql-container-pagila.sql")
            assert file_path.exists()
            psql_cmd = f"PGPASSWORD={self.admin_password} psql -h {cip_create}"
            PodmanCLIWrapper.call_podman_command(
                cmd=f"run --rm -i {VARS.IMAGE_NAME} bash -c '{psql_cmd}' < {file_path}",
            )
            check_pagila_db(cid=cid_create)

    def upgrade_image(self, upgrade_type: str, bool_test_upgrade: bool = True):
        """
        Upgrade the image.
        Steps are:
        1. Create a container with the new version and run pg_upgrade
        2. Test if the database connection works
        3. If bool_test_upgrade is True, check the database output after upgrade.
           If False, just check the connection as the second upgrade
           can take more time and we have already tested the output after the first upgrade.
        4. If datadir is empty, create a simple table and insert some data.
           Done by calling check_table_output_in_db function.
           If datadir is pagila, add the pagila example database
           Done by calling check_pagila_db function.
        5. Stop and remove the container after the test.
        """
        self.db.image_name = VARS.IMAGE_NAME
        cid_file_name = f"upg-test-{upgrade_type}-{self.datadir}"
        container_args = [
            f"-e POSTGRESQL_ADMIN_PASSWORD={self.admin_password}",
            f"-v {self.upgrade_volume_dir}:/var/lib/pgsql/data:Z",
        ]
        if bool_test_upgrade:
            container_args.append(f"-e POSTGRESQL_UPGRADE={upgrade_type}")

        cid_upg, _ = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        time.sleep(5)
        assert is_db_ready(dw_api=self.db.db_lib, cid=cid_upg)
        if self.datadir == "empty":
            check_table_output_in_db(cid=cid_upg)
            PodmanCLIWrapper.call_podman_command(cmd=f"stop {cid_upg}")
            PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid_upg}")
        else:
            check_pagila_db(cid=cid_upg)
