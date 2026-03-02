import shutil

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.utils import ContainerTestLibUtils

from conftest import VARS, create_postgresql_temp_file


def build_s2i_app(app_path: Path) -> ContainerTestLib:
    container_lib = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type="postgresql")
    app_name = app_path.name
    s2i_app = container_lib.build_as_df(
        app_path=app_path,
        s2i_args="--pull-policy=never",
        src_image=VARS.IMAGE_NAME,
        dst_image=f"{VARS.IMAGE_NAME}-{app_name}",
    )
    return s2i_app


class TestPostgreSQLBasicsContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.app_image = build_s2i_app(app_path=VARS.TEST_DIR / "test-app")
        self.app_image.db_lib.db_type = "postgresql"

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.app_image.cleanup()

    def test_s2i_usage(self):
        """
        Test container creation based on s2i technology.
        """
        cid_config_build = "s2i_config_build"
        psql_password = "password"
        psql_database = "db"
        psql_user = "user"
        psql_admin_password = psql_password
        psql_backup_user = "backuser"
        psql_backup_password = "pass"
        self.app_image.assert_container_creation_fails(
            cid_file_name=cid_config_build,
            command="",
            container_args=[
                "-e POSTGRESQL_PASSWORD=pass",
                f"-e POSTGRESQL_DATABASE={psql_database}",
            ],
        )
        assert self.app_image.create_container(
            cid_file_name=cid_config_build,
            docker_args=[
                f"-e POSTGRESQL_USER={psql_user}",
                f"-e POSTGRESQL_PASSWORD={psql_password}",
                f"-e POSTGRESQL_DATABASE={psql_database}",
                f"-e POSTGRESQL_BACKUP_USER={psql_backup_user}",
                f"-e POSTGRESQL_BACKUP_PASSWORD={psql_backup_password}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={psql_admin_password}",
            ],
        )
        cip = self.app_image.get_cip(cid_file_name=cid_config_build)
        assert cip
        assert self.app_image.test_db_connection(
            container_ip=cip, username=psql_user, password=psql_password
        )
        assert self.app_image.test_db_connection(
            container_ip=cip,
            username=psql_backup_user,
            password=psql_backup_password,
            database="backup",
        )
        backup_user_script = (
            VARS.TEST_DIR / "test-app" / "postgresql-init" / "backup_user.sh"
        )
        tmp_file = create_postgresql_temp_file()
        shutil.copy(backup_user_script, tmp_file)
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:rw- {tmp_file}",
            ]
        )
        cid_s2i_test_mount = "s2i_test_mount"
        mount_point = "/opt/app-root/src/postgresql-init/add_backup_user.sh"
        assert self.app_image.create_container(
            cid_file_name=cid_s2i_test_mount,
            docker_args=[
                f"-e POSTGRESQL_USER={psql_user}",
                f"-e POSTGRESQL_PASSWORD={psql_password}",
                f"-e POSTGRESQL_DATABASE={psql_database}",
                f"-e POSTGRESQL_BACKUP_USER={psql_backup_user}",
                f"-e POSTGRESQL_BACKUP_PASSWORD={psql_backup_password}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={psql_admin_password}",
                f"-v {tmp_file}:{mount_point}:z,ro",
            ],
        )
        cip = self.app_image.get_cip(cid_file_name=cid_s2i_test_mount)
        assert cip
        assert self.app_image.test_db_connection(
            container_ip=cip, username=psql_user, password=psql_password
        )
        assert self.app_image.test_db_connection(
            container_ip=cip,
            username=psql_backup_user,
            password=psql_backup_password,
            database="backup",
        )
