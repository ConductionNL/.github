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
