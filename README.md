# JakDojadeClone

This is a project that aims to reproduce the [jakdojade](https://jakdojade.pl) website with AI support. Ultimately, we want to serve large cities, e.g. Madrid

### First steps

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

## Preparing GTFS for cities

Step 1 -> create venv
Step 2 -> move into pipeline directory
Step 3 -> install requirements from pipeline directory

# Option 1 - prepare for specific city

Final step -> 
```
python prepare.py CityName
```
Where CityName is a name of city from cities.json, ex. Poznań, Roma, Madrid

This command is recommended.

# Option 2 - prepare all cities
Final step ->
```
sudo ./preapre_all_cities.sh
```
This command takes long time, even half of an hour.


### Application

Command to run application:
```
docker-compose up --build
```

This will build whole project, including postgres database.
Application is ready on 0.0.0.0:8000

If no route is found, change date into future (+- 2/3 days into future). 

## Benchmarks

To run the benchmark go to benchmark folder and run run.py file from there. The results of the benchmark will be  saved in the `benchmark/benchamrk_results` with the corresponding date and time. To perform analysis or comparison of the results open one the corresponding jupiter notebooks in the folder and follow instructions. The required packages to run the notebooks are in the `data_analysis_requirements.txt` file 

## Contributing


This is our final project for an engineering thesis. 

Therefore, we do not accept pull requests
