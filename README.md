# A backend for Perceval to retrieve Sonarqube's data
A grimoirelab-perceval backend for the API of a Sonarqube service [1] that extracts information about the projects hosted in such service.
It is basic backend of grimoirelab-perceval [2], the data collector of CHAOSS GrimoireLab Tool.

## Deployment
This backend needs [perceval](https://github.com/chaoss/grimoirelab-perceval) installed.

The perceval/backends/sonarqube/sonarqube.py executable beelongs inside /usr/local/lib/python3.5/dist-packages/
(as /usr/local/lib/python3.5/dist-packages/perceval/backends/sonarqube/sonarqube.py) to
- be available for perceval and the test runners.
- have perceval available.

## Configuration
The executable expects the configuration file perceval/backends/sonarqube/sonarqube.cfg to be on the same directory.
It accepts the following (sections and) parameters:

[connection]

- SSL_VERIFY accepts True/False, Y/N, Yes/No.
- API_TOKEN is a user token for the SonarQube API.

[sonarqube]

- TARGET_METRIC_FIELDS is a list of Sonarqube metric names sepparated by commas.

## Configuration
The executable expects the configuration file perceval/backends/sonarqube/sonarqube.cfg to be on the same directory.
It accepts the following (sections and) parameters:

[connection]

- SSL_VERIFY accepts True/False, Y/N, Yes/No.
- API_TOKEN is a user token for the SonarQube API.

[sonarqube]

- TARGET_METRIC_FIELDS is a list of Sonarqube metric names sepparated by commas.

## Usage
Once correctly deployed this backend is used like any other. `perceval sonarqube --help` shows the corresponding help, with the list of available categories for Sonarqube.

**Ignore** the archive-related arguments. Archiving isn't yet implemented. `--from-date` isn't implented yet either.

## Testing

Please check [TESTING.md](https://github.com/fioddor/sonarqube-perceval-backend/blob/master/TESTING.md) for more details. For a fast track introduction:

1. install httpretty: `$ sudo pip install httpretty`
1. run all enabled tests: `$ python3 tests/test_sonarqube.py`


# Links

[1] https://www.sonarqube.org

[2] https://github.com/chaoss/grimoirelab-perceval

