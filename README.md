# Heads up

> If you have stumbled upon this project and you're just looking for an easy way to play the game again, without having to host a server by yourself, you can do so by joinining this [public server](https://discord.com/invite/rzP2qGjGww).
> Otherwise, if you would rather prefer to host your own server, continue reading the guide.

<h1 align="center">Welcome to Springfield 👋</h1>
<p>
  <a href="https://www.docker.com/" target="_blank">
    <img alt="Docker badge" src="https://img.shields.io/badge/docker-white?logo=docker">
  </a>
  <a href="https://www.djangoproject.com/" target="_blank">
    <img alt="Django badge" src="https://img.shields.io/badge/django-green?logo=django">
  </a>
  <a href="https://www.python.org/" target="_blank">
    <img alt="Python Badge" src="https://img.shields.io/badge/python-gray?logo=python&logoColor=yellow">
  </a>
  <a href="https://www.postgresql.org/" target="_blank">
    <img alt="Postgresql Badge" src="https://img.shields.io/badge/postgresql-beige?logo=postgresql">
  </a>
  <a href="https://redis.io/" target="_blank">
      <img alt="Redis Badge" src="https://img.shields.io/badge/redis-orange?logo=redis&logoColor=firebrick">
  </a>  
  <a href="#" target="_blank">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
  </a>
  <a href="#" target="_blank">
    <img alt="License: MIT" src="https://github.com/al1sant0s/springfield/actions/workflows/docker-publish.yml/badge.svg" />
  </a>
</p>

> A full-featured server for the game: &#34;The Simpsons: Tapped Out&#34;.

Get your old Springfield back up and running again with this super customizable game server.

Among all its features, it includes support for:

- multiple accounts,

- usernames and profile pictures,

- adding and visiting friend neighbors,

- editing money and donuts currencies at your will,

- importing and exporting town files,

- tracking connected devices,

- a beautiful user dashboard for managing your accounts,

- versatile configuration to set up the server, with the option to run a single or multiple instances in parallel, all connected to the same database and storage (e.g., S3 bucket)

- and a lot of other cool things.

## Table of contents

- [📋 Requirements](#user-content--requirements)
- [⚡ Usage](#user-content--usage)
- [💪 Advanced usage](#user-content--advanced-usage)
- [📧 Sending emails with a custom email service](#user-content--sending-emails-with-a-custom-email-service)
- [🗃️ Picking another database](#user-content-️-picking-another-database)
- [⬆️ Updating the server](#user-content-️-updating-the-server)
- [🩺 Run tests](#user-content--run-tests)
- [⚙️ Environment variables](#user-content-️-environment-variables)


## 📋 Requirements

The server can be set up in a plethora of ways according to your preferences, but it relies on some external services to work.

Some services are essential, while others are optional and can extend the server functionality.

The required services, which must be available in any configuration, are:

- a web server to act as a reverse proxy to the game server and to serve the static and DLC files, e.g., nginx

- and a database service.

The optional services, which extend the server functionality, are:

- Docker (**highly recommended**)

- Redis for caching (recommended),

- any other kind of storage service listed in [django-storages](https://django-storages.readthedocs.io/en/latest/), just in case you prefer to
  use another type of storage rather than local storage (e.g., S3 bucket),

- an email service to deliver emails with authentication codes. This is completely optional as you can also request permission to use [TSTO API](https://tsto.app/).

Other independent services are not covered in this guide, like Fail2ban for rate limiting with nginx and whatnot.

## ⚡ Usage

The easiest and recommended way to get the server running is through the usage of Docker containers. If you do not want to use Docker, you will need to install each dependency listed
in the file `environment.yaml` with your favorite Python package manager: pip, conda, etc.

To make this guide easier to follow we will focus on Docker Compose. Let's start with the simplest possible configuration which just includes the server itself.
Create the following compose file somewhere in your file system. If necessary adjust the ports field.

**`compose.yaml`**
```yaml
services:

  springfield-server:
    image: ghcr.io/al1sant0s/springfield:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - /data/media/:/app/media/:z
      - /data/static/:/app/static/:z
      - /data/database.db:/app/database.db:z
```

With this configuration the server will use a SQLite file as your database.
It only requires that you provide a web server, e.g., nginx, to act as a reverse proxy and serve the DLC, media files (avatars and towns), and static files for the dashboard.

A simple nginx configuration for a local server, which listens on port 8080, may be specified like so:

```nginx
server {
	listen 8080;
	server_name localhost;
	client_max_body_size 10M;

	location /static/ {
		alias	/data/static/;
	}

	# Internal location used by X-Accel-Redirect to stream local media files
	# (avatars and towns) directly from disk without buffering through Python workers.
	location /media/ {
		internal;
		alias	/data/media/;
	}

	location /dlc/ {
		alias	/data/dlc/;
	}

	location / {
		proxy_pass		http://localhost:8000;
		proxy_set_header	Host $http_host;
		proxy_set_header	X-Real-IP $remote_addr;
		proxy_set_header	X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header	X-Forwarded-Proto $scheme;
	}
}
```

This configuration specifies that static files are served from `/data/static/`, DLC from `/data/dlc/`, and all game requests are forwarded to the Django server on port 8000. The `/media/` location is marked `internal` so it is only reachable via `X-Accel-Redirect` responses from Django — Nginx streams avatars and towns directly from disk without buffering them through Python workers.

Finally you need to create an `.env` file at the same directory where you have the `compose.yaml` file, with the following minimal settings:

**`.env`**
```env
# Server settings
DEBUG=false
SECRET_KEY='insert-your-secret-key-here'
SERVER_BASE_URL=http://192.168.1.115:8080
ALLOWED_HOSTS=192.168.1.115,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.1.115:8080,http://localhost:8080,http://127.0.0.1:8080
STATIC_URL=static/
STATIC_ROOT=/app/static/
MEDIA_URL=media/
MEDIA_ROOT=/app/media/
```

A few things to consider:

* Pick a good **SECRET_KEY**.
* `SERVER_BASE_URL` and `ALLOWED_HOSTS`: Reflect your nginx host and port.
* `CSRF_TRUSTED_ORIGINS`: Include the full scheme, host, and port (e.g. `http://192.168.1.115:8080,http://localhost:8080`) for every origin you use to access the dashboard, to prevent CSRF 403 errors on form submissions.
* `STATIC_ROOT` and `MEDIA_ROOT`: Internal container paths where static files and media (avatars, towns) reside. These correspond to the bind mounts defined in `compose.yaml`.

> For a full detailed list of the environment variables, jump to the [environment variables](user-content-️-environment-variables) section.

Before starting the containers, ensure the host persistent directories and the SQLite database file exist beforehand:

```sh
sudo mkdir -p /data/media /data/static /data/dlc
sudo touch /data/database.db
```

> **Note**: Creating `/data/database.db` before running Docker Compose is important. If a single-file mount target does not exist when the container launches, Docker will automatically create it as a directory.

With nginx running, host directories prepared, and your `compose.yaml` and `.env` file ready, start your server:

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

Second, you must collect the static files into `STATIC_ROOT`. Since `STATIC_ROOT` lives within the container and we need its contents to be available to the host machine (where nginx is running), we provided a bind mount in the `compose.yaml` file that links `STATIC_ROOT` with the static files location from nginx.

```sh
docker compose exec springfield-server python manage.py collectstatic
```

Additionally, you should create an admin account for you. This isn't exactly required but it is recommended in case you need to manage the server directly
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

With that said, let's update our compose file like so.

**`compose.yaml`**
```yaml
services:

  springfield-server:
    image: ghcr.io/al1sant0s/springfield:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    command: [
        "gunicorn",
        "springfield.wsgi",
        "--capture-output",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--bind", "0.0.0.0:8000",
        "--worker-class", "gthread",
        "--workers", "6",
        "--threads", "8",
        "--preload"
    ]
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
DEBUG=false
SECRET_KEY='insert-your-secret-key-here'
SERVER_BASE_URL=http://192.168.1.115:8080
ALLOWED_HOSTS=192.168.1.115,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.1.115:8080,http://localhost:8080,http://127.0.0.1:8080
AUTH_CODE_MINUTES=30
LOGIN_ATTEMPTS=10
LOGIN_FAIL_COOLOFF_TIME=10

# Cache configuration
CACHE_URL=redis://redis:6379/0?timeout=3600
CACHEOPS_REDIS=redis://redis:6379/1

# Static and media files
STATIC_URL=static/
STATIC_ROOT=static/
MEDIA_URL=media/
MEDIA_ROOT=media/

# TSTO API configuration
TSTO_API_KEY='insert-your-api-key-if-you-have-one'
TSTO_API_TEAM_NAME=MyTeamNameHere

# PostgreSQL configuration
POSTGRES_DB=springfield
POSTGRES_USER=springfield
POSTGRES_PASSWORD=springfield
DATABASE_URL=postgres://springfield:springfield@db:5432/springfield

# Garage / S3 configuration
AWS_ACCESS_KEY_ID=ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=garage
AWS_ENDPOINT_URL=http://192.168.1.115:3900
STORAGE_DEFAULT=s3://?bucket_name=tsto-bucket
STORAGE_STATICFILES=s3+static://?bucket_name=static-bucket&url_protocol=http:&custom_domain=192.168.1.115:8080&location=static/
```

This .env file configures the advanced services:

In the first part we define the server base URL, allowed hosts, lifetime of authentication codes (`AUTH_CODE_MINUTES`), the maximum failed login attempts (`LOGIN_ATTEMPTS`), and the cooldown lockout duration in minutes (`LOGIN_FAIL_COOLOFF_TIME`).

For caching, `CACHE_URL` configures the Redis default cache backend (with a 1-hour timeout query parameter). `CACHEOPS_REDIS` enables [django-cacheops](https://pypi.org/project/django-cacheops/) on a dedicated Redis database index for automatic ORM queryset caching.

Moving on to the TSTO API configuration: if you have obtained access to the TSTO API, insert your credentials here for authentication code delivery.

In the database section, `DATABASE_URL` provides the PostgreSQL connection string matching the credentials defined for the Postgres container.

The last part configures S3-compatible storage (such as Garage):
* `AWS_ENDPOINT_URL` specifies the S3 endpoint URL. This value is also used by Django to generate presigned URLs for avatars and towns. Therefore, `AWS_ENDPOINT_URL` should point to your host's externally reachable IP/domain and port (e.g. `http://192.168.1.115:3900`) — this is the host that gets embedded in the SigV4 signature, and **Nginx must forward requests to S3 using this same host** so that the signature validates.
* `STORAGE_DEFAULT` defines the backend for default storage (towns and avatars) along with the bucket name (`tsto-bucket`).
* `STORAGE_STATICFILES` defines S3 storage for static files (`static-bucket`). Extra options like `custom_domain` and `location` can be passed as URL query parameters. For static files, the bucket is typically exposed as a [public website](https://garagehq.deuxfleurs.fr/documentation/cookbook/exposing-websites/) so user web browsers can fetch static assets directly.

To reflect our new storage configuration, we update our nginx settings:

```nginx
server {
	listen 8080;
	server_name localhost;
	client_max_body_size 10M;

	location /static/ {
		proxy_pass		http://localhost:3902;
		proxy_set_header	Host static-bucket.web.garage.localhost;
	}

	# Internal proxy to stream S3/Garage media files (avatars and towns) via X-Accel-Redirect.
	# Django strips the domain from the presigned URL and sets X-Accel-Redirect to the signed
	# path+query so Nginx can proxy it here. The Host header MUST match the host embedded in
	# AWS_ENDPOINT_URL (e.g. 192.168.1.115:3900) so that Garage validates the SigV4 signature.
	location /tsto-bucket/ {
		internal;
		proxy_pass		http://localhost:3900;
		proxy_set_header	Host 192.168.1.115:3900;
	}

	location /dlc/ {
		alias			/data/dlc/;
	}

	location / {
		proxy_pass		http://localhost:8000;
		proxy_set_header	Host $http_host;
		proxy_set_header	X-Real-IP $remote_addr;
		proxy_set_header	X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header	X-Forwarded-Proto $scheme;
	}
}
```

With this setup Django authenticates access, generates a signed URL for the requested file, strips the domain, and returns it as an `X-Accel-Redirect` header. Nginx intercepts the redirect and streams the file to the game client directly from S3/Garage — Python workers are never involved in the data transfer itself. Replace `192.168.1.115:3900` and `localhost:3900` with your actual `AWS_ENDPOINT_URL` host and local S3 port respectively. If you use a different bucket name in `STORAGE_DEFAULT`, update the location path accordingly.


Now that everything is configured, run the commands to start and initialize the server:

```sh
docker compose up -d
docker compose exec springfield-server python manage.py migrate
docker compose exec springfield-server python manage.py collectstatic
docker compose exec springfield-server python manage.py createsuperuser
```

To confirm your server works correctly, run the [testing routines](#user-content--run-tests).

## 📧 Sending emails with a custom email service

If you are unable to use the TSTO API service for sending emails for you, you can use another service for that. Remove the TSTO_API variables from your .env file and set two new variables:
SENDER_EMAIL and EMAIL_BACKEND.

SENDER_EMAIL is used to specify whose email address sends emails to users. EMAIL_BACKEND contains the configuration for the server to connect with your email service. Check django-service-urls [documentation](https://pypi.org/project/django-service-urls/) for details on how to specify that.

Here is an example to illustrate, using a "fake" Gmail account to send emails. Note that at the moment of writing this, in order to send emails with Gmail, you need to set up an app password.
This may change in the foreseeable future. Check the details as a precaution.

**.env**
```.env
SENDER_EMAIL=myaddress@gmail.com
EMAIL_BACKEND=smtp+tls://myaddress%40gmail.com:abcd%20efgh%20ijkl%20mnop@smtp.gmail.com:587
```
The default email message comes from a template file located at `/proxy/templates/templated_email/auth_code.email`. If you wish to replace the email message with one of your own, you can bind your email template file with the server's. To do this, include the following line in the volumes section from the springfield-server service in your compose file.

**.compose.yaml**
```.yaml
volumes:
	- /path/to/auth_code.email:/app/proxy/templates/templated_email/auth_code.email:z
```

The server uses [django-templated-email](https://pypi.org/project/django-templated-email/) for sending emails. It supports both plain text and HTML for structuring the email message. The template receives a context that includes three variables: username, code and auth_code_minutes, which you may use in your custom email message.

Be aware that you can also use both the **TSTO API** service and an email custom service as a fallback in case the API is not available. Just set up both of them in your `.env` file. The server will prioritize the **TSTO API** for authentication and use only the custom email service when the API becomes unavailable.

## 🗃️ Picking another database

Django offers support for multiple [database engines](https://docs.djangoproject.com/en/6.0/ref/settings/#std-setting-DATABASE-ENGINE). If you plan to run a server only for you and a few acquaintances, you may stick with the light SQLite database. However, if you plan to have multiple people playing in your server,
I highly recommend picking PostgreSQL as your database. If you decide to pick another database other than PostgreSQL or SQLite, you may need to install additional dependencies in your container so the server can talk with the specified database.

## ⬆️ Updating the server

In order to update the server, you must run the following sequence of commands:

```sh
docker compose down
docker compose up -d --pull always
docker compose exec springfield-server python manage.py migrate
```

This will shut down the server instance, recreate the containers with the latest images available, and apply any new database migrations.

> If you are running multiple servers connected to the same database, run `docker compose down` on all of them first. Then perform the update and migrations on one server, and finally restart the remaining servers with `docker compose up -d --pull always`.

## 🩺 Run tests

Always run tests whenever you start your server.

```sh
docker compose exec springfield-server python manage.py test
```

## ⚙️ Environment variables

Here is a list of all available environment variables, which you can tweak in your `.env` file to configure the server. Variables in square brackets `[]` are optional. Variables without square brackets are required.

Service URLs for caching, storage, and email use _django-service-urls_ / _django-environ_ formatting. Consult the [django-service-urls](https://pypi.org/project/django-service-urls/) documentation for syntax details.

- `[ALLOWED_HOSTS]`: Comma-separated list of host/domain names this Django site can serve. Default: `localhost,127.0.0.1,::1`.

- `[AUTH_CODE_MINUTES]`: Authentication code lifetime in minutes. Default: `30` minutes.

- `[AWS_ACCESS_KEY_ID]`: Access key ID for S3-compatible storage backends.

- `[AWS_DEFAULT_REGION]`: AWS/S3 region name for S3 storage (e.g. `garage` or `us-east-1`).

- `[AWS_ENDPOINT_URL]`: Endpoint URL for S3-compatible storage (e.g. `http://192.168.1.115:3900`). Must be reachable from both the container and client browsers/devices when generating presigned media URLs (such as avatars).

- `[AWS_SECRET_ACCESS_KEY]`: Secret access key for S3-compatible storage backends.

- `[CACHEOPS_REDIS]`: Redis URL for query caching via *django-cacheops* (e.g., `redis://redis:6379/1`). When omitted, query caching is disabled.

- `[CACHE_URL]`: Cache backend URL formatted according to *django-service-urls* (e.g. `redis://redis:6379/0?timeout=3600`). Default: `memory://`.

- `[CSRF_TRUSTED_ORIGINS]`: Comma-separated list of trusted origins for unsafe HTTP requests (e.g., `http://192.168.1.115:8080,http://localhost:8080`). Must include scheme and port. Default: `http://localhost:8000,http://127.0.0.1:8000`.

- `[DATABASE_URL]`: Database connection URL (e.g., `postgres://springfield:springfield@db:5432/springfield` or `sqlite:///database.db`). Default: SQLite database at `database.db`.

- `DEBUG`: Boolean variable determining if the server runs in debug mode. Must be set to `false` in production.

- `[EMAIL_BACKEND]`: Service URL determining the email backend (e.g. `smtp+tls://user:pass@smtp.example.com:587`). Default: `console://`. Only used if `TSTO_API_KEY` is not provided.

- `[INTERNAL_IPS]`: Comma-separated list of internal IP addresses for Django debug toolbar. Default: `127.0.0.1,::1`.

- `[LOGIN_ATTEMPTS]`: Maximum number of failed login attempts permitted before temporarily blocking user access (via *django-axes*). Default: `0` (disabled).

- `[LOGIN_FAIL_COOLOFF_TIME]`: Duration in minutes that an IP remains locked out after exceeding `LOGIN_ATTEMPTS`. Default: `30` minutes.

- `[MEDIA_ROOT]`: Internal container filesystem directory where uploaded media files (towns, avatars) are saved. Default: `/app/media`.

- `[MEDIA_URL]`: URL prefix for accessing media files. Default: `media/`.

- `SECRET_KEY`: Secret key used for cryptographic signing and session security. Must be kept secret.

- `[SENDER_EMAIL]`: Email address used as the sender when dispatching verification codes.

- `SERVER_BASE_URL`: Public base URL of the server (e.g. `http://192.168.1.115:8080` or `https://tsto.example.com`). Default: `http://localhost:8000`.

- `[STATIC_ROOT]`: Internal container filesystem directory where static files are collected. Default: `/app/staticfiles`.

- `[STATIC_URL]`: URL prefix for static files. Default: `static/`.

- `[STORAGE_DEFAULT]`: Storage service URL for default file storage (towns and avatars). Supports `fs://?allow_overwrite=true` or S3 buckets via `s3://?bucket_name=my-bucket`. Default: `fs://?allow_overwrite=true`.

- `[STORAGE_STATICFILES]`: Storage service URL for static files. Default: `static://`.

- `[TIME_ZONE]`: Time zone string for the Django application. Default: `UTC`.

- `[TSTO_API_KEY]`: TSTO API authentication key. Optional; overrides custom email delivery when provided.

- `[TSTO_API_TEAM_NAME]`: TSTO API team name. Optional.

## Author

👤 **Alisson Santos**

* Github: [@al1sant0s](https://github.com/al1sant0s)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/al1sant0s/springfield/issues). 

## Show your support

Give a ⭐️ if this project helped you!

***
_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
