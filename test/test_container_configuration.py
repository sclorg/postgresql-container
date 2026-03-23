import tempfile
import pytest

from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.utils import ContainerTestLibUtils
from container_ci_suite.engines.database import DatabaseWrapper

from conftest import VARS

volume_dir = tempfile.mkdtemp(prefix="/tmp/psql-volume-dir")
ContainerTestLibUtils.commands_to_run(
    commands_to_run=[
        f"setfacl -m u:26:-wx {volume_dir}",
    ]
)


class TestPostgreSQLInvalidConfigurations:
    """
    Test PostgreSQL container invalid configurations tests.
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
        assert self.db.assert_container_creation_fails(
            cid_file_name="creation_fails", container_args=[], command=""
        )

    @pytest.mark.parametrize(
        "psql_user, psql_password, psql_database, psql_admin_password",
        [
            (
                "user",
                "pass",
                "",
                "",
            ),
            (
                "user",
                "pass",
                "",
                "admin_pass",
            ),
            (
                "user",
                "",
                "db",
                "",
            ),
            (
                "user",
                "",
                "db",
                "admin_pass",
            ),
            (
                "",
                "pass",
                "db",
                "",
            ),
            (
                "",
                "pass",
                "db",
                "admin_pass",
            ),
            (VARS.VERY_LONG_IDENTIFIER, "pass", "db", ""),
            (VARS.VERY_LONG_IDENTIFIER, "pass", "db", "admin_pass"),
            (
                "user",
                "pass",
                VARS.VERY_LONG_IDENTIFIER,
                "",
            ),
            (
                "user",
                "pass",
                VARS.VERY_LONG_IDENTIFIER,
                "admin_pass",
            ),
        ],
    )
    def test_try_image_invalid_combinations(
        self, psql_user, psql_password, psql_database, psql_admin_password
    ):
        """
        Test container creation fails with invalid combinations of arguments.
        """
        cid_file_name = "try_image_invalid_combinations"
        psql_user_arg = f"-e POSTGRESQL_USER={psql_user}" if psql_user else ""
        psql_password_arg = (
            f"-e POSTGRESQL_PASSWORD={psql_password}" if psql_password else ""
        )
        psql_database_arg = (
            f"-e POSTGRESQL_DATABASE={psql_database}" if psql_database else ""
        )
        psql_admin_password_arg = (
            f"-e POSTGRESQL_ADMIN_PASSWORD={psql_admin_password}"
            if psql_admin_password
            else ""
        )
        assert self.db.assert_container_creation_fails(
            cid_file_name=cid_file_name,
            container_args=[
                psql_user_arg,
                psql_password_arg,
                psql_database_arg,
                psql_admin_password_arg,
            ],
            command="",
        )


class TestPostgreSQLValidConfigurations:
    """
    Test PostgreSQL container valid configurations tests.
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
                "the @password",
            ],
            [
                "the user",
                "the pass",
                "the db",
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
        psql_user_arg = f'-e POSTGRESQL_USER="{psql_user}"' if psql_user else ""
        psql_password_arg = (
            f'-e POSTGRESQL_PASSWORD="{psql_password}"' if psql_password else ""
        )
        psql_database_arg = (
            f'-e POSTGRESQL_DATABASE="{psql_database}"' if psql_database else ""
        )
        psql_admin_password_arg = (
            f'-e POSTGRESQL_ADMIN_PASSWORD="{psql_admin_password}"'
            if psql_admin_password
            else ""
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
        cip, cid = self.db.get_cip_cid(cid_file_name=cid_file_name)
        assert cip and cid
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


class TestPostgreSQLBufferHooks:
    """
    Test PostgreSQL container buffer hooks tests.
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

    def test_configuration_hook(self):
        """
        Test buffer hook configurations.
        """
        self.shared_buffer_test("32MB")
        self.shared_buffer_test("113MB")
        self.shared_buffer_test("111MB")

    def shared_buffer_test(self, shared_buffer_value):
        """
        Test buffer hook configurations.
        Args:
            shared_buffer_value: The value of the shared buffer to test.
        Steps:
        1. Create a container with the given shared buffer value.
        2. Wait for the database to be ready.
        3. Check if the shared buffer value is set correctly.
        """
        cid_file_name = f"test_pg_hook_{shared_buffer_value}"
        container_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            f"-e POSTGRESQL_SHARED_BUFFERS={shared_buffer_value}",
            f"-v {volume_dir}:/opt/app-root/src:Z",
        ]

        assert self.db.create_container(
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )
        cip, cid = self.db.get_cip_cid(cid_file_name=cid_file_name)
        assert cip and cid
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
