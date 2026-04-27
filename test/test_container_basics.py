import shutil
import tempfile

from container_ci_suite.utils import ContainerTestLibUtils

from conftest import VARS, create_and_wait_for_container, build_s2i_app


class TestPostgreSQLBasicsContainer:

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.app_image = build_s2i_app(app_path=VARS.TEST_APP)

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.app_image.cleanup()

    def test_backup_functionality(self):
        """
        Test backup functionality of the PostgreSQL container.
        Steps are:
        1. Test if the container creation fails with invalid combinations of arguments
        2. Test if the container creation succeeds with valid combinations of arguments
        3. Test if the database connection works
        4. Test if the database backup works properly by adding a backup_user.sh script
        """
        with tempfile.NamedTemporaryFile(prefix="/tmp/psql-temp-file") as temp_file:
            cid_create = "conf_backup"
            psql_password = "password"
            psql_database = "db"
            psql_user = "user"
            psql_admin_password = psql_password
            psql_backup_user = "backuser"
            psql_backup_password = "pass"
            self.app_image.assert_container_creation_fails(
                cid_file_name=cid_create,
                command="",
                container_args=[
                    f"-e POSTGRESQL_PASSWORD={psql_password}",
                    f"-e POSTGRESQL_DATABASE={psql_database}",
                ],
            )
            container_args = [
                f"-e POSTGRESQL_USER={psql_user}",
                f"-e POSTGRESQL_PASSWORD={psql_password}",
                f"-e POSTGRESQL_DATABASE={psql_database}",
                f"-e POSTGRESQL_BACKUP_USER={psql_backup_user}",
                f"-e POSTGRESQL_BACKUP_PASSWORD={psql_backup_password}",
                f"-e POSTGRESQL_ADMIN_PASSWORD={psql_admin_password}",
            ]
            cid_create, cip_create = create_and_wait_for_container(
                db=self.app_image,
                cid_file_name=cid_create,
                container_args=container_args,
                command="",
            )
            self.check_psql_connection(cip_create, psql_user, psql_password)
            backup_user_script = (
                VARS.TEST_DIR / "test-app/postgresql-init/backup_user.sh"
            )
            shutil.copy(backup_user_script, temp_file.name)
            ContainerTestLibUtils.commands_to_run(
                commands_to_run=[
                    f"setfacl -m u:26:rw- {temp_file.name}",
                ]
            )

            cid_backup = "cid_backup"
            mount_point = "/opt/app-root/src/postgresql-init/add_backup_user.sh"
            container_args.extend(
                [
                    f"-v {temp_file.name}:{mount_point}:z,ro",
                ]
            )
            cid_backup, cip_backup = create_and_wait_for_container(
                db=self.app_image,
                cid_file_name=cid_backup,
                container_args=container_args,
                command="",
            )
            self.check_psql_connection(
                cip_backup, psql_backup_user, psql_backup_password
            )

    def check_psql_connection(self, cip, psql_user, psql_password):
        """
        Check the PostgreSQL connection.
        Check also connection to the backup database.
        """
        assert self.app_image.test_db_connection(
            container_ip=cip, username=psql_user, password=psql_password
        )
        assert self.app_image.test_db_connection(
            container_ip=cip,
            username=psql_user,
            password=psql_password,
            database="backup",
        )
