import pytest

from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.database import DatabaseWrapper

from conftest import VARS, create_postgresql_volume_dir


class TestPostgreSQLConfigurationContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type="postgresql")
        self.db_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")
        self.volume_dir = create_postgresql_volume_dir()

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()

    def test_container_creation_fails(self):
        """
        Test container creation fails with no arguments.
        """
        cid_config_test = "container_creation_fails"
        assert self.db.assert_container_creation_fails(
            cid_file_name=cid_config_test, container_args=[], command=""
        )

    @pytest.mark.parametrize(
        "psql_user, psql_password, psql_database",
        [
            (
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=pass",
                "",
            ),
            (
                "-e POSTGRESQL_USER=user",
                "",
                "-e POSTGRESQL_DATABASE=db",
            ),
            (
                "",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=db",
            ),
        ],
    )
    def test_try_image_invalid_combinations(
        self, psql_user, psql_password, psql_database
    ):
        """
        Test container creation fails with invalid combinations of arguments.
        """
        assert self.db.assert_container_creation_fails(
            cid_file_name="try_image_invalid_combinations",
            container_args=[psql_user, psql_password, psql_database],
            command="",
        )
        assert self.db.assert_container_creation_fails(
            cid_file_name="try_image_invalid_combinations",
            container_args=[
                psql_user,
                psql_password,
                psql_database,
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
            command="",
        )

    @pytest.mark.parametrize(
        "psql_user, psql_password, psql_database, psql_admin_password",
        [
            [
                "-e POSTGRESQL_USER=",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=db",
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
            [
                f"-e POSTGRESQL_USER={VARS.VERY_LONG_IDENTIFIER}",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=db",
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
            [
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=pass",
                f"-e POSTGRESQL_DATABASE={VARS.VERY_LONG_IDENTIFIER}",
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
        ],
    )
    def test_invalid_configuration_tests(
        self,
        psql_user,
        psql_password,
        psql_database,
        psql_admin_password,
    ):
        """
        Test invalid configuration combinations for PostgreSQL container.
        """
        assert self.db.assert_container_creation_fails(
            cid_file_name="invalid_configuration_tests",
            container_args=[
                psql_user,
                psql_password,
                psql_database,
                psql_admin_password,
            ],
            command="",
        )

    @pytest.mark.parametrize(
        "psql_user, psql_password, psql_database, psql_admin_password",
        [
            [
                "user",
                "pass",
                "db",
                "admin_pass",
            ],
            [
                "user",
                "pass",
                "9invalid",
                "admin_pass",
            ],
            [
                "user",
                "pass",
                "db",
                "",
            ],
            [
                "",
                "",
                "",
                '"the @password"',
            ],
            [
                '"the user"',
                '"the pass"',
                '"the db"',
                "",
            ],
        ],
    )
    def test_correct_configuration_tests(
        self,
        psql_user,
        psql_password,
        psql_database,
        psql_admin_password,
    ):
        """
        Test correct configuration combinations for PostgreSQL container.
        """
        psql_admin_password_arg = ""
        psql_user_arg = ""
        psql_password_arg = ""
        psql_database_arg = ""
        if psql_user:
            psql_user_arg = f"-e POSTGRESQL_USER={psql_user}"
        if psql_password:
            psql_password_arg = f"-e POSTGRESQL_PASSWORD={psql_password}"
        if psql_database:
            psql_database_arg = f"-e POSTGRESQL_DATABASE={psql_database}"
        if psql_admin_password:
            psql_admin_password_arg = (
                f"-e POSTGRESQL_ADMIN_PASSWORD={psql_admin_password}"
            )
        container_args = [
            psql_user_arg,
            psql_password_arg,
            psql_database_arg,
            psql_admin_password_arg,
        ]
        assert self.db.assert_container_creation_succeeds(
            container_args=container_args,
            command="",
        )
        cid_file_name = "cid_success_test"
        assert self.db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip = self.db.get_cip(cid_file_name=cid_file_name)
        assert cip
        if psql_user and psql_password:
            assert self.db.test_db_connection(
                container_ip=cip,
                username=psql_user,
                password=psql_password,
                database=psql_database,
            )
        if psql_admin_password:
            assert self.db.test_db_connection(
                container_ip=cip,
                username="postgres",
                password=psql_admin_password,
                database=psql_database,
            )

    def test_configuration_hook(self):
        """
        Test container creation fails with no arguments.
        """
        self.shared_buffer_test("32MB")
        self.shared_buffer_test("113MB")
        self.shared_buffer_test("111MB")

    def shared_buffer_test(self, shared_buffer_value):
        """
        Test shared buffer configuration.
        """
        cid_file_name = f"test_pg_hook_{shared_buffer_value}"
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            f"-e POSTGRESQL_SHARED_BUFFERS={shared_buffer_value}",
            f"-v {self.volume_dir}:/opt/app-root/src:Z",
        ]

        assert self.db.create_container(
            cid_file_name=cid_file_name,
            docker_args=docker_args,
            command="",
        )
        cid = self.db.get_cid(cid_file_name=cid_file_name)
        assert cid
        cip = self.db.get_cip(cid_file_name=cid_file_name)
        assert cip
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd='psql -tA -c "SHOW shared_buffers;"',
        )
        assert shared_buffer_value in output, (
            f"Shared buffers should be {shared_buffer_value}, but is {output}"
        )
