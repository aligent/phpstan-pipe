# Aligent PHPStan Pipe

This pipe is used to execute PHPStan over changed files on a PR

## YAML Definition

Add the following your `bitbucket-pipelines.yml` file:

```yaml
      - step:
          name: "PHPStan check"
          script:
            - pipe: docker://aligent/phpstan-pipe:latest
              variables:
                SKIP_DEPENDENCIES: "false"
                LEVEL: "0"
                AUTOLOADER: "vendor/autoload.php"
                IGNORE_PLATFORM_DEPENDENCIES: "false"
```

We have docker images built for the following PHP Versions: 7.3, 7.4, 8.0, 8.1
## Variables

| Variable              | Usage                                                       |
| -----------------------------| ----------------------------------------------------------- |
| DEBUG                        | (Optional) Turn on extra debug information. Default: `false`. |
| SKIP_DEPENDENCIES            | (Optional) Skip installing project composer dependencies. Default: `false`. |
| LEVEL                        | (Optional) Which level to execute phpstan at. Default: `0`|
| AUTOLOADER                   | (Optional) Which PHP Autoloader to use. Default: `vendor/autoload.php`|
| IGNORE_PLATFORM_DEPENDENCIES | (Optional) Whether to install platform dependencies or not. Default: `false`|
| SCAN_DIRECTORY               | (Optional) Which directory to scan. This will override the default behavior of comparing only the changed files, and will instead scan this entire directory. |
| EXCLUDE_EXPRESSION           | (Optional) A grep [regular expression](https://www.gnu.org/software/grep/manual/html_node/Basic-vs-Extended.html) to exclude files from standards testing|

## Development

The following command can be used to invoke the pipe locally:
```
docker run -v $PWD:/app aligent/phpstan-pipe:<PHP-Version>
```

Commits published to the `main` branch  will trigger an automated build for each of the configured PHP version.
Commits to `staging` will do the same but image tags will be suffixed with `-experimiental`.
