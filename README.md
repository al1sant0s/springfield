<h1 align="center">Welcome to springfield ](url)</h1>
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

- versatile configuration to set up the server, with the option to run a single or multiple instances in parallel, all connected to the same database and storage (i.e. s3 bucket)

- and a lot of other cool things.

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

With this configuration the server will use a sqlite file as your database.
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

This configuration specifies that static files are served at `/data/static/` and DLC served at `data/dlc/` in the file system. By default the server listens on port 8000, so we redirect the other requests to that port. Obviously this is just an example of configuration for the proxy server, you will need to make one according to your own circumstances. For example, if your server and proxy are running on different machines, you shouldn't use `localhost` for the proxy_pass entry.

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

* Remember to change the DOMAIN with your server address.
* Pick a good **SECRET_KEY**. Change the PORT and STATIC_LOCATION to reflect your nginx settings.
* STATIC_ROOT is where the static files from the server will be served at.
* TOWNS_ROOT is where towns will be stored in.

> For a full detailed list of the environment variables, jump to section #ref.

With nginx running and your compose and .env file ready, start your server running the following command
in a terminal at the same location as your compose.yaml file

```sh
docker compose up -d
```

To check if your server is running, navigate to the address `http://localhost:8080` or whatever address your
nginx instance is running on. If you get a "Hello, World!" page, then your server _is running, but it is not ready yet for usage_.
There are still two remaining steps.

First, you must run the migrations against your database. Run the following command for that

```sh
docker compose exec springfield-server python manage.py migrate
```

Second, you should create an admin account for you. This isn't exactly required but it is recommended in case you need to manage the server directly
with Django admin dashboard. Run the following command and follow the instructions it presents to you

```sh
docker compose exec springfield-server python manage.py createsuperuser
```

Check the admin dashboard at `http://localhost:8080/admin/`.

Now your server is ready to be used. Congratulations!

## Advanced usage

The previous configurations work, but since the server is so flexible, you can do a lot more with it. To demonstrate that, in this advanced section, we will explore some optional
external services to use with the server. Mainly we will:

- pick another database engine, PostgreSQL in this case,

- set up Redis for caching,

- configure the TSTO API for delivering code emails,

- use a self-hosted garage S3 bucket to illustrate how to use other types of storages.

Any external service can be installed in a variety of ways. To keep this guide the most simplest possible, we will stick with Docker Compose to
install these additional services.

### Picking a database

Django offer support for multiple [database engines](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-DATABASE-ENGINE). If you plan to run a server only for you and a few acquaintances you may stick with the light sqlite database. However, if you plan to have multiple people playing in your server, I highly
recommend picking PostgreSQL as your database. If you device to pick another database other than PostgreSQL or sqlite you may need to install additional depenciens in your container so the server can talk with the specified database.

### Set up all the se

To use PostgreSQL, we will expand our compose file like so

## Run tests

```sh
docker compose exec springfield-server python manage.py migrate
```

## Author

👤 **Alisson Santos**

* Github: [@al1sant0s](https://github.com/al1sant0s)

## 🤝 Contributing

Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/al1sant0s/springfield/issues). 

## Show your support

Give a ⭐️ if this project helped you!

***
_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_
