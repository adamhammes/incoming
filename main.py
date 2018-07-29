
import logging
import pprint
import sys
from urllib.parse import urlparse

import cssselect
import lxml.html
import requests
import toml
import twilio.rest

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1)"
HEADERS = {"User-Agent": USER_AGENT}

ACCOUNT_FORM_DEFAULTS = {"autologin": "false", "language": "en", "kid": ""}

USER_LOGIN_URL = "https://lobby-api.ogame.gameforge.com/users"
ACCOUNT_INFO_URL = "https://lobby-api.ogame.gameforge.com/users/me/accounts"
LOGIN_LINK_URL = "https://lobby-api.ogame.gameforge.com/users/me/loginLink"

ATTACK_ALERT_SELECTOR = "#attack_alert:not(.noAttack)"


def am_being_attacked(main_page_response):
    tree = lxml.html.fromstring(main_page_response.text)
    return bool(tree.cssselect(ATTACK_ALERT_SELECTOR))


def user_login(session, user_credentials):
    email, password = user_credentials["email"], user_credentials["password"]

    logging.info(f"Performing login for {email}")

    session.headers = HEADERS

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
        return []

    account_json = account_response.json()

    logging.info(f"Num accounts: {len(account_json)}")

    logging.info("START account list\n")

    accounts = []
    for account in account_json:
        account_info = {
            "account_id": account["id"],
            "server_id": account["server"]["number"],
            "language": account["server"]["language"],
        }

        logging.info(pprint.pformat(account_info))
        accounts.append(account_info)

    logging.info("\nEND account list\n")

    return accounts


def account_login(session, account):
    login_query = {
        "id": account["account_id"],
        "server[number]": account["server_id"],
        "server[language]": account["language"],
    }

    return session.get(LOGIN_LINK_URL, params=login_query).json()["url"]


def check_for_attacks(session, account_login_url):
    logging.info(f"Login link: {account_login_url}")

    page_response = session.get(account_login_url)

    if page_response.ok:
        logging.info("Successfully logged in!")
    else:
        logging.error("Failed game login :-(")
        sys.exit()

    being_attacked = am_being_attacked(page_response)

    if not being_attacked:
        logging.info("All clear.")
        return []
    else:
        logging.info("You are being attacked!")
        logging.info("Fetching event info...")

    base_location = urlparse(account_login_url).netloc
    event_info_url = f"https://{base_location}/game/index.php?page=eventList&ajax=1"

    event_response = session.get(event_info_url)

    if event_response.ok:
        logging.info("Successfully retrieved event info")
    else:
        logging.error("Failed event info fetch :-(")
        sys.exit()

    return read_attacks(event_response)


def read_attacks(event_response):
    event_tree = lxml.html.fromstring(event_response.text)

    all_attack_selector = 'tr[data-mission-type="1"]'
    all_attack_rows = event_tree.cssselect(all_attack_selector)

    def attack_is_hostile(row):
        return row.cssselect(".countDown.hostile")

    hostile_attack_rows = filter(attack_is_hostile, all_attack_rows)

    hostile_attacks = []
    logging.debug("START: incoming attacks\n")
    for row in hostile_attack_rows:
        attack_info = {
            "id": row.get("id"),
            "arrival_time": row.get("data-arrival-time"),
            "origin": row.cssselect(".originFleet")[0].text_content().strip(),
            "destination": row.cssselect(".destFleet")[0].text_content().strip(),
        }

        logging.info(pprint.pformat(attack_info))
        hostile_attacks.append(attack_info)

    logging.debug("\nEND: incoming attacks\n")

    return hostile_attacks


def notify_attacks(config, user, attacks):
    client = twilio.rest.Client(
        account_sid=config["twilio"]["account_sid"],
        oauth_token=config["twilio"]["oauth_token"],
    )

    user_cell = user["cell_number"]

    client.messages.create(
        from_=config["twilio"]["number"],
        to=user_cell,
        body="You're under attack! - OGame Incoming!",
    )


def run(config):
    for user in config["users"]:
        with requests.Session() as session:
            accounts = user_login(session, user)

            for account in accounts:
                account_url = account_login(session, account)
                attacks = check_for_attacks(session, account_url)

                if attacks:
                    notify_attacks(config, user, attacks)


def main():
    config = toml.load("config.toml")
    run(config)


if __name__ == "__main__":
    main()
