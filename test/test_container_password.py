import tempfile

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.container_lib import ContainerTestLibUtils
from container_ci_suite.container_lib import DatabaseWrapper
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper

from conftest import VARS, check_db_output


class TestPostgreSQLPasswordChangeContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.pwd_change = ContainerTestLib(image_name=VARS.IMAGE_NAME)
        self.pwd_change.set_new_db_type(db_type="postgresql")
        self.dw_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.pwd_change.cleanup()

    def test_password_change(self):
        """
        Test password change.
        """
        pwd_dir = tempfile.mkdtemp(prefix="/tmp/psql-pwd-change")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {pwd_dir}",
            ]
        )
        pwd_file_name = "test_password_change"
        volume_options = f"-v {pwd_dir}:/var/lib/pgsql/data:Z"
        database = "db"
        username = "user"
        password = "password"
        admin_password = "adminPassword"
        assert self.pwd_change.create_container(
            cid_file_name=pwd_file_name,
            container_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
                volume_options,
            ],
        )
        cip1, cid1 = self.pwd_change.get_cip_cid(cid_file_name=pwd_file_name)
        assert cip1 and cid1
        assert self.pwd_change.test_db_connection(
            container_ip=cip1,
            username=username,
            password=password,
        )
        login_access = True
        for user, pwd in [
            (username, password),
            ("postgres", admin_password),
        ]:
            test_assert = self.pwd_change.db_lib.assert_login_access(
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
        assert self.pwd_change.test_db_connection(
            container_ip=cip1, username=username, password=password
        )
        # test_postgresql
        self.dw_api.run_sql_command(
            container_ip=cip1,
            username=username,
            password=password,
            container_id=VARS.IMAGE_NAME,
            database=database,
            sql_cmd='-At -c "CREATE TABLE tbl (a integer, b integer);"',
        )

        self.dw_api.run_sql_command(
            container_ip=cip1,
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
        check_db_output(
            dw_api=self.dw_api,
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
        assert self.pwd_change.create_container(
            cid_file_name=pwd_file_name_new,
            container_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={new_password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={new_admin_password}",
                volume_options,
            ],
        )
        cip_new, cid_new = self.pwd_change.get_cip_cid(cid_file_name=pwd_file_name_new)
        assert cip_new and cid_new

        assert self.pwd_change.test_db_connection(
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
            ("postgres", "admin_password", False),
        ]:
            # Let's check login access for user and pwd combinations
            # with expected ret_value. Otherwise let's failed.
            test_assert = self.pwd_change.db_lib.assert_login_access(
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
        self.dw_api.run_sql_command(
            container_ip=cip_new,
            username=username,
            password=password,
            container_id=VARS.IMAGE_NAME,
        )
        check_db_output(
            dw_api=self.dw_api,
            cip=cip_new,
            username=username,
            password=new_password,
            database=database,
        )
