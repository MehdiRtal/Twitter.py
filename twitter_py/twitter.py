import httpx
import json
import re
import random
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import hashlib
import time

from twitter_py.models import Tweet, User
from twitter_py.utils import generate_csrf_token, generate_transaction_id


class Twitter:
    def __init__(self, proxy: str = None, captcha_handler: callable = None):
        self._captcha_handler = captcha_handler
        self._client = httpx.Client(proxies=f"http://{proxy}" if proxy else None, timeout=httpx.Timeout(10, read=30))
        self.session = None
        self.username = None
        self.guest_token = None
        csrf_token = generate_csrf_token()
        ua = UserAgent()
        user_agent = ua.chrome
        if user_agent.endswith(" "):
            user_agent = user_agent[:-1]
        self._client.headers.update({
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "X-Csrf-Token": csrf_token,
            "User-Agent": user_agent,
        })
        self._client.cookies.update({
            "ct0": csrf_token
        })

    def _refresh_guest_token(self):
        headers = {
            "Authorization": "",
            "Referer": "https://twitter.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        r = self._client.get("https://twitter.com/", headers=headers, follow_redirects=True)
        r.raise_for_status()
        self.guest_token = re.search(r"gt=(\d+)", r.text).group(1)

    def signup(self, name: str, email: str, password: str, otp_handler: callable):
        if not self.guest_token:
            self._refresh_guest_token()

        headers = {
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Guest-Token": self.guest_token,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en",
        }
        body = {
            "input_flow_data": {
                "requested_variant": "{\"signup_type\":\"phone_email\"}",
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {
                        "location": "splash_screen"
                    }
                }
            },
            "subtask_versions": {
                "action_list": 2,
                "alert_dialog": 1,
                "app_download_cta": 1,
                "check_logged_in_account": 1,
                "choice_selection": 3,
                "contacts_live_sync_permission_prompt": 0,
                "cta": 7,
                "email_verification": 2,
                "end_flow": 1,
                "enter_date": 1,
                "enter_email": 2,
                "enter_password": 5,
                "enter_phone": 2,
                "enter_recaptcha": 1,
                "enter_text": 5,
                "enter_username": 2,
                "generic_urt": 3,
                "in_app_notification": 1,
                "interest_picker": 3,
                "js_instrumentation": 1,
                "menu_dialog": 1,
                "notifications_permission_prompt": 2,
                "open_account": 2,
                "open_home_timeline": 1,
                "open_link": 1,
                "phone_verification": 4,
                "privacy_options": 1,
                "security_key": 3,
                "select_avatar": 4,
                "select_banner": 2,
                "settings_list": 7,
                "show_code": 1,
                "sign_up": 2,
                "sign_up_review": 4,
                "tweet_selection_urt": 1,
                "update_users": 1,
                "upload_media": 1,
                "user_recommendations_list": 4,
                "user_recommendations_urt": 1,
                "wait_spinner": 3,
                "web_modal": 1
            }
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json?flow_name=signup", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "email": email,
            "display_name": name,
            "flow_token": flow_token
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/begin_verification.json", headers=headers, json=body)
        r.raise_for_status()

        otp = otp_handler()
        for _ in range(3):
            try:
                token = self._captcha_handler(public_key="2CB16598-CB82-4CF7-B332-5990DB66F3AB", url="https://twitter.com/i/flow/signup")
            except Exception:
                pass
            else:
                break
        else:
            raise Exception("Failed to solve captcha")
        body = {
            "flow_token": flow_token,
            "subtask_inputs": [
                {
                    "subtask_id": "Signup",
                    "sign_up": {
                        "link": "email_next_link",
                        "name": name,
                        "email": email,
                        "birthday": {
                            "day": random.randint(1, 28),
                            "month": random.randint(1, 12),
                            "year": random.randint(1950, 2000)
                        },
                        "personalization_settings": {
                            "allow_cookie_use": True,
                            "allow_device_personalization": True,
                            "allow_partnerships": True,
                            "allow_ads_personalization": True
                        }
                    }
                },
                {
                    "subtask_id": "SignupSettingsListEmailNonEU",
                    "settings_list": {
                        "setting_responses": [
                            {
                                "key": "twitter_for_web",
                                "response_data": {
                                    "boolean_data": {
                                        "result": True
                                    }
                                }
                            }
                        ],
                        "link": "next_link"
                    }
                },
                {
                    "subtask_id": "SignupReview",
                    "sign_up_review": {
                        "link": "signup_with_email_next_link"
                    }
                },
                {
                    "subtask_id": "ArkoseEmail",
                    "web_modal": {
                        "completion_deeplink": f"twitter://onboarding/web_modal/next_link?access_token={token}",
                        "link": "signup_with_email_next_link"
                    }
                },
                {
                    "subtask_id": "EmailVerification",
                    "email_verification": {
                        "code": otp,
                        "email": email,
                        "link": "next_link"
                    }
                }
            ]
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "flow_token": flow_token,
            "subtask_inputs": [
                {
                    "subtask_id": "EnterPassword",
                    "enter_password": {
                        "password": password,
                        "link": "next_link"
                    }
                }
            ]
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        self.session = r.cookies["auth_token"]
        self.username = data["subtasks"][0]["open_account"]["user"]["screen_name"]

    def login(self, username: str = None, password: str = None, email: str = None, session: str = None, otp_handler: callable = None):
        if username and password:
            if not self.guest_token:
                self._refresh_guest_token()

            headers = {
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "X-Client-Transaction-Id": generate_transaction_id(),
                "X-Guest-Token": self.guest_token,
                "X-Twitter-Active-User": "yes",
                "X-Twitter-Client-Language": "en",
            }
            body = {
                "input_flow_data": {
                    "flow_context": {
                        "debug_overrides": {},
                        "start_location": {
                            "location": "splash_screen"
                        }
                    }
                },
                "subtask_versions": {
                    "action_list": 2,
                    "alert_dialog": 1,
                    "app_download_cta": 1,
                    "check_logged_in_account": 1,
                    "choice_selection": 3,
                    "contacts_live_sync_permission_prompt": 0,
                    "cta": 7,
                    "email_verification": 2,
                    "end_flow": 1,
                    "enter_date": 1,
                    "enter_email": 2,
                    "enter_password": 5,
                    "enter_phone": 2,
                    "enter_recaptcha": 1,
                    "enter_text": 5,
                    "enter_username": 2,
                    "generic_urt": 3,
                    "in_app_notification": 1,
                    "interest_picker": 3,
                    "js_instrumentation": 1,
                    "menu_dialog": 1,
                    "notifications_permission_prompt": 2,
                    "open_account": 2,
                    "open_home_timeline": 1,
                    "open_link": 1,
                    "phone_verification": 4,
                    "privacy_options": 1,
                    "security_key": 3,
                    "select_avatar": 4,
                    "select_banner": 2,
                    "settings_list": 7,
                    "show_code": 1,
                    "sign_up": 2,
                    "sign_up_review": 4,
                    "tweet_selection_urt": 1,
                    "update_users": 1,
                    "upload_media": 1,
                    "user_recommendations_list": 4,
                    "user_recommendations_urt": 1,
                    "wait_spinner": 3,
                    "web_modal": 1
                }
            }
            r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json?flow_name=login", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]

            body = {
                "flow_token": flow_token,
                "subtask_inputs": [
                    {
                        "subtask_id": "LoginJsInstrumentationSubtask",
                        "js_instrumentation": {
                            "response": json.dumps({"rf":{"a09c71841bd9f4d27bd346884026bacaaf4e08e4df409437e1dfa0daa473e255":-244,"a4709145d8b647971ed8d008fbb71582dfabf395199016426a047f23e0856bb0":-175,"ac41dd06a5824fb7c0d7882007cc7d48bb6b787092915e56f83c53f31ee3dd08":72,"f851c0cbe720b43a67010f8f9b2c02b7c869023aa836f238a54e3f487fc7d686":-132},"s":"9JnhidShEmBkzvxgCzycTEICsjnNAU8h8kLJ9YeJdFaxiF8OxLN4Wb-m8DWZavJy9FOti-n1HLovSBet_nTxhVnXIYWFCRjHJQQ6zdYrGfT8etndSZIUMLetwaTceml0Wwju7EnVI2Ac4U08Dif3BqOCu7wgr2bAf5gKy4jCRn6X6-N_zpSltK6or8ma7rBm9bRRt2WG9WXQWna9cssbpOdL2b0ZBUh82rrKV5Q_xMiaDQsd_kXey_zbCA0o3mcy1KlGjWy2ZKIf7NI3sxuHcaWrTOgzuHJtSihoOdEHSEkFRVuv8G3-vadY3GQxVuIySI-eAQ6G5Q57pqBer25hDgAAAYsqkTND"}),
                            "link": "next_link"
                        }
                    }
                ]
            }
            r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]

            body = {
                "flow_token": flow_token,
                "subtask_inputs": [
                    {
                        "subtask_id": "LoginEnterUserIdentifierSSO",
                        "settings_list": {
                            "setting_responses": [
                                {
                                    "key": "user_identifier",
                                    "response_data": {
                                        "text_data": {
                                            "result": username
                                        }
                                    }
                                }
                            ],
                            "link": "next_link"
                        }
                    }
                ]
            }
            r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]

            body = {
                "flow_token": flow_token,
                "subtask_inputs": [
                    {
                        "subtask_id": "LoginEnterPassword",
                        "enter_password": {
                            "password": password,
                            "link": "next_link"
                        }
                    }
                ]
            }
            r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]

            body = {
                "flow_token": flow_token,
                "subtask_inputs": [
                    {
                        "subtask_id": "AccountDuplicationCheck",
                        "check_logged_in_account": {
                            "link": "AccountDuplicationCheck_ False"
                        }
                    }
                ]
            }
            r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()

            if data["subtasks"][0]["subtask_id"] == "LoginAcid":
                otp = otp_handler()
                flow_token = data["flow_token"]
                body = {
                    "flow_token": flow_token,
                    "subtask_inputs": [
                        {
                            "subtask_id": "LoginAcid",
                            "enter_text": {
                                "link": "next_link",
                                "text": otp
                            }
                        }
                    ]
                }
                r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
                r.raise_for_status()

            self.session = r.cookies["auth_token"]
        elif session:
            self.session = session
            self._client.cookies.update({
                "auth_token": self.session
            })

            headers = {
                "Authorization": "",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
            r = self._client.get("https://twitter.com/account/access", headers=headers, follow_redirects=True)
            if "login" in str(r.url):
                raise Exception("Invalid auth token")

    def solve_captcha(self):
        headers = {
            "Authorization": "",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        r = self._client.get("https://twitter.com/account/access", headers=headers, follow_redirects=True)
        r.raise_for_status()

        if "access" in str(r.url):
            soup = BeautifulSoup(r.text, "html.parser")
            authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
            assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")

            headers.update({
                "Referer": "https://twitter.com/account/access",
            })

            for _ in range(3):
                token = self._captcha_handler(public_key="0152B4EB-D2DC-460A-89A1-629838B529C9", url="https://twitter.com/account/access")
                body = {
                    "authenticity_token": authenticity_token,
                    "assignment_token": assignment_token,
                    "lang": "en",
                    "flow": "",
                    "verification_string": token,
                    "language_code": "en"
                }
                r = self._client.post("https://twitter.com/account/access", headers=headers, data=body)
                soup = BeautifulSoup(r.text, "html.parser")
                if not soup.find("form", {"id": "arkose_form"}):
                    break
                authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
                assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")
            else:
                raise Exception("Failed to solve captcha")

    def change_password(self, password: str, new_password: str):
        headers = {
            "Referer": "https://twitter.com/settings/password",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "current_password": password,
            "password": new_password,
            "password_confirmation": new_password
        }
        r = self._client.post("https://twitter.com/i/api/i/account/change_password.json", headers=headers, data=body)
        r.raise_for_status()
        self.session = r.cookies["auth_token"]

    def change_email(self, password: str, new_email: str, otp_handler: callable):
        headers = {
            "Referer": "https://twitter.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en",
        }
        body = {
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {
                        "location": "settings"
                    }
                }
            },
            "subtask_versions": {
                "action_list": 2,
                "alert_dialog": 1,
                "app_download_cta": 1,
                "check_logged_in_account": 1,
                "choice_selection": 3,
                "contacts_live_sync_permission_prompt": 0,
                "cta": 7,
                "email_verification": 2,
                "end_flow": 1,
                "enter_date": 1,
                "enter_email": 2,
                "enter_password": 5,
                "enter_phone": 2,
                "enter_recaptcha": 1,
                "enter_text": 5,
                "enter_username": 2,
                "generic_urt": 3,
                "in_app_notification": 1,
                "interest_picker": 3,
                "js_instrumentation": 1,
                "menu_dialog": 1,
                "notifications_permission_prompt": 2,
                "open_account": 2,
                "open_home_timeline": 1,
                "open_link": 1,
                "phone_verification": 4,
                "privacy_options": 1,
                "security_key": 3,
                "select_avatar": 4,
                "select_banner": 2,
                "settings_list": 7,
                "show_code": 1,
                "sign_up": 2,
                "sign_up_review": 4,
                "tweet_selection_urt": 1,
                "update_users": 1,
                "upload_media": 1,
                "user_recommendations_list": 4,
                "user_recommendations_urt": 1,
                "wait_spinner": 3,
                "web_modal": 1
            }
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json?flow_name=add_email", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "flow_token": flow_token,
            "subtask_inputs": [
                {
                    "subtask_id": "DeviceAssocEnterPassword",
                    "enter_password": {
                        "password": password,
                        "link": "next_link"
                    }
                }
            ]
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "email": new_email,
            "flow_token": flow_token
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/begin_verification.json", headers=headers, json=body)
        r.raise_for_status()

        otp = otp_handler()
        body = {
            "flow_token": flow_token,
            "subtask_inputs": [
                {
                    "subtask_id": "EmailAssocEnterEmail",
                    "enter_email": {
                        "setting_responses": [
                            {
                                "key": "email_discoverability_setting",
                                "response_data": {
                                    "boolean_data": {
                                        "result": False
                                    }
                                }
                            }
                        ],
                        "email": new_email,
                        "link": "next_link"
                    }
                },
                {
                    "subtask_id": "EmailAssocVerifyEmail",
                    "email_verification": {
                        "code": otp,
                        "email": new_email,
                        "link": "next_link"
                    }
                }
            ]
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()

    def edit_profile(self, name: str = "", bio: str = "", avatar: bytes = None):
        if avatar:
            params = {
                "command": "INIT",
                "total_bytes": len(avatar),
                "media_type": "image/jpeg"
            }
            headers = {
                "Referer": "https://twitter.com/"
            }
            r = self._client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers)
            r.raise_for_status()
            media_id = r.json()["media_id"]

            headers = {
                "Referer": "https://twitter.com/"
            }
            files = {
                "media": ("blob", avatar, "application/octet-stream")
            }
            params = {
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": 0
            }
            r = self._client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers, files=files)
            r.raise_for_status()

            headers = {
                "Referer": "https://twitter.com/"
            }
            params = {
                "command": "FINALIZE",
                "media_id": media_id,
                "original_md5": hashlib.md5(avatar).hexdigest()
            }
            r = self._client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers)
            r.raise_for_status()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            body = f"include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&include_ext_has_nft_avatar=1&include_ext_is_blue_verified=1&include_ext_verified_type=1&include_ext_profile_image_shape=1&skip_status=1&return_user= True&media_id={media_id}"
            r = self._client.post("https://api.twitter.com/1.1/account/update_profile_image.json", headers=headers, data=body)
            r.raise_for_status()

        if name or bio:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            body = "birthdate_day=0&birthdate_month=0&birthdate_year=0"
            r = self._client.post("https://api.twitter.com/1.1/account/update_profile.json", headers=headers, data=body)
            r.raise_for_status()

            body = f"displayNameMaxLength=50&name={name}&description={bio}&location="
            r = self._client.post("https://api.twitter.com/1.1/account/update_profile.json", headers=headers, data=body)
            r.raise_for_status()

            self.solve_captcha()

    def like(self, tweet_id: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_id": tweet_id
            },
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        }
        self._client.post("https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet", headers=headers, json=body).raise_for_status()

    def follow(self, user: User):
        headers = {
            "Referer": f"https://twitter.com/{user.username}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        params = {
            "user_id": user.id
        }
        self._client.post("https://twitter.com/i/api/1.1/friendships/create.json", headers=headers, params=params).raise_for_status()

    def tweet(self, text: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_text": text,
                "dark_request": False,
                "media": {
                    "media_entities": [],
                    "possibly_sensitive": False
                },
                "semantic_annotation_ids": []
            },
            "features": {
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_home_pinned_timelines_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "5V_dkq1jfalfiFOEZ4g47A"
        }
        self._client.post("https://twitter.com/i/api/graphql/5V_dkq1jfalfiFOEZ4g47A/CreateTweet", headers=headers, json=body).raise_for_status()

    def reply(self, tweet_id: str, text: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_text": text,
                "reply": {
                    "in_reply_to_tweet_id": tweet_id,
                    "exclude_reply_user_ids": []
                },
                "dark_request": False,
                "media": {
                    "media_entities": [],
                    "possibly_sensitive": False
                },
                "semantic_annotation_ids": []
            },
            "features": {
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "SoVnbfCycZ7fERGCwpZkYA"
        }
        self._client.post("https://twitter.com/i/api/graphql/SoVnbfCycZ7fERGCwpZkYA/CreateTweet", headers=headers, json=body).raise_for_status()

    def retweet(self, tweet_id: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        }
        self._client.post("https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet", headers=headers, json=body).raise_for_status()

    def bookmark(self, tweet_id: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_id": tweet_id,
            },
            "queryId": "aoDbu3RHznuiSkQ9aNM67Q"
        }
        self._client.post("https://twitter.com/i/api/graphql/aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark", headers=headers, json=body).raise_for_status()

    def watch_space(self, id: str, sleep_m: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        r = self._client.get("https://twitter.com/i/api/1.1/oauth/authenticate_periscope.json", headers=headers)
        r.raise_for_status()
        r_json = r.json()
        token = r_json["token"]

        body = {
            "jwt": token,
            "vendor_id": "m5-proxsee-login-a2011357b73e",
            "create_user": False,
            "direct": True
        }
        r = self._client.post("https://proxsee.pscp.tv/api/v2/loginTwitterToken", headers=headers, json=body)
        r.raise_for_status()
        r_json = r.json()
        cookie = r_json["cookie"]

        media_key = self.get_space_info(id)["metadata"]["media_key"]

        r = self._client.get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}?client=web&use_syndication_guest_id=False&cookie_set_host=twitter.com", headers=headers)
        r.raise_for_status()
        r_json = r.json()
        chat_token = r_json["chatToken"]
        life_cycle_token = r_json["lifecycleToken"]

        body = {
            "chat_token": chat_token,
            "cookie": cookie
        }
        self._client.post("https://proxsee.pscp.tv/api/v2/twitter/accessChat", headers=headers, json=body).raise_for_status()

        body = {
            "cookie": cookie,
            "service": "guest"
        }
        r = self._client.post("https://proxsee.pscp.tv/api/v2/twitter/authorizeToken", headers=headers, json=body).raise_for_status()

        body = {
            "auto_play": False,
            "cookie": cookie,
            "life_cycle_token": life_cycle_token
        }
        r = self._client.post("https://proxsee.pscp.tv/api/v2/twitter/startWatching", headers=headers, json=body)
        r.raise_for_status()
        r_json = r.json()
        session = r_json["session"]

        for _ in range(sleep_m * 2):
            body = {
                "cookie": cookie,
                "session": session
            }
            self._client.post("https://proxsee.pscp.tv/api/v2/twitter/pingWatching", headers=headers, json=body).raise_for_status()
            time.sleep(30)

    def delete_tweet(self, tweet_id: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "VaenaVgh5q5ih7kvyVjgtg"
        }
        self._client.post("https://twitter.com/i/api/graphql/VaenaVgh5q5ih7kvyVjgtg/DeleteTweet", headers=headers, json=body).raise_for_status()

    def delete_retweet(self, tweet_id: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        body = {
            "variables": {
                "source_tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "iQtK4dl5hBmXewYZuEOKVw"
        }
        self._client.post("https://twitter.com/i/api/graphql/iQtK4dl5hBmXewYZuEOKVw/DeleteRetweet", headers=headers, json=body).raise_for_status()

    def get_tweet_id(self, url: str):
        return re.search(r"\/status\/(\d+)", url).group(1)

    def get_space_id(self, url: str):
        return re.search(r"\/spaces\/([A-Za-z0-9]+)", url).group(1)

    def get_space_info(self, space_id: str):
        headers = {
            "Referer": f"https://twitter.com/i/spaces/{space_id}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en"
        }
        params = {
            "variables": json.dumps({
                "id": space_id,
                "isMetatagsQuery": True,
                "withReplays": True,
                "withListeners": True
            }),
            "features": json.dumps({
                "spaces_2022_h2_spaces_communities": True,
                "spaces_2022_h2_clipping": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }),
        }
        r = self._client.get("https://twitter.com/i/api/graphql/MZwo_AA10ZpJfbY4ZekqQA/AudioSpaceById", headers=headers, params=params)
        r.raise_for_status()
        return r.json()["data"]["audioSpace"]

    def get_user_info(self, username: str) -> User:
        if not self.guest_token:
            self._refresh_guest_token()

        headers = {
            "Referer": f"https://twitter.com/{username}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Guest-Token": self.guest_token,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en",
        }
        params = {
            "variables": json.dumps({
                "screen_name": username,
                "withSafetyModeUserFields": True
            }),
            "features": json.dumps({
                "hidden_profile_likes_enabled":True,
                "hidden_profile_subscriptions_enabled":True,
                "responsive_web_graphql_exclude_directive_enabled":True,
                "verified_phone_label_enabled":False,
                "subscriptions_verification_info_is_identity_verified_enabled":True,
                "subscriptions_verification_info_verified_since_enabled":True,
                "highlights_tweets_tab_ui_enabled":True,
                "responsive_web_twitter_article_notes_tab_enabled":True,
                "creator_subscriptions_tweet_preview_api_enabled":True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,
                "responsive_web_graphql_timeline_navigation_enabled":True
            }),
            "fieldToggles": json.dumps({
                "withAuxiliaryUserLabels": False
            }),
        }
        r = self._client.get("https://api.twitter.com/graphql/k5XapwcSikNsEsILW5FvgA/UserByScreenName", headers=headers, params=params)
        r.raise_for_status()
        return User(**r.json()["data"]["user"]["result"])

    def get_user_tweets(self, user: User) -> list[Tweet]:
        if not self.guest_token:
            self._refresh_guest_token()

        headers = {
            "Referer": f"https://twitter.com/{user.username}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Guest-Token": self.guest_token,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en"
        }
        params = {
            "variables": json.dumps({
                "userId": user.id,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled":True,
                "verified_phone_label_enabled":False,
                "creator_subscriptions_tweet_preview_api_enabled":True,
                "responsive_web_graphql_timeline_navigation_enabled":True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,
                "c9s_tweet_anatomy_moderator_badge_enabled":True,
                "tweetypie_unmention_optimization_enabled":True,
                "responsive_web_edit_tweet_api_enabled":True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,
                "view_counts_everywhere_api_enabled":True,
                "longform_notetweets_consumption_enabled":True,
                "responsive_web_twitter_article_tweet_consumption_enabled":True,
                "tweet_awards_web_tipping_enabled":False,
                "freedom_of_speech_not_reach_fetch_enabled":True,
                "standardized_nudges_misinfo":True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,
                "rweb_video_timestamps_enabled":True,
                "longform_notetweets_rich_text_read_enabled":True,
                "longform_notetweets_inline_media_enabled":True,
                "responsive_web_enhance_cards_enabled":False
            })
        }
        r = self._client.get("https://api.twitter.com/graphql/eS7LO5Jy3xgmd3dbL044EA/UserTweets", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [Tweet(**tweet["content"]["itemContent"]["tweet_results"]["result"]) for tweet in instruction["entries"]]

    def get_tweet_info(self, url: str) -> Tweet:
        if not self.guest_token:
            self._refresh_guest_token()

        headers = {
            "Referer": url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client-Transaction-Id": generate_transaction_id(),
            "X-Guest-Token": self.guest_token,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en"
        }
        params = {
            "variables": json.dumps({
                "tweetId":self.get_tweet_id(url),
                "withCommunity":False,
                "includePromotedContent":False,
                "withVoice":False
            }),
            "features": json.dumps({
                "creator_subscriptions_tweet_preview_api_enabled":True,
                "c9s_tweet_anatomy_moderator_badge_enabled":True,
                "tweetypie_unmention_optimization_enabled":True,
                "responsive_web_edit_tweet_api_enabled":True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,
                "view_counts_everywhere_api_enabled":True,
                "longform_notetweets_consumption_enabled":True,
                "responsive_web_twitter_article_tweet_consumption_enabled":True,
                "tweet_awards_web_tipping_enabled":False,
                "freedom_of_speech_not_reach_fetch_enabled":True,
                "standardized_nudges_misinfo":True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,
                "rweb_video_timestamps_enabled":True,
                "longform_notetweets_rich_text_read_enabled":True,
                "longform_notetweets_inline_media_enabled":True,
                "responsive_web_graphql_exclude_directive_enabled":True,
                "verified_phone_label_enabled":False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,
                "responsive_web_graphql_timeline_navigation_enabled":True,
                "responsive_web_enhance_cards_enabled":False}),
            "fieldToggles": json.dumps({
                "withArticleRichContentState": False
            })
        }
        r = self._client.get("https://api.twitter.com/graphql/OUKdeWm3g4tDbW5hffX_QA/TweetResultByRestId", headers=headers, params=params)
        r.raise_for_status()
        return Tweet(**r.json()["data"]["tweetResult"]["result"])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()
