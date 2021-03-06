import datetime
import logging
import os
import pprint
import sys
import time
from urllib.parse import urlparse

import cssselect
import lxml.html
import requests
import toml
import twilio.rest


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1)"
HEADERS = {"User-Agent": USER_AGENT}

ACCOUNT_FORM_DEFAULTS = {"autologin": "false", "language": "en", "kid": ""}

USER_LOGIN_URL = "https://lobby-api.ogame.gameforge.com/users"
ACCOUNT_INFO_URL = "https://lobby-api.ogame.gameforge.com/users/me/accounts"
LOGIN_LINK_URL = "https://lobby-api.ogame.gameforge.com/users/me/loginLink"

ATTACK_ALERT_SELECTOR = "#attack_alert:not(.noAttack)"

OUTPUT_DIR = "output"
ATTACK_CACHE_PATH = os.path.join(OUTPUT_DIR, "seen_attacks.toml")
LOG_PATH = os.path.join(OUTPUT_DIR, "log.txt")


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
            "id": row.get("id").split("-")[1],
            "arrival_time": int(row.get("data-arrival-time")),
            "origin": row.cssselect(".originFleet")[0].text_content().strip(),
            "destination": row.cssselect(".destFleet")[0].text_content().strip(),
        }

        logging.info(pprint.pformat(attack_info))
        hostile_attacks.append(attack_info)

    logging.debug("\nEND: incoming attacks\n")

    return hostile_attacks


def cache_and_filter_attacks(user, attacks):
    with open(ATTACK_CACHE_PATH, "r+") as f:
        attack_cache = toml.loads(f.read())

    if not user["email"] in attack_cache:
        attack_cache[user["email"]] = {}

    previous_attacks = attack_cache[user["email"]]

    new_attacks = []
    for attack in attacks:
        if attack["id"] in previous_attacks:
            logging.info(f"Attack #{attack['id']} already seen")
        else:
            logging.info(f"Attack #{attack['id']} is new!")
            new_attacks.append(attack)
            previous_attacks[attack["id"]] = attack

    with open(ATTACK_CACHE_PATH, "w") as f:
        toml.dump(attack_cache, f)

    return new_attacks


def notify_attacks(config, user, attacks):
    client = twilio.rest.Client(
        config["twilio"]["account_sid"], config["twilio"]["auth_token"]
    )

    user_cell = user["cell_number"]

    first_arrival = min(attack["arrival_time"] for attack in attacks)
    now = int(time.time())

    time_delta = datetime.timedelta(seconds=first_arrival - now)

    client.messages.create(
        from_=config["twilio"]["from_number"],
        to=user_cell,
        body=f"You're under attack! Arrival in {str(time_delta)}.",
    )


def run(config):
    for user in config["users"]:
        with requests.Session() as session:
            accounts = user_login(session, user)

            for account in accounts:
                account_url = account_login(session, account)
                all_attacks = check_for_attacks(session, account_url)

                new_attacks = cache_and_filter_attacks(user, all_attacks)

                if new_attacks:
                    notify_attacks(config, user, new_attacks)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Create the attack cache if it doesn't already exist
    open(ATTACK_CACHE_PATH, "a").close()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="a"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    config = toml.load("config.toml")
    run(config)


if __name__ == "__main__":
    main()
