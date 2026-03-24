import re
import pytest

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.container_lib import DatabaseWrapper

from conftest import VARS, check_db_output


class TestPostgreSQLGeneralContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db_image = ContainerTestLib(
            image_name=VARS.IMAGE_NAME, db_type="postgresql"
        )
        self.db_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db_image.cleanup()

    @pytest.mark.parametrize(
        "container_args, psql_user, psql_password, psql_database, root_password, test_name",
        [
            ("", "user", "pass", "", "", "no_admin"),
            ("", "user1", "pass1", "", "r00t", "admin"),
            ("", "", "", "postgres", "r00t", "only_admin"),
            ("-u 12345", "user2", "pass", "", "", "no_admin_altuid"),
            ("-u 12345", "user3", "pass1", "", "r00t", "admin_altuid"),
            ("-u 12345", "", "", "postgres", "r00t", "only_admin_altuid"),
        ],
    )
    def test_run(
        self,
        container_args,
        psql_user,
        psql_password,
        psql_database,
        root_password,
        test_name,
    ):
        """
        Test PostgreSQL container general usage.
        Steps are:
        1. Create a container with the given arguments.
        2. Check if the container is created successfully
        3. Check if the database connection works.
        4. Check if the PostgreSQL version is correct.
        5. Check if the login access works.
        6. Check if the local access works.
        7. Test the database creation.
        """
        psql_max_connections = 42 if test_name == "no_admin" else 100
        psql_max_prepared_transactions = 42 if test_name == "no_admin" else 0
        psql_shared_buffers = "64MB" if test_name == "no_admin" else "32MB"
        expected_success = expected_admin_success = False
        psql_user_arg = psql_pwd_arg = db_name_arg = admin_root_password_arg = ""
        if psql_user != "":
            psql_user_arg = f"-e POSTGRESQL_USER={psql_user}"
            expected_success = True
        if psql_password:  # empty password is allowed
            psql_pwd_arg = f"-e POSTGRESQL_PASSWORD={psql_password}"
        if psql_user and psql_password:
            db_name_arg = "-e POSTGRESQL_DATABASE=db"
        if root_password == "r00t":
            admin_root_password_arg = f"-e POSTGRESQL_ADMIN_PASSWORD={root_password}"
            expected_admin_success = True
        container_all_args = [
            psql_user_arg,
            psql_pwd_arg,
            db_name_arg,
            admin_root_password_arg,
            f"-e POSTGRESQL_MAX_CONNECTIONS={psql_max_connections}",
            f"-e POSTGRESQL_MAX_PREPARED_TRANSACTIONS={psql_max_prepared_transactions}",
            f"-e POSTGRESQL_SHARED_BUFFERS={psql_shared_buffers}",
            f"{container_args}",
        ]
        cid_file_name = test_name
        assert self.db_image.create_container(
            cid_file_name=cid_file_name, container_args=container_all_args
        )
        cip, cid = self.db_image.get_cip_cid(cid_file_name=cid_file_name)
        assert cip and cid
        if root_password:
            assert self.db_image.test_db_connection(
                container_ip=cip,
                username="postgres",
                password=root_password,
                database="postgres",
                max_attempts=10,
            )
        else:
            assert self.db_image.test_db_connection(
                container_ip=cip,
                username=psql_user,
                password=psql_password,
                max_attempts=10,
            )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd="psql --version",
        )
        assert VARS.VERSION in output
        login_access = True
        if psql_database == "":
            psql_database = "db"
        for user, pwd, ret_value in [
            (psql_user, psql_password, expected_success),
            (psql_user, f"{psql_password}_foo", False),
            ("postgres", root_password, expected_admin_success),
            ("postgres", f"{root_password}_foo", False),
        ]:
            test_assert = self.db_image.db_lib.assert_login_access(
                container_ip=cip,
                username=user,
                password=pwd,
                expected_success=ret_value,
                database=psql_database,
            )
            if not test_assert:
                print(
                    f"Login access failed for {user}:{pwd} with expected success {ret_value}"
                )
                login_access = False
        assert login_access
        assert self.db_image.db_lib.assert_local_access(container_id=cid)
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd="cat /var/lib/pgsql/openshift-custom-postgresql.conf",
        )

        rows = [
            rf"max_connections\s*=\s*{psql_max_connections}",
            rf"max_prepared_transactions\s*=\s*{psql_max_prepared_transactions}",
            rf"shared_buffers\s*=\s*{psql_shared_buffers}",
        ]
        for row in rows:
            assert re.search(row, output), f"Row {row} not found in {output}"
        # test_postgresql
        if test_name == "admin":
            assert self.db_api.run_sql_command(
                container_ip=cip,
                username="postgres",
                password=root_password,
                container_id=VARS.IMAGE_NAME,
                database="postgres",
                sql_cmd="-At -c 'CREATE EXTENSION \"uuid-ossp\";'",
            )
        if psql_password == "":
            psql_password = root_password

        self.database_test(cip, psql_user, psql_password, psql_database)

    def database_test(self, cip, psql_user, psql_password, psql_database):
        """
        Test PostgreSQL database creation and data insertion is valid.
        Steps are:
        1. Create a table with the given name and columns.
        2. Insert data into the table.
        3. Select data from the table.
        4. Drop the table.
        """
        self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd='-At -c "CREATE TABLE tbl (a integer, b integer);"',
        )

        self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd=[
                '-At -c "INSERT INTO tbl VALUES (1, 2);"',
                '-At -c "INSERT INTO tbl VALUES (3, 4);"',
                '-At -c "INSERT INTO tbl VALUES (5, 6);"',
            ],
        )
        check_db_output(
            dw_api=self.db_api,
            cip=cip,
            username=psql_user,
            password=psql_password,
            database=psql_database,
        )
        self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd='-At -c "DROP TABLE tbl;"',
        )
