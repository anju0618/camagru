FROM php:8.3-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpng-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-configure gd --with-jpeg \
    && docker-php-ext-install gd \
    && mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && a2disconf other-vhosts-access-log

COPY docker/php.ini $PHP_INI_DIR/conf.d/99-camagru.ini
COPY docker/vhost.conf /etc/apache2/sites-available/000-default.conf
COPY docker/apache.conf /etc/apache2/conf-available/zz-camagru.conf
RUN a2enconf zz-camagru

COPY src/ /var/www/html/src/
COPY public/ /var/www/html/public/

RUN mkdir -p /var/www/data/images && chown -R www-data:www-data /var/www/data
