# The dev Nextcloud image = the pinned upstream image plus the PHP extensions
# our apps declare but upstream does not ship.
#
# ext-soap: integriq requires php-soap/ext-soap-engine, which needs ext-soap. It
# was absent from the container, so every SOAP code path fatalled at runtime --
# and nothing said so, because a missing PHP extension is not a boot error. The
# app enabled, served 200s, and only the SOAP paths were dead.
#
# This does NOT make the host-side `composer install --ignore-platform-reqs` in
# dev-up.sh unnecessary: that flag is there because the host CLI is a different
# PHP (8.3, no bcmath/intl/soap) from the one the code runs on. Two separate
# problems that happen to name the same extension.
#
# Keep the FROM tag in lockstep with the `image:` pin in docker-compose.yml. It
# is pinned for a reason: on an env reset a floating tag boots a drifted NC over
# the existing data volume -> needsDbUpgrade -> maintenance/503 + disabled apps.
FROM nextcloud:34.0.0-apache

RUN set -eux; \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update; \
    apt-get install -y --no-install-recommends libxml2-dev; \
    docker-php-ext-install -j"$(nproc)" soap; \
    apt-mark auto '.*' > /dev/null; \
    apt-mark manual $savedAptMark > /dev/null; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*; \
    php -m | grep -qx soap

# Exception traces without call arguments. Upstream loads no php.ini, so PHP's
# default (Off) applies and every logged exception carries its arguments. During
# `occ upgrade` Nextcloud forces debug logging, and core logs each "dirty table
# reads" with a full trace; with an app's register import on the stack that was
# ~1 MB per line. On 2026-10-11 one upgrade wrote an 83 GB nextcloud.log, filled
# the disk and took WSL down. php.ini-production ships this On; so do we.
RUN set -eux; \
    printf 'zend.exception_ignore_args = On\n' > /usr/local/etc/php/conf.d/zz-conduction-logs.ini; \
    php -r 'exit(ini_get("zend.exception_ignore_args") === "1" ? 0 : 1);'
