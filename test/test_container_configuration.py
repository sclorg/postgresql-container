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
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=",
                "-e POSTGRESQL_DATABASE=db",
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
            [
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=9invalid",
                "-e POSTGRESQL_ADMIN_PASSWORD=admin_pass",
            ],
            [
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=db",
                "-e POSTGRESQL_ADMIN_PASSWORD=",
            ],
            [
                "-e POSTGRESQL_USER=user",
                "-e POSTGRESQL_PASSWORD=pass",
                "-e POSTGRESQL_DATABASE=db",
                "-e POSTGRESQL_ADMIN_PASSWORD=",
            ],
            [
                "-e POSTGRESQL_USER=",
                "-e POSTGRESQL_PASSWORD=",
                "-e POSTGRESQL_DATABASE=",
                '-e POSTGRESQL_ADMIN_PASSWORD="The @password"',
            ],
            [
                '-e POSTGRESQL_USER="the user"',
                '-e POSTGRESQL_PASSWORD="the pass"',
                '-e POSTGRESQL_DATABASE="the db"',
                "-e POSTGRESQL_ADMIN_PASSWORD=",
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
        assert self.db.assert_container_creation_succeeds(
            container_args=[
                psql_user,
                psql_password,
                psql_database,
                psql_admin_password,
            ],
            command="",
        )

    def test_configuration_hook(self):
        """
        Test container creation fails with no arguments.
        """
        cid_file_name = "test_pg_hook"
        volume_dir = create_postgresql_volume_dir()
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            "-e POSTGRESQL_SHARED_BUFFERS=32MB",
            f"-v {volume_dir}:/opt/app-root/src:Z",
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
        assert "32MB" in output, f"Shared buffers should be 32MB, but is {output}"
        # Check that POSTGRESQL_SHARED_BUFFERS has effect.
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            "-e POSTGRESQL_SHARED_BUFFERS=113MB",
        ]
        cid_file_name2 = "test_pg_hook_2"
        assert self.db.create_container(
            cid_file_name=cid_file_name2,
            docker_args=docker_args,
            command="",
        )
        cid = self.db.get_cid(cid_file_name=cid_file_name2)
        assert cid
        cip = self.db.get_cip(cid_file_name=cid_file_name2)
        assert cip
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd='psql -tA -c "SHOW shared_buffers;"',
        )
        assert "113MB" in output, f"Shared buffers should be 113MB, but is {output}"
        # Check that volume has priority over POSTGRESQL_SHARED_BUFFERS.
        cid_file_name3 = "test_pg_hook_3"
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            "-e POSTGRESQL_SHARED_BUFFERS=113MB",
            f"-v {volume_dir}:/opt/app-root/src:Z",
        ]
        assert self.db.create_container(
            cid_file_name=cid_file_name3,
            docker_args=docker_args,
            command="",
        )
        cid = self.db.get_cid(cid_file_name=cid_file_name3)
        assert cid
        cip = self.db.get_cip(cid_file_name=cid_file_name3)
        assert cip
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd='psql -tA -c "SHOW shared_buffers;"',
        )

        assert "113MB" in output, f"Shared buffers should be 113MB, but is {output}"
