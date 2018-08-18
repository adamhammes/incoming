# Incoming!

Incoming! is a Python script to detect incoming attacks in [OGame](https://en.ogame.gameforge.com/) and notify the user by text message.

## Prerequisites:

* [A Twilio account and number](https://www.twilio.com/try-twilio)
* [Python >= 3.7](https://www.python.org/getit/)
* [Pipenv](https://docs.pipenv.org/install/#installing-pipenv)


## Quickstart:

If you haven't already, install the [prerequisites](#prerequisites).
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

... and edit it to include your Twilio/OGame credentials.
For example,

```toml
[twilio]

# Your Account Sid and Auth Token from twilio.com/console

account_sid = "asdfasdfasdfasdf"
auth_token = "asdfasdfasdfasdf"

# Your Twilio number to send from
from_number = "+12222222222"

# Repeat this section for each user you wish to monitor.
# By default, Incoming! will check all of a user's accounts.
[[users]]

email = "your account email"
password = "your account password"

cell_number = "+233333333333"
```

Now you're ready to rumble!

```
$ pipenv run python main.py
```