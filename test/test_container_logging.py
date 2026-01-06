import re

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.database import DatabaseWrapper
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper

from conftest import VARS, create_postgresql_volume_dir


class TestPostgreSQLLoggingContainer:
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

    def test_logging_destination(self):
        """
        Test logging destination.
        """
        cid_file_name = "test_pg_logging"
        volume_dir = create_postgresql_volume_dir()
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            "-e POSTGRESQL_LOG_DESTINATION=/dev/stderr",
            f"-v {volume_dir}:/var/lib/pgsql/data:Z",
        ]

        assert self.db.create_container(
            cid_file_name=cid_file_name,
            docker_args=docker_args,
            command="",
        )
        cip = self.db.get_cip(cid_file_name=cid_file_name)
        assert cip
        cid = self.db.get_cid(cid_file_name=cid_file_name)
        assert cid
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )

        output = PodmanCLIWrapper.call_podman_command(
            cmd=f"exec {cid} bash -c \"psql -tA -c 'SHOW log_destination;'\"",
        )
        # TODO NEED TO FIX THIS
        # assert "logging_collector log_directory log_filename" in output, (
        #     f"logging_collector log_directory log_filename should be in the log_destination, but is {output}"
        # )
        assert "stderr" in output, (
            f"stderr should be in the log_destination, but is {output}"
        )
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )

        output = PodmanCLIWrapper.call_podman_command(
            cmd=f"exec {cid} bash -c 'psql -U nonexistent'",
            ignore_error=True,
        )

        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        logs = PodmanCLIWrapper.podman_logs(
            container_id=cid,
        )
        assert re.search('FATAL:\\s*role "nonexistent" does not exist', logs), (
            "ERROR: the container log does not include expected error message"
        )
        assert not (Path(volume_dir) / "userdata" / "log").exists(), (
            f"ERROR: the traditional log file {Path(volume_dir) / 'userdata' / 'log'} should not exist"
        )
