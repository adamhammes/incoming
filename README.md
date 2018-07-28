# Incoming!

Incoming! is a Python script to detect incoming attacks in [OGame](https://en.ogame.gameforge.com/).


## Dependencies:

* [Python >= 3.7](https://www.python.org/getit/)
* [Pipenv](https://docs.pipenv.org/install/#installing-pipenv)


## Quickstart:

If you haven't already, install the [dependencies](#dependencies).
Then, grab a copy of the project and its dependencies:

```
$ git clone https://github.com/adamhammes/incoming.git
$ cd incoming
$ pipenv install
```

Create the config file...

```
$ touch config.toml
```

... and edit it to include your OGame credentials.
For example,

```toml
[[accounts]]

email = "your account email"
password = "your account password"
```

Now you're ready to rumble!

```
$ pipenv run python main.py
```