# Aligent PHPStan Pipe

This pipe is used to execute PHPStan over changed files on a PR

## YAML Definition

Add the following your `bitbucket-pipelines.yml` file:

```yaml
      - step:
          name: "PHPStan check"
          script:
            - pipe: aligent/phpstan-pipe:latest
              variables:
                SKIP_DEPENDENCIES: "false"
                MAGENTO_USER: "${MAGENTO_USER}"
                MAGENTO_PASS: "${MAGENTO_PASS}"
                LEVEL: "0"
                AUTOLOADER: "vendor/autoload.php"
                IGNORE_PLATFORM_DEPENDENCIES: "false"
```
## Variables

| Variable              | Usage                                                       |
| -----------------------------| ----------------------------------------------------------- |
| DEBUG                        | (Optional) Turn on extra debug information. Default: `false`. |
| SKIP_DEPENDENCIES            | (Optional) Skip installing project composer dependencies. Default: `false`. |
| MAGENTO_USER                 | (Optional) Injects repo.magento.com user into auth.json |
| MAGENTO_PASS                 | (Optional) Injects repo.magento.com password into auth.json|
| LEVEL                        | (Optional) Which level to execute phpstan at. Default: `0`|
| AUTOLOADER                   | (Optional) Which PHP Autoloader to use. Default: `vendor/autoload.php`|
| IGNORE_PLATFORM_DEPENDENCIES | (Optional) Whether to install platform dependencies or not. Default: `false`|
| EXCLUDE_EXPRESSION           | (Optional) A grep [regular expression](https://www.gnu.org/software/grep/manual/html_node/Basic-vs-Extended.html) to exclude files from standards testing|

## Development

The following command can be used to invoke the pipe locally:
```
docker run -v $PWD:/app aligent/phpstan-pipe:latest
```

Commits published to the `main` branch  will trigger an automated build for the each of the configured PHP version.
Commits to `staging` will do the same but image tags will be suffixed with `-experimiental`.