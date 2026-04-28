<h1 align="center">Welcome to Springfield 👋</h1>
<p>
  <a href="https://www.docker.com/" target="_blank">
    <img alt="Docker badge" src="https://img.shields.io/badge/docker-white?logo=docker">
  </a>
  <a href="#" target="_blank">
    <img alt="Django badge" src="https://img.shields.io/badge/django-green?logo=django">
  </a>
  <a href="https://www.docker.com/" target="_blank">
    <img alt="Python Badge" src="https://img.shields.io/badge/python-gray?logo=python&logoColor=yellow">
  </a>
  <a href="#" target="_blank">
    <img alt="Postgresql Badge" src="https://img.shields.io/badge/postgresql-beige?logo=postgresql">
  </a>
  <a href="#" target="_blank">
      <img alt="Redis Badge" src="https://img.shields.io/badge/redis-orange?logo=redis&logoColor=firebrick">
  </a>  
  <a href="#" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
  </a>
</p>

> A full featured server for the game: &#34;The Simpsons Tapped Out&#34;.

Get your old springfield back up and running again with this super customizable game server.
Among all its features it includes support for:

- multiple accounts,

- usernames and profile pictures,

- adding and visiting friend neighbors,

- editing money and donut currencies at your will,

- importing and exporting town files,

- tracking connected devices,

- a beautiful user dashboard for managing your accounts,

- versatile configuration to set up the server, with the option to run a single or multiple instances in parallel, all connected to the same database and storage (i.e. S3 bucket)

- and a lot of other cool things.

## Table of contents

- [📋 Requirements](#user-content--requirements)



## 📋 Requirements

The server can be set up in a plethora of ways according to your preferences, but it relies on some external services to work.

Some services are essential, whilst others are optional and can extend the server functionality.

The required services, which must be available in any configuration, are:

- a web server to act as a reverse proxy to the server and the static and DLC files, i.e., nginx

- and a database service.

The optional services, which extend the server functionality, are:

- Docker (**highly recommended**)

- Redis for caching (recommended),

- any other kind of storage service listed in [django-storages](https://django-storages.readthedocs.io/en/latest/), just in case you prefer to
  use another type of storage rather than local storage (i.e., S3 bucket),

- an email service to deliver emails with authentication codes. This is completely optional as you can also request permission to use [TSTO API](https://tsto.app/).

Other independent services are not covered in this guide, like fail2ban for rate limiting with nginx and whatnot.

## ⚡ Usage

The easiest and recommended way to get the server running is through the usage of Docker containers. If you do not want to use Docker, you will need to install each dependency listed
in the file `environment.yaml` with your favorite Python package manager: pip, conda, etc.

To make this guide easier to follow we will focus on Docker Compose. Let's start with the simplest possible configuration which just includes the server itself.
Create the following compose file somewhere in your file system. If necessary adjust the ports field.

**`compose.yaml`**
```yaml
services:

  springfield-server:
    image: docker.io/al1sant0s/springfield-server:v1.1
    ports:
      - "8000:8000"
    env_file:
      - .env

```

With this configuration the server will use a SQLite file as your database.
It only requires that you provide a web server, i.e., nginx, to act as a reverse proxy and serve the DLC and static files for the dashboard.

A simple nginx configuration for a local server, which listens on port 8080, may be specified like so:

```
	server {
		listen 8080;
		server_name localhost;
		client_max_body_size 5M;


		location /static/ {
			root		/data;
		}

		location /dlc/ {
			root		/data;
		}

		location / {
			proxy_pass	http://localhost:8000;
		}
	}

```

This configuration specifies that static files are served at `/data/static/` and DLC served at `/data/dlc/` in the file system. By default the server listens on port 8000, so we redirect the other requests to that port. Obviously this is just an example of configuration for the proxy server, you will need to make one according to your own circumstances. For example, if your server and proxy are running on different machines, you shouldn't use `localhost` for the `proxy_pass` entry.

Finally you need to create an `.env` file at the same directory where you have the `compose.yaml` file. With the following minimal settings:

**`.env`**
```env
# Server settings

DEBUG=false
DOMAIN=192.168.1.115
PORT=8080
PROTOCOL=http
SECRET_KEY='insert-your-secret-key-here'
STATIC_LOCATION=static/
STATIC_ROOT=/data/static/
TOWNS_ROOT=./towns/

```

A few things to consider.

* Pick a good **SECRET_KEY**.
* Remember to change the DOMAIN, PORT and STATIC_LOCATION with your own values to reflect your nginx settings.
* STATIC_ROOT is where the static files from the server will be served at. Change it if necessary.
* TOWNS_ROOT is where towns will be stored in. Change it if necessary.

> For a full detailed list of the environment variables, jump to the [environment variables](#user-content-environment-variables) section.

With nginx running and your compose and .env file ready, start your server running the following command
in a terminal at the same location as your compose.yaml file.

```sh
docker compose up -d
```

To check if your server is running, navigate to the address `http://localhost:8080` or whatever address your
nginx instance is running on. If you get a "Hello, World!" page, then your server _is running, but it is not ready for usage yet_.
There are still two remaining steps that need to be done.

First, you must run the migrations against your database. Run the following command for that.

```sh
docker compose exec springfield-server python manage.py migrate
```

Second, you must copy the server static files to the destination defined in `STATIC_ROOT`.

```sh
docker compose exec springfield-server python manage.py collectstatic
```

Additionaly, you should create an admin account for you. This isn't exactly required but it is recommended in case you need to manage the server directly
with Django admin dashboard. Run the following command and answer the questions it prompts to you.

```sh
docker compose exec springfield-server python manage.py createsuperuser
```

After that, check the admin dashboard at `http://localhost:8080/admin/`.
The normal user dashboard is located at `http://localhost:8080/dashboard/`.

Now your server is ready to be used. Congratulations!

## 💪 Advanced usage

The previous configurations work, but since the server is so flexible, you can do a lot more with it. To demonstrate this, in this advanced section, we will explore some optional
external services to use with the server. Mainly we will:

- pick another database engine, [PostgreSQL](https://hub.docker.com/_/postgres) in this case,

- set up [Redis](https://hub.docker.com/r/redis/redis-stack-server) for caching,

- configure the [TSTO API](https://tsto.app/) for delivering code emails,

- use a self-hosted [garage](https://garagehq.deuxfleurs.fr/) S3 bucket to illustrate how to use other types of storages.

Any external service can be installed in a variety of ways. To keep this guide the most simplest possible, we will stick with Docker Compose to
Install these additional services. Be aware that some of these services (like **garage** for example) require additional configuration that cannot be covered in this guide. You
should definitely check their documentation too.

With that said, let's expand our compose file like so.

**`compose.yaml`**
```yaml
services:

  springfield-server:
    image: docker.io/al1sant0s/springfield-server:v1.1
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      garage:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: postgres:latest
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  garage:
    image: dxflrs/garage:v2.2.0
    ports:
      - "3900:3900"
      - "3901:3901"
      - "3902:3902"
      - "3903:3903"
    volumes:
      - /etc/garage.toml:/etc/garage.toml:ro,z
      - /var/lib/garage/meta:/var/lib/garage/meta:z
      - /var/lib/garage/data:/var/lib/garage/data:z
    healthcheck:
      test: ["CMD", "/garage", "status"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 10s

  webui:
    image: khairul169/garage-webui:latest
    container_name: garage-webui
    volumes:
      - /etc/garage.toml:/etc/garage.toml:ro,z
    ports:
      - 3909:3909
    environment:
      API_BASE_URL: "http://garage:3903"
      S3_ENDPOINT_URL: "http://garage:3900"

  redis:
    image: redis:alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s


volumes:
  db-data:
  redis-data:

```

For these new services to run, we need to expand our .env file. Remember, you must update each environment variable with your own values.

**`.env`**
```env
# Server settings
AUTH_CODE_MINUTES=30
CACHE_DEFAULT_BACKEND=django_redis.cache.RedisCache
CACHE_DEFAULT_LOCATION=redis://redis:6379/1
CACHEOPS_REDIS_URL=$CACHE_DEFAULT_LOCATION
CACHE_SECONDS=3600
DEBUG=false
DOMAIN=192.168.1.115
PORT=8080
PROTOCOL=http
SECRET_KEY='insert-your-secret-key-here'
STATIC_LOCATION=static/
STATIC_ROOT=static/
TOWNS_ROOT=./


# TSTO API configuration
TSTO_API_KEY='insert-your-api-key-if-you-have-one'
TSTO_API_TEAM_NAME=MyTeamNameHere

# PostgreSQL configuration
POSTGRES_DB=springfield
POSTGRES_USER=springfield
POSTGRES_PASSWORD=springfield
DATABASE_DEFAULT=postgres://springfield:springfield@db:5432/springfield


# Garage configuration
AWS_ACCESS_KEY_ID=ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=garage
AWS_ENDPOINT_URL=http://garage:3900
STORAGE_DEFAULT=s3://?bucket_name=tsto-bucket
STORAGE_STATICFILES=s3+static://?bucket_name=static-bucket&url_protocol=http:&custom_domain=192.168.1.115:8080&location=static/

```

This .env file is way longer than the first one we saw before, so lets take it easy.

In the first part of the file we are defining some new defaults for the lifetime of the authentication codes (AUTH_CODE_MINUTES) and the cache duration (CACHE_SECONDS).

We are specifying that our cache backend is powered by Redis (CACHE_DEFAULT_BACKEND) and pointing to its location (CACHE_DEFAULT_LOCATION).
The variable CACHEOPS_REDIS_URL is also important here; it signals to our server that we want to enable an additional service for caching (actually it would be called an app in Django context), which depends on Redis. It's called [django-cacheops](https://pypi.org/project/django-cacheops/) and its main purpose is to support automatic or manual queryset caching.

Also we are now saying that our static files will be situated at `static/` (STATIC_ROOT). This directory is actually relative to
the S3 bucket we will use to store the static files.

Moving on to the second part, we have our TSTO API configuration. If you have obtained access to the TSTO API, then you can insert your settings here.
The TSTO API settings will be used for authentication when users request a code for login.

The third part is our database configuration for PostgreSQL. We are setting an user, their password and database; all with the same value 'springfield'.
The variable DATABASE_DEFAULT defines the server database backend.

The last part is our S3 service configuration. The first four variables are for establishing a connection with it.

STORAGE_DEFAULT defines the backend for the default storage as well as the name of our bucket (tsto-bucket in this case).

Analogously, there is STORAGE_STATICFILES which defines the storage backend for static files. We provide extra options to it: the custom_domain
and location, so the server may construct the appropriate static URL. These extra options are described in the specific page for S3 storage from [django-storages](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html). For the static files we are using another bucket rather than tsto-bucket called static-bucket. This bucket is different since its exposed as a [public website](https://garagehq.deuxfleurs.fr/documentation/cookbook/exposing-websites/). This is done so the user web browser can request the static files from the bucket. Otherwise, only the game server would have access to the static files. To reflect our new static configurations, we also updated our nginx settings.

```
	server {
		listen 8080;
		server_name localhost;
		client_max_body_size 5M;


		location /static/ {
			root					/data;
		}

		location /dlc/ {
			proxy_pass				http://localhost:3902;
			proxy_set_header		Host static-bucket.web.garage.localhost;
		}

		location / {
			proxy_pass				http://localhost:8000;
		}
	}
```

Now that everything is done, run the commands to start and set the server up.

```sh
docker compose up -d
docker compose exec springfield-server python manage.py migrate
docker compose exec springfield-server python manage.py collectstatic
docker compose exec springfield-server python manage.py createsuperuser
```

To confirm your server works correctly, run the [testing routines](#user-content--run-tests).

## 📧 Sending emails with a custom email service

If you are unable to use the TSTO API service to send emails for you, you can use another service for that. Remove the TSTO_API variables from your .env file and set two new variables:
SENDER_EMAIL and EMAIL_BACKEND.

SENDER_EMAIL is used to specify whose email address sends emails to users. EMAIL_BACKEND contains the configuration for the server to connect
with your email service. Check [django-service-urls documentation](https://pypi.org/project/django-service-urls/) for details on how to specify that.
Here is a fake example to illustrate, using a gmail account to send emails.

**.env**
```.env
SENDER_EMAIL=myaddress@gmail.com
EMAIL_BACKEND=smtp+tls://myaddress%40gmail.com:abcd%20efgh%20ijkl%20mnop@smtp.gmail.com:587
```

## 🗃️ Picking another database

Django offers support for multiple [database engines](https://docs.djangoproject.com/en/6.0/ref/settings/#std-setting-DATABASE-ENGINE). If you plan to run a server only for you and a few acquaintances, you may stick with the light SQLite database. However, if you plan to have multiple people playing in your server,
I highly recommend picking PostgreSQL as your database. If you decide to pick another database other than PostgreSQL or SQLite, you may need to install additional dependencies in your container so the server can talk with the specified database.

## ⬆️ Updating the server

It's just convenient to run the migrate command every time you update the server.

```sh
docker compose exec springfield-server python manage.py migrate
```

## 🩺 Run tests

Always run tests whenever you start your server.

```sh
docker compose exec springfield-server python manage.py test
```

## Environment variables

Here is a list of all available environment variables, which you can tweak in your .env file to adjust the server. Variables between square brackets [] are optional. Variables without square brackets [] are required, and if they are not specified, the server will not work.

Variables which specifies the backends for: cache, database, storages, etc; use _django-service-urls_ to specify multiple values with a single string.
Consult the [documentation](https://pypi.org/project/django-service-urls/) to understand how to specify such values.

- [AUTH_CODE_MINUTES]: authentication code lifetime in minutes. Defaults to 30 minutes.

- [CACHEOPS_REDIS_URL]: enables _django-cacheops_. Only set this variable in case you are using Redis as your caching backend. Usually it should be set with the same value as CACHE_DEFAULT_LOCATION.

- [CACHE_DEFAULT_BACKEND]: a string specified in the format described by _django-service-urls_ which determines the cache backend. Defaults to _django.core.cache.backends.locmem.LocMemCache_.

- [CACHE_DEFAULT_LOCATION]: a string specified in the format described by _django-service-urls_ which determines the cache service location. Defaults to _unique-snowflake_.

- [CACHE_SECONDS]: duration of cached values in seconds. Defaults to 3600 seconds.

- [DATABASE_DEFAULT]: a string specified in the format described by _django-service-urls_ which determines the database backend. Defaults to a SQLite file called database.db which is created in the working directory.

- DEBUG: boolean variable which determines if server runs in debug mode. This value must be set to false when the server is in a production environment.

- DOMAIN: reverse proxy domain or ip address which redirects to the server.

- [EMAIL_BACKEND]: a string specified in the format described by _django-service-urls_ which determines the email backend. Defaults to printing emails to console. Note that this is only used if SENDER_EMAIL is defined and TSTO_API variables are not.

- PORT: reverse proxy port.

- PROTOCOL: reverse proxy protocol.

- SECRET_KEY: the server secret key.

- [SENDER_EMAIL]: email address where emails are dispatched from.

- [STATIC_LOCATION]: static endpoint. Defaults to `static/`.

- [STATIC_ROOT]: directory or path where static files will be stored. Defaults to `/data/static/`.

- [STORAGE_DEFAULT]: a string specified in the format described by _django-service-urls_ which determines the default storage backend. Defaults to _django.core.files.storage.filesystem.FileSystemStorage_.

- [STORAGE_STATICFILES]: a string specified in the format described by _django-service-urls_ which determines the default storage backend. Defaults to _django.contrib.staticfiles.storage.StaticFilesStorage_.
  
- [TOWNS_ROOT]: directory or path where town files will be stored. Defaults to `towns/`.

- [TSTO_API_KEY]: self-explanatory. No default value.

- [TSTO_API_TEAM_NAME]: self-explanatory. No default value.

## Author

👤 **Alisson Santos**

* Github: [@al1sant0s](https://github.com/al1sant0s)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/al1sant0s/springfield/issues). 

## Show your support

Give a ⭐️ if this project helped you!

***
_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
