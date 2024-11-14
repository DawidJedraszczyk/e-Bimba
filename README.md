# JakDojadeClone

This is a project that aims to reproduce the [jakdojade](https://jakdojade.pl) website with AI support. Ultimately, we want to serve large cities, e.g. Tokyo

## Installation

### Preparing data

To prepare data for route planning go into the `pipeline` directory and run

```bash
./prepare.py Poznań
```

where `Poznań` can be replaced with any city defined in `pipeline/cities.json`.

### Running the app

As first step You have to install [docker compose](https://docs.docker.com/compose/install/).

Create <b>.env</b> file, with same structure as in example:
```
POSTGRES_DB=example_db_name
POSTGRES_USER=user
POSTGRES_PASSWORD=example_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
```


After that run this command:

```
docker-compose up --build
```

This will build whole project, including postgres database.

## Benchmarks

To run the benchmark go to benchmark folder and run run.py file from there. The results of the benchmark will be  saved in the benchmark/benchamrk_results with the corresponding date and time. To perform analysis or comparison of the results open one the corresponding jupiter notebooks in the folder and follow instructions. The required packages to run the notebooks are in the data_analysis_requirements.txt file 

## Contributing


This is our final project for an engineering thesis. 

Therefore, we do not accept pull requests
