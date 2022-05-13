ARG PHP_VERSION
FROM php:${PHP_VERSION}-cli-alpine

# Fetch the latest version of composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

RUN mkdir /composer
ENV COMPOSER_HOME /composer
ENV COMPOSER_ALLOW_SUPERUSER 1
ENV PATH /composer/vendor/bin:$PATH
ENV PHP_CONF_DIR=/usr/local/etc/php/conf.d

# Allow unlimited memory and add git for composer
RUN echo "memory_limit=-1" > $PHP_CONF_DIR/99_memory-limit.ini \
    && apk add --update --no-cache git wget jq openssh-client

# Copy Bitbucket Pipeline script and dependencies
COPY pipe /
RUN wget -P / https://bitbucket.org/bitbucketpipelines/bitbucket-pipes-toolkit-bash/raw/0.4.0/common.sh
RUN chmod a+x /*.sh

# Install phpstan globally
RUN composer global require phpstan/phpstan:1.6 --prefer-dist \
	&& composer clear-cache

VOLUME ["/app"]
WORKDIR /app

ENTRYPOINT ["/pipe.sh"]
