import tempfile

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.container_lib import ContainerTestLibUtils
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.utils import shutil

from conftest import VARS, check_db_output, create_and_wait_for_container


class TestPostgreSQLPasswordChangeContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)
        self.pwd_dir = tempfile.mkdtemp(prefix="/tmp/psql-pwd-change")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {self.pwd_dir}",
            ]
        )

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()
        shutil.rmtree(self.pwd_dir, ignore_errors=True)

    def test_password_change(self):
        """
        Test password change.
        """

        pwd_file_name = "test_password_change"
        volume_options = f"-v {self.pwd_dir}:/var/lib/pgsql/data:Z"
        database = "db"
        username = "user"
        password = "password"
        admin_password = "adminPassword"
        cid1, cip1 = create_and_wait_for_container(
            db=self.db,
            cid_file_name=pwd_file_name,
            container_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
                volume_options,
            ],
            command="",
        )
        assert self.db.test_db_connection(
            container_ip=cip1,
            username=username,
            password=password,
        )
        login_access = True
        for user, pwd in [
            (username, password),
            ("postgres", admin_password),
        ]:
            test_assert = self.db.db_lib.assert_login_access(
                container_ip=cip1,
                username=user,
                password=pwd,
                expected_success=True,
            )
            if not test_assert:
                print(
                    f"Login access failed for {user}:{pwd} with expected success {True}"
                )
                login_access = False
        assert login_access
        assert self.db.test_db_connection(
            container_ip=cip1, username=username, password=password
        )
        check_db_output(
            dw_api=self.db.db_lib,
            cip=cip1,
            username=username,
            password=password,
            database=database,
        )

        PodmanCLIWrapper.call_podman_command(cmd=f"kill {cid1}")
        PodmanCLIWrapper.call_podman_command(cmd=f"rm {cid1}")
        pwd_file_name_new = "test_password_change_new_password"
        new_password = f"NEW_{password}"
        new_admin_password = f"NEW_{admin_password}"
        _, cip_new = create_and_wait_for_container(
            db=self.db,
            cid_file_name=pwd_file_name_new,
            container_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={new_password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={new_admin_password}",
                volume_options,
            ],
            command="",
        )
        assert self.db.test_db_connection(
            container_ip=cip_new,
            username=username,
            password=new_password,
            max_attempts=10,
        )

        login_access = True
        for user, pwd, ret_value in [
            (username, new_password, True),
            (username, password, False),
            ("postgres", new_admin_password, True),
            ("postgres", admin_password, False),
        ]:
            # Let's check login access for user and pwd combinations
            # with expected ret_value
            test_assert = self.db.db_lib.assert_login_access(
                container_ip=cip_new,
                username=user,
                password=pwd,
                expected_success=ret_value,
            )
            if not test_assert:
                print(
                    f"Login access failed for {user}:{pwd} with expected success {ret_value}"
                )
                login_access = False
        assert login_access
        check_db_output(
            dw_api=self.db.db_lib,
            cip=cip_new,
            username=username,
            password=new_password,
            database=database,
        )
