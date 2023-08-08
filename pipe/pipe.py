#!/usr/bin/env python3

from operator import sub
import os
import shutil
from sre_constants import SUCCESS
import subprocess
from sys import stdout
import sys
import uuid
import re
from bitbucket import Bitbucket
from bitbucket_pipes_toolkit import Pipe, get_logger


logger = get_logger()
schema = {
    'SKIP_DEPENDENCIES': {'type': 'string', 'required': False, 'allowed': ['true', 'false']},
    'AUTOLOADER': {'type': 'string', 'required': False},
    'IGNORE_PLATFORM_DEPENDENCIES': {'type': 'string', 'required': False, 'allowed': ['true', 'false']},
    'LEVEL': {'type': 'integer', 'required': False, 'min': 1, 'max': 9},
    'EXCLUDE_EXPRESSION': {'type': 'string', 'required': False},
    'CONFIG_FILE': {'type': 'string', 'required': False},
    'SCAN_DIRECTORY': {'type': 'string', 'required': False},
    'DISABLE_REPORT': {'type': 'string', 'required': False, 'allowed': ['true', 'false']},
    'DEBUG': {'type': 'boolean', 'required': False}
}


class PHPStan(Pipe):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Composer Configuration
        self.skip_dependencies = self.get_variable('SKIP_DEPENDENCIES') == 'true'
        self.ignore_platform_dependencies = self.get_variable('IGNORE_PLATFORM_DEPENDENCIES') == 'true'

        # PHPStan Configuration
        self.config_file = self.get_variable('CONFIG_FILE')
        self.autoloader = self.get_variable('AUTOLOADER')
        self.level = self.get_variable('LEVEL')
        self.exclude_expression = self.get_variable('EXCLUDE_EXPRESSION')
        self.scan_directory = self.get_variable('SCAN_DIRECTORY')

        # Bitbucket Configuration
        self.bitbucket_workspace = os.getenv('BITBUCKET_WORKSPACE')
        self.bitbucket_repo_slug = os.getenv('BITBUCKET_REPO_SLUG')
        self.bitbucket_pipeline_uuid = os.getenv('BITBUCKET_PIPELINE_UUID')
        self.bitbucket_step_uuid = os.getenv('BITBUCKET_STEP_UUID')
        self.bitbucket_commit = os.getenv('BITBUCKET_COMMIT')

        # Enable/Disable Bitbucket reporting
        self.disable_report = self.get_variable('DISABLE_REPORT') == 'true'

    def setup_ssh_credentials(self):
        ssh_dir = os.path.expanduser("~/.ssh/")
        injected_ssh_config_dir = "/opt/atlassian/pipelines/agent/ssh"
        identity_file = f"{injected_ssh_config_dir}/id_rsa_tmp"
        known_servers_file = f"{injected_ssh_config_dir}/known_hosts"

        if not os.path.exists(identity_file):
            self.fail(message="No default SSH key configured in Pipelines.\n These are required to install internal composer packages. \n These should be generated in bitbucket settings at Pipelines > SSH Keys.")

        if not os.path.exists(known_servers_file):
            self.fail(message="No SSH known_hosts configured in Pipelines.")

        os.mkdir(ssh_dir)
        shutil.copy(identity_file, f"{ssh_dir}pipelines_id")

        # Read contents of pipe-injected known hosts and pipe into
        # runtime ssh config
        with open(known_servers_file) as pipe_known_host_file:
            with open(f"{ssh_dir}known_hosts", 'a') as known_host_file:
                for line in pipe_known_host_file:
                    known_host_file.write(line)

        with open(f"{ssh_dir}config", 'a') as config_file:
            config_file.write("IdentityFile ~/.ssh/pipelines_id")

        subprocess.run(["chmod", "-R", "go-rwx", ssh_dir], check=True)

    def run_phpstan(self):
        target_branch = "origin/main"
        if os.getenv("BITBUCKET_PR_DESTINATION_BRANCH"):
            target_branch = f"origin/{os.getenv('BITBUCKET_PR_DESTINATION_BRANCH')}"

        # Output is terminated with newline char, remove it.
        if self.scan_directory is None:
          self.log_info(f"Comparing HEAD against branch {target_branch}")
          merge_base = subprocess.check_output(["git",
                                                "merge-base",
                                                "HEAD",
                                                target_branch
                                                ]).decode(sys.stdout.encoding)[:-1]
          self.log_info(f"Comparing HEAD against merge base {merge_base}")
          changed_files = subprocess.check_output(["git",
                                                  "diff",
                                                   "--relative",
                                                   "--name-only",
                                                   "--diff-filter=AM",
                                                   merge_base,
                                                   "--",
                                                   "*.php"
                                                   ]).decode(sys.stdout.encoding).split('\n')
        else:
          changed_files = [self.scan_directory]

        # Filter empty strings
        changed_files = list(filter(None, changed_files))

        if self.exclude_expression:
            def filter_paths(path):
                match = re.search(self.exclude_expression, path)
                if match:
                    self.log_info(f"Excluding: {path}")
                else:
                    self.log_info(f"Testing: {path}")
                return not match

            changed_files = list(filter(filter_paths, changed_files))

        else:
            self.log_info(f"Exclude expression not provided. All changed files will be scanned.")

        if not changed_files:
            self.success("No changed files to scan")
            self.failure = False
            return

        if not os.path.exists("test-results"):
            os.mkdir("test-results")

        phpstan_command = ["/composer/vendor/bin/phpstan", "analyse"] + changed_files

        phpstan_command.append("--error-format=junit")

        if self.config_file:
          phpstan_command.append(f"--configuration={self.config_file}")

        if self.autoloader:
          phpstan_command.append(f"--autoload-file={self.autoloader}")
        else:
          phpstan_command.append(f"--autoload-file=vendor/autoload.php")

        if self.level:
          phpstan_command.append(f"--level={self.level}")

        self.log_debug(f'Executing PHPStan command {phpstan_command}')

        phpstan = subprocess.run(
          args=phpstan_command,
          capture_output=True,
          universal_newlines=True)

        self.failure = phpstan.returncode != 0

        phpstan_output = phpstan.stdout

        if phpstan_output:
            with open("test-results/phpstan.xml", 'a') as output_file:
                output_file.write(phpstan_output)

    def composer_install(self):
        composer_install_command = ["composer", "install", "--dev"]

        if self.ignore_platform_dependencies:
          composer_install_command.append('--ignore-platform-dependencies')

        self.log_debug(f'Executing Composer command {composer_install_command}')

        composer_install = subprocess.run(composer_install_command)
        composer_install.check_returncode()

    def upload_report(self):
        # Parses a Junit file and returns all errors
        def read_failures_from_file(file):
            from junitparser import JUnitXml

            results = []
            suite = JUnitXml.fromfile(file)
            if not suite.failures:
                return []
            for case in suite:
                  for result in case.result:
                      # Covert paths to relative equivalent
                      workspace_path = "/opt/atlassian/pipelines/agent/build/"
                      path = case.name.replace(workspace_path, '')
                      results.append({
                          "path": re.search("(.*\.php):\d*", path).group(1),
                          "title": case.name,
                          "summary": result.message,
                          # Extract line number from name
                          # Example: src/AppKernel.php:42
                          "line": re.search("\.*:(\d*)", case.name).group(1)
                      })

            return results

        # Builds a report given a number of failures
        def build_report_data(failure_count):
            report_data = [
                {
                    "title": 'Failures',
                    "type": 'NUMBER',
                    "value": failure_count
                }
            ]

            return report_data

        report_id = str(uuid.uuid4())

        bitbucket_api = Bitbucket(
            proxies={"http": 'http://host.docker.internal:29418'})

        failures = []
        if os.path.exists("test-results/phpstan.xml"):
            failures = read_failures_from_file(f"test-results/phpstan.xml")
        
        # self.log_debug(f"bitbucket_workspace: {self.bitbucket_workspace}")
        # self.log_debug(f"bitbucket_repo_slug: {self.bitbucket_repo_slug}")
        # self.log_debug(f"bitbucket_commit: {self.bitbucket_commit}")
        # self.log_debug(f"bitbucket_step_uuid: {self.bitbucket_step_uuid}")
        # self.log_debug(f"link: https://bitbucket.org/{self.bitbucket_workspace}/{self.bitbucket_repo_slug}/addon/pipelines/home#!/results/{self.bitbucket_pipeline_uuid}/steps/{self.bitbucket_step_uuid}/test-report")

        bitbucket_api.create_report(
            "PHPStan report",
            "Results produced by running PHPStan against updated files",
            "SECURITY",
            report_id,
            "phpstan-pipe",
            "FAILED" if len(failures) else "PASSED",
            f'"text": "Link text here", "href":"https://bitbucket.org/{self.bitbucket_workspace}/{self.bitbucket_repo_slug}/addon/pipelines/home#!/results/{self.bitbucket_pipeline_uuid}/steps/{self.bitbucket_step_uuid}/test-report"',
            build_report_data(len(failures)),
            self.bitbucket_workspace,
            self.bitbucket_repo_slug,
            self.bitbucket_commit
        )

        for failure in failures:
            self.log_debug(f"Submitting failure: {failure}")
            bitbucket_api.create_annotation(
                failure["title"],
                failure["summary"],
                "MEDIUM",
                failure["path"],
                failure["line"],
                "phpstan-pipe",
                report_id,
                "CODE_SMELL",
                str(uuid.uuid4()),
                self.bitbucket_workspace,
                self.bitbucket_repo_slug,
                self.bitbucket_commit
            )

    def run(self):
        super().run()
        if not self.skip_dependencies:
            self.log_debug("Setting up ssh credentials.")
            self.setup_ssh_credentials()
            self.log_debug("Installing Dependencies.")
            self.composer_install()
        else:
            self.log_debug("Skipping dependency installation.")

        self.log_debug("Running PHPStan.")
        self.run_phpstan()

        if not self.disable_report:
          self.log_debug("Uploading test results to Bitbucket.")
          self.upload_report()

        if self.failure:
            self.fail(message=f"Failed PHPStan")
        else:
            self.success(message=f"PHPStan Passed")

if __name__ == '__main__':
    pipe = PHPStan(schema=schema, logger=logger)
    pipe.run()
