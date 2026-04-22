import re
from time import sleep

from container_ci_suite.container_lib import ContainerTestLib

from conftest import VARS, create_and_wait_for_container


class TestPostgreSQLReplicationContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()

    def test_replication(self):
        """
        Test replication.
        """
        database = "postgres"
        master_user = "master"
        master_password = "master"
        master_hostname = "postgresql-master"
        master_cid_name = "master-basic"
        slave_cid_name = "slave-basic"

        container_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=pass",
            f"-e POSTGRESQL_MASTER_USER={master_user}",
            f"-e POSTGRESQL_MASTER_PASSWORD={master_password}",
        ]
        # Run the PostgreSQL master
        _, master_cip = create_and_wait_for_container(
            db=self.db,
            cid_file_name=master_cid_name,
            container_args=container_args,
            command="run-postgresql-master",
        )
        container_args += [
            f"--add-host {master_hostname}:{master_cip}",
            f"-e POSTGRESQL_MASTER_IP={master_hostname}",
        ]
        _, slave_cip = create_and_wait_for_container(
            db=self.db,
            cid_file_name=slave_cid_name,
            container_args=container_args,
            command="run-postgresql-slave",
        )
        output = self.db.db_lib.run_sql_command(
            container_ip=master_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd="-c 'select client_addr from pg_stat_replication;'",
            expected_output=f"{slave_cip}",
        )
        assert slave_cip in output, (
            f"Replica {slave_cip} not found in MASTER {master_cip}"
        )
        # Test the replication
        output = self.db.db_lib.run_sql_command(
            container_ip=master_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd="-c 'CREATE TABLE t1 (a integer); INSERT INTO t1 VALUES (24);'",
        )
        # let's wait for the table to be created and available for replication
        sleep(3)
        output = self.db.db_lib.run_sql_command(
            container_ip=slave_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd="-At -c 'select * from t1;'",
        )
        assert re.search(r"^24", output), (
            f"Value 24 not found in REPLICA {slave_cip} for table t1"
        )
