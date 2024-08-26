ARG PHP_VERSION
FROM php:${PHP_VERSION}-cli-alpine

# Fetch the latest version of composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

RUN mkdir /composer
ENV COMPOSER_HOME /composer
ENV COMPOSER_ALLOW_SUPERUSER 1
ENV PATH /composer/vendor/bin:$PATH
ENV PHP_CONF_DIR=/usr/local/etc/php/conf.d

# Allow unlimited memory and install git for composer and python dependencies
RUN echo "memory_limit=-1" > $PHP_CONF_DIR/99_memory-limit.ini \
    && apk add --update --no-cache git wget jq openssh-client python3 python3-dev gcc libffi-dev musl-dev \
    && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# Install phpstan globally
RUN composer global require phpstan/phpstan:1.11 --prefer-dist \
	&& composer clear-cache

# Allow git access to mounted build directories
RUN git config --global --add safe.directory /build
RUN mkdir -p /opt/atlassian/pipelines/agent/build
RUN git config --global --add safe.directory /opt/atlassian/pipelines/agent/build

ENV PYTHONUNBUFFERED=1

COPY pipe pipe.yml /
RUN chmod a+x /pipe.py
COPY requirements.txt /
RUN python3 -m pip install --no-cache-dir -r /requirements.txt

ENTRYPOINT ["/pipe.py"]
