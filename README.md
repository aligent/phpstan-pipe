# Aligent PHPStan Pipe

This pipe is used to execute PHPStan over changed files on a PR

## YAML Definition

Add the following your `bitbucket-pipelines.yml` file:

```yaml
      - step:
          name: "PHPStan check"
          script:
            - pipe: docker://ghcr.io/aligent/phpstan-pipe:8.4
              variables:
                SKIP_DEPENDENCIES: "false"
                LEVEL: "0"
                AUTOLOADER: "vendor/autoload.php"
                IGNORE_PLATFORM_DEPENDENCIES: "false"
```

We have docker images built for the following PHP Versions: 8.1, 8.2, 8.3, 8.4
## Variables

| Variable                     | Usage                                                                                                                                                       |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| SKIP_DEPENDENCIES            | (Optional) Skip installing project composer dependencies. Default: `false`.                                                                                 |
| LEVEL                        | (Optional) Which level to execute phpstan at. Default: `0`                                                                                                  |
| AUTOLOADER                   | (Optional) Which PHP Autoloader to use. Default: `vendor/autoload.php`                                                                                      |
| IGNORE_PLATFORM_DEPENDENCIES | (Optional) Whether to install platform dependencies or not. Default: `false`                                                                                |
| CONFIG_FILE                  | (Optional) Config file to use.                                                                                                                |
| SCAN_DIRECTORY               | (Optional) Which directory to scan. This will override the default behavior of comparing only the changed files, and will instead scan this entire directory. |
| EXCLUDE_EXPRESSION           | (Optional) A grep [regular expression](https://www.gnu.org/software/grep/manual/html_node/Basic-vs-Extended.html) to exclude files from standards testing   |

## Development

The following command can be used to invoke the pipe locally:
```
docker run -it --env="SKIP_DEPENDENCIES=true" --env="AUTOLOADER=vendor/autoload.php" --env="LEVEL=9" --env="BITBUCKET_PR_DESTINATION_BRANCH=<DESTINATION_BRANCH" --env="DISABLE_REPORT=true" -v $PWD:/build --workdir=/build ghcr.io/aligent/phpstan-pipe:<PHP-Version>
```

## CI/CD

Docker images are built and pushed to GitHub Container Registry (`ghcr.io/aligent/phpstan-pipe`) via GitHub Actions
(`.github/workflows/docker-build.yml`, using the shared `aligent/workflows` Docker build workflow). The workflow:

- Builds an image for every configured PHP version, tagged `<PHP_VERSION>`
- Pushes images on commits to `main`; commits to `staging` push tags suffixed with `-experimental`
- Builds without pushing on pull requests
- Can be triggered manually
