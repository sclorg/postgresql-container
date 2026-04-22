import re

from pathlib import Path
import shutil

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.container import ContainerTestLibUtils
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.utils import tempfile

from conftest import VARS, create_and_wait_for_container


class TestPostgreSQLLoggingContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type=VARS.DB_TYPE)
        self.logging_dir = tempfile.mkdtemp(prefix="/tmp/psql-logging-volume-dir")
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -m u:26:-wx {self.logging_dir}",
            ]
        )

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()
        shutil.rmtree(self.logging_dir, ignore_errors=True)

    def test_logging_destination(self):
        """
        Test logging destination.
        """
        cid_file_name = "test_pg_logging"
        container_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            "-e POSTGRESQL_LOG_DESTINATION=/dev/stderr",
            f"-v {self.logging_dir}:/var/lib/pgsql/data:Z",
        ]
        cid, _ = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_file_name,
            container_args=container_args,
            command="",
        )

        output = PodmanCLIWrapper.call_podman_command(
            cmd=f"exec {cid} bash -c \"psql -tA -c 'SHOW log_destination;'\"",
        )
        assert "stderr" in output, (
            f"stderr should be in the log_destination, but is {output}"
        )
        assert self.db.db_lib.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )

        PodmanCLIWrapper.call_podman_command(
            cmd=f"exec {cid} bash -c 'psql -U nonexistent'",
            ignore_error=True,
        )

        assert self.db.db_lib.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        logs = PodmanCLIWrapper.podman_logs(
            container_id=cid,
        )
        assert re.search('FATAL:\\s*role "nonexistent" does not exist', logs), (
            "ERROR: the container log does not include expected error message"
        )
        assert not (Path(self.logging_dir) / "userdata" / "log").exists(), (
            "ERROR: the traditional log file should not exist"
        )
