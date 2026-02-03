import re
import pytest

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.container_lib import DatabaseWrapper

from conftest import VARS


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
        "docker_args, psql_user, psql_password, psql_database, root_password, test_name",
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
        docker_args,
        psql_user,
        psql_password,
        psql_database,
        root_password,
        test_name,
    ):
        """
        Test PostgreSQL container general usage.
        """
        POSTGRESQL_MAX_CONNECTIONS = 100
        POSTGRESQL_MAX_PREPARED_TRANSACTIONS = 0
        POSTGRESQL_SHARED_BUFFERS = "32MB"
        if test_name == "no_admin":
            POSTGRESQL_MAX_CONNECTIONS = 42
            POSTGRESQL_MAX_PREPARED_TRANSACTIONS = 42
            POSTGRESQL_SHARED_BUFFERS = "64MB"
        expected_success = False
        expected_admin_success = False
        psql_user_arg = ""
        psql_pwd_arg = ""
        db_name_arg = ""
        admin_root_password_arg = ""
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
        docker_all_args = [
            psql_user_arg,
            psql_pwd_arg,
            db_name_arg,
            admin_root_password_arg,
            f"-e POSTGRESQL_MAX_CONNECTIONS={POSTGRESQL_MAX_CONNECTIONS}",
            f"-e POSTGRESQL_MAX_PREPARED_TRANSACTIONS={POSTGRESQL_MAX_PREPARED_TRANSACTIONS}",
            f"-e POSTGRESQL_SHARED_BUFFERS={POSTGRESQL_SHARED_BUFFERS}",
            f"{docker_args}",
        ]
        cid_file_name = test_name
        assert self.db_image.create_container(
            cid_file_name=cid_file_name, docker_args=docker_all_args
        )
        cip = self.db_image.get_cip(cid_file_name=cid_file_name)
        assert cip
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
        cid = self.db_image.get_cid(cid_file_name=cid_file_name)
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd="psql --version",
        )
        assert VARS.VERSION in output
        access_output = True
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
                access_output = False
                break
        assert access_output, "Login access failed for above results"
        assert self.db_image.db_lib.assert_local_access(container_id=cid)
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd="cat /var/lib/pgsql/openshift-custom-postgresql.conf",
        )

        words = [
            f"max_connections\\s*=\\s*{POSTGRESQL_MAX_CONNECTIONS}",
            f"max_prepared_transactions\\s*=\\s*{POSTGRESQL_MAX_PREPARED_TRANSACTIONS}",
            f"shared_buffers\\s*=\\s*{POSTGRESQL_SHARED_BUFFERS}",
        ]
        for word in words:
            assert re.search(word, output), f"Word {word} not found in {output}"
        # test_postgresql
        if test_name == "admin":
            output = self.db_api.run_sql_command(
                container_ip=cip,
                username="postgres",
                password=root_password,
                container_id=VARS.IMAGE_NAME,
                database="postgres",
                sql_cmd="-At -c 'CREATE EXTENSION \"uuid-ossp\";'",
                expected_output="CREATE EXTENSION",
            )
        if psql_password == "":
            psql_password = root_password

        self.database_test(cip, psql_user, psql_password, psql_database)

    def database_test(self, cip, psql_user, psql_password, psql_database):
        """
        Test PostgreSQL database creation.
        """
        output = self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd='-At -c "CREATE TABLE tbl (a integer, b integer);"',
            expected_output="CREATE TABLE",
        )

        output = self.db_api.run_sql_command(
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
            expected_output="INSERT 0 1",
        )
        output = self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd='-At -c "SELECT * FROM tbl;"',
        )
        words = [
            "1|2",
            "3|4",
            "5|6",
        ]
        for word in words:
            assert re.search(word, output), f"Word {word} not found in {output}"
        self.db_api.run_sql_command(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            container_id=VARS.IMAGE_NAME,
            database=psql_database,
            sql_cmd='-At -c "DROP TABLE tbl;"',
            expected_output="DROP TABLE",
        )
