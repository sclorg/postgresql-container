import tempfile
import re

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.container_lib import ContainerTestLibUtils
from container_ci_suite.container_lib import DatabaseWrapper
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper

from conftest import VARS


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
        cid_file_name1 = "test_password_change"
        pwd_dir = tempfile.mkdtemp(prefix="/tmp/psql-pwd")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {pwd_dir}",
            ]
        )
        volume_options = f"-v {pwd_dir}:/var/lib/pgsql/data:Z"
        database = "db"
        username = "user"
        password = "password"
        admin_password = "adminPassword"
        assert self.pwd_change.create_container(
            cid_file_name=cid_file_name1,
            docker_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
                volume_options,
            ],
        )
        cip1 = self.pwd_change.get_cip(cid_file_name=cid_file_name1)
        assert cip1
        assert self.pwd_change.test_db_connection(
            container_ip=cip1,
            username=username,
            password=password,
            max_attempts=10,
        )
        cid1 = self.pwd_change.get_cid(cid_file_name=cid_file_name1)
        assert cid1
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip1,
            username=username,
            password=password,
            expected_success=True,
        )
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip1,
            username="postgres",
            password=admin_password,
            expected_success=True,
        )
        assert self.pwd_change.test_db_connection(
            container_ip=cip1, username=username, password=password
        )
        # test_postgresql
        output = self.dw_api.run_sql_command(
            container_ip=cip1,
            username=username,
            password=password,
            container_id=VARS.IMAGE_NAME,
            database=database,
            sql_cmd='-At -c "CREATE TABLE tbl (a integer, b integer);"',
            expected_output="CREATE TABLE",
        )

        output = self.dw_api.run_sql_command(
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
            expected_output="INSERT 0 1",
        )
        output = self.dw_api.run_sql_command(
            container_ip=cip1,
            username=username,
            password=password,
            container_id=VARS.IMAGE_NAME,
            database=database,
            sql_cmd='-At -c "SELECT * FROM tbl;"',
        )
        words = [
            "1|2",
            "3|4",
            "5|6",
        ]
        for word in words:
            assert re.search(word, output), f"Word {word} not found in {output}"
        PodmanCLIWrapper.call_podman_command(cmd=f"kill {cid1}")
        PodmanCLIWrapper.call_podman_command(cmd=f"rm -f {cid1}")
        cid_file_name_new = "test_password_change_new_password"
        new_password = f"NEW_{password}"
        new_admin_password = f"NEW_{admin_password}"
        assert self.pwd_change.create_container(
            cid_file_name=cid_file_name_new,
            docker_args=[
                f"-e POSTGRESQL_USER={username}",
                f"-e POSTGRESQL_PASSWORD={new_password}",
                f"-e POSTGRESQL_DATABASE={database}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={new_admin_password}",
                volume_options,
            ],
        )
        cip_new = self.pwd_change.get_cip(cid_file_name=cid_file_name_new)
        assert cip_new
        assert self.pwd_change.test_db_connection(
            container_ip=cip_new,
            username=username,
            password=new_password,
            max_attempts=10,
        )
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip_new,
            username=username,
            password=new_password,
            expected_success=True,
        )
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip_new,
            username=username,
            password=password,
            expected_success=False,
        )
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip_new,
            username="postgres",
            password=new_admin_password,
            expected_success=True,
        )
        self.pwd_change.db_lib.assert_login_access(
            container_ip=cip_new,
            username="postgres",
            password=admin_password,
            expected_success=False,
        )
        output = self.dw_api.run_sql_command(
            container_ip=cip_new,
            username=username,
            password=password,
            container_id=VARS.IMAGE_NAME,
            ignore_error=True,
        )
        output = self.dw_api.run_sql_command(
            container_ip=cip_new,
            username=username,
            password=new_password,
            container_id=VARS.IMAGE_NAME,
            database=database,
            sql_cmd='-At -c "SELECT * FROM tbl;"',
        )
        words = [
            "1|2",
            "3|4",
            "5|6",
        ]
        for word in words:
            assert re.search(word, output), f"Word {word} not found in {output}"
