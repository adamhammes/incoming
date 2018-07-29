
import logging
import sys
from urllib.parse import urlparse

import requests
import toml

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1)"
HEADERS = {"User-Agent": USER_AGENT}

ACCOUNT_FORM_DEFAULTS = {"autologin": "false", "language": "en", "kid": ""}

USER_LOGIN_URL = "https://lobby-api.ogame.gameforge.com/users"
ACCOUNT_INFO_URL = "https://lobby-api.ogame.gameforge.com/users/me/accounts"
LOGIN_LINK_URL = "https://lobby-api.ogame.gameforge.com/users/me/loginLink"


def login(user_credentials):
    email, password = user_credentials["email"], user_credentials["password"]

    logging.info(f"Performing login for {email}")

    with requests.Session() as session:
        session.headers = HEADERS

        # Perform the login action
        user_login_data = {
            **ACCOUNT_FORM_DEFAULTS,
            "credentials[email]": email,
            "credentials[password]": password,
        }

        login_response = session.post(USER_LOGIN_URL, data=user_login_data)

        if login_response.ok:
            logging.info("Successfully logged into account!")
        else:
            logging.error("Failed account login :-(")
            sys.exit()

        # Fetch the account info
        account_response = session.get(ACCOUNT_INFO_URL)

        if account_response.ok:
            logging.info("Successfully navigated to the lobby!")
        else:
            logging.error("Could not access lobby :-(")
            sys.exit()

        account_json = account_response.json()

        logging.info(f"Num accounts: {len(account_json)}")

        logging.info("START account list\n")

        for account in account_json:
            logging.info(f"Account name: {account['name']}")
            logging.info(f"Account id:   {account['id']}")
            logging.info(f"Universe id:  {account['server']['number']}")

        logging.info("\nEND account list\n")

        account = account_json[0]
        account_id = account["id"]
        universe_language = account["server"]["language"]
        universe_id = account["server"]["number"]

        login_query = {
            "id": account_id,
            "server[language]": universe_language,
            "server[number]": universe_id,
        }

        game_login_url = session.get(LOGIN_LINK_URL, params=login_query).json()["url"]
        logging.info(f"Login link: {game_login_url}")

        page_response = session.get(game_login_url)

        if page_response.ok:
            logging.info("Successfully logged in!")
        else:
            logging.error("Failed game login :-(")
            sys.exit()

        with open("game_page_normal.html", "w") as f:
            f.write(page_response.text)

        base_location = urlparse(game_login_url).netloc
        event_info_url = f"https://{base_location}/game/index.php?page=eventList&ajax=1"

        event_response = session.get(event_info_url)

        if event_response.ok:
            logging.info("Successfully retrieved event info")
        else:
            logging.error("Failed event info fetch :-(")
            sys.exit()

        with open("event_info.html", "w") as f:
            f.write(event_response.text)


def run(config):
    for account in config["accounts"]:
        login(account)


def main():
    config = toml.load("config.toml")
    run(config)


if __name__ == "__main__":
    main()
