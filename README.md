# JakDojadeClone

This is a project that aims to reproduce the jakdojade.pl website with AI support. Ultimately, we want to serve large cities, e.g. Tokyo

## Installation

As first step You have to install [docker compose](https://docs.docker.com/compose/install/).

Create <b>.env</b> file, with same structure as in example:
```
POSTGRES_DB=example_db_name
POSTGRES_USER=user
POSTGRES_PASSWORD=example_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```


After that run this command:

```
docker-compose up --build
```

This will build whole project, including postgres database.


## Contributing


This is our final project for an engineering thesis. 

Therefore, we do not accept pull requests