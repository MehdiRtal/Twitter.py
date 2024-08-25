import httpx
import json
import re
import random
from bs4 import BeautifulSoup
from fake_useragent import FakeUserAgent
import hashlib
import pickle
import asyncio
import base64

from twitter_py.models import Tweet, User
from twitter_py.utils import generate_csrf_token
from twitter_py.exceptions import UserNotFound, TweetNotFound, InvalidCredentials, InvalidOTP, CaptchaFailed, InvalidEmail, InvalidToken, AccountSuspended


class Twitter:
    def __init__(self, proxy: str = None, captcha_handler: callable = None):
        self._captcha_handler = captcha_handler
        self._private_client = httpx.AsyncClient(proxies=f"http://{proxy}" if proxy else None, timeout=httpx.Timeout(10, read=30))
        self._public_client = httpx.AsyncClient(proxies=f"http://{proxy}" if proxy else None, timeout=httpx.Timeout(10, read=30))
        self.csrf_token = generate_csrf_token()
        ua = FakeUserAgent(browsers="chrome", platforms="pc")
        self.user_agent = ua.random
        if self.user_agent.endswith(" "):
            self.user_agent = self.user_agent[:-1]
        self._private_client.headers.update({
            "User-Agent": self.user_agent,
        })
        self._public_client.headers.update({
            "User-Agent": self.user_agent,
        })
        self._private_client.cookies.update({
            "ct0": self.csrf_token
        })
        self._public_client.cookies.update({
            "ct0": self.csrf_token
        })
        self.session = None
        self.username = None
        self.guest_token = None

    @property
    def graphql_headers(self):
        return {
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "X-Client-Transaction-Id": "EqjcC+Oqz5rVgWFdZa+I58llasRyV8ro8eQlSvR8dPYKLaShdUkhgT2PV0QHokoKMJPHYBDVoFyik9MqBN2IQ0OQwUisEQ",
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Client-Language": "en"
        }

    async def _refresh_guest_token(self):
        headers = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent
        }
        r = await self._private_client.get("https://twitter.com/x/migrate?tok=7b2265223a222f222c2274223a313732333435363038327d5aeeb3ef98ff16b4eacc40c89a8ff4e2", headers=headers, follow_redirects=True)
        r.raise_for_status()
        self.guest_token = re.search(r"gt=(\d+)", r.text).group(1)

    async def signup(self, name: str, email: str, password: str, otp_handler: callable):
        if not self.guest_token:
            await self._refresh_guest_token()

        headers = {
            "Referer": "https://twitter.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Guest-Token": self.guest_token,
        }
        headers.update(self.graphql_headers)
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
        r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json?flow_name=signup", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "email": email,
            "display_name": name,
            "flow_token": flow_token
        }
        r = await self._private_client.post("https://api.x.com/1.1/onboarding/begin_verification.json", headers=headers, json=body)
        r.raise_for_status()

        otp = await asyncio.to_thread(otp_handler)
        token = await asyncio.to_thread(self._captcha_handler, public_key="2CB16598-CB82-4CF7-B332-5990DB66F3AB", url="https://twitter.com/i/flow/signup")
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
        r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
        try:
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]
        except Exception:
            raise InvalidOTP

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
        r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        self.session = json.dumps({"cookies": dict(self._private_client.cookies), "user_agent": self.user_agent})
        self.username = data["subtasks"][0]["open_account"]["user"]["screen_name"]

    async def login(self, username: str = None, password: str = None, email: str = None, session: str = None, otp_handler: callable = None):
        if username and password:
            if not self.guest_token:
                await self._refresh_guest_token()

            headers = {
                "Referer": "https://x.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "X-Guest-Token": self.guest_token,
            }
            headers.update(self.graphql_headers)
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
            r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json?flow_name=login", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            flow_token = data["flow_token"]

            body = {
                "flow_token": flow_token,
                "subtask_inputs": [
                    {
                        "subtask_id": "LoginJsInstrumentationSubtask",
                        "js_instrumentation": {
                            "response": "{\"rf\":{\"a0c31dc7af71809a61f7f806f0e3cc6d4b512badb613b7efb33a79657fa3e0f9\":-124,\"a1d40174a732349eeff8ef71efd8971721abaf99277a1c124005a6feb6f4e9eb\":96,\"cc0bb613e70dee6c8f3a2c078c910bf474d4a21d41be94bb3680cff4a29d59f5\":-108,\"c08306c9c58ef153ac44aa4cf10622225ceb72bf60b30a2051188bea05bafa9b\":123},\"s\":\"r_aBSp-X-hy4vpvBRlcPBANA9NrHfpnG-W0dqg3-zkuZLXWJu-Si5-doXYdM8HAcKJP1s0LcuMN7xfiWyx08rvIdgp5WEXYBNzAJ37ip7JD-TTwZR3zcL5WaFFOTZ9fTha4a-5VQEwVz6JqXaMBIpKnUE_uhWaeG5m5k_9PmVm1ur9UroX1VsNVM1wBt-MiUbYRFPa-hN0jmu2eujdxof320TuYxUutmQW1l3G7nlyL5sw73ZgAmNS_J8eBnC-ZpjB7qA-Vn2z_MunKI_qe-C9OTu_drYgsVkjYyg-EqcoqLQSS8wzvp0CZ6YNpt7bokBZCuI4b_dHWO45br0LKMswAAAZFFvAYb\"}",
                            "link": "next_link"
                        }
                    }
                ]
            }
            r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
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
            r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
            try:
                r.raise_for_status()
                data = r.json()
                flow_token = data["flow_token"]
            except Exception:
                raise InvalidCredentials

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
            r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
            try:
                r.raise_for_status()
                data = r.json()
                flow_token = data["flow_token"]
            except Exception:
                raise InvalidCredentials

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
            r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()

            if data["subtasks"][0]["subtask_id"] == "LoginAcid":
                flow_token = data["flow_token"]
                if data["subtasks"][0]["enter_text"]["keyboard_type"] == "email":
                    body = {
                        "flow_token": flow_token,
                        "subtask_inputs": [
                            {
                                "subtask_id": "LoginAcid",
                                "enter_text": {
                                    "text": email,
                                    "link": "next_link"
                                }
                            }
                        ]
                    }
                    r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
                    try:
                        r.raise_for_status()
                    except Exception:
                        raise InvalidEmail
                if data["subtasks"][0]["enter_text"]["keyboard_type"] == "text":
                    otp = await asyncio.to_thread(otp_handler)
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
                    r = await self._private_client.post("https://api.x.com/1.1/onboarding/task.json", headers=headers, json=body)
                    try:
                        r.raise_for_status()
                    except Exception:
                        raise InvalidOTP


            self.session = json.dumps({"cookies": base64.b64encode(pickle.dumps(self._private_client.cookies.jar._cookies)).decode(), "user_agent": self.user_agent})
        elif session:
            self.session = session
            self._private_client.cookies.jar._cookies.update(pickle.loads(base64.b64decode(session["cookies"])))
            self.csrf_token = self._private_client.cookies.get("ct0")
            self._private_client.headers.update({
                "User-Agent": session["user_agent"]
            })
        await self.solve_captcha()
        await self.check_suspended()

    async def check_suspended(self):
        headers = {
            "Referer": "https://x.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({"count":20,"includePromotedContent":True,"latestControlAvailable":True,"requestContext":"launch","withCommunity":True}),
            "features": json.dumps({"rweb_tipjar_consumption_enabled":True,"responsive_web_graphql_exclude_directive_enabled":True,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"articles_preview_enabled":True,"tweetypie_unmention_optimization_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"rweb_video_timestamps_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_enhance_cards_enabled":False}),
        }
        r = await self._private_client.get("https://x.com/i/api/graphql/A_qu1009UoeQToazaP4YCg/HomeTimeline", headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        if data["data"]["home"]["home_timeline_urt"]["instructions"][0]["entries"][0]["entryId"] == "messageprompt-suspended-prompt":
            raise AccountSuspended

    async def solve_captcha(self):
        headers = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        r = await self._private_client.get("https://twitter.com/account/access", headers=headers, follow_redirects=True)
        r.raise_for_status()

        if "/access" in str(r.url):
            soup = BeautifulSoup(r.text, "html.parser")
            authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
            assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")

            headers.update({
                "Referer": "https://twitter.com/account/access",
            })
            for _ in range(3):
                if not soup.find("form", {"id": "arkose_form"}):
                    body = {
                        "authenticity_token": authenticity_token,
                        "assignment_token": assignment_token,
                        "lang": "en",
                        "flow": ""
                    }
                    r = await self._private_client.post("https://twitter.com/account/access", headers=headers, data=body)
                    break
                token = await asyncio.to_thread(self._captcha_handler, public_key="0152B4EB-D2DC-460A-89A1-629838B529C9", url="https://twitter.com/account/access")
                body = {
                    "authenticity_token": authenticity_token,
                    "assignment_token": assignment_token,
                    "lang": "en",
                    "flow": "",
                    "verification_string": token,
                    "language_code": "en"
                }
                r = await self._private_client.post("https://twitter.com/account/access", headers=headers, data=body)
                soup = BeautifulSoup(r.text, "html.parser")
                authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
                assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")
            else:
                raise CaptchaFailed
        elif "/login" in str(r.url):
            raise InvalidToken

    async def change_password(self, password: str, new_password: str):
        headers = {
            "Referer": "https://twitter.com/settings/password",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "current_password": password,
            "password": new_password,
            "password_confirmation": new_password
        }
        r = await self._private_client.post("https://twitter.com/i/api/i/account/change_password.json", headers=headers, data=body)
        r.raise_for_status()
        self.session = r.cookies["auth_token"]

    async def change_email(self, password: str, new_email: str, otp_handler: callable):
        headers = {
            "Referer": "https://twitter.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
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
        r = await self._private_client.post("https://api.twitter.com/1.1/onboarding/task.json?flow_name=add_email", headers=headers, json=body)
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
        r = await self._private_client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
        flow_token = data["flow_token"]

        body = {
            "email": new_email,
            "flow_token": flow_token
        }
        r = await self._private_client.post("https://api.twitter.com/1.1/onboarding/begin_verification.json", headers=headers, json=body)
        r.raise_for_status()

        otp = await asyncio.to_thread(otp_handler)
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
        try:
            r = await self._private_client.post("https://api.twitter.com/1.1/onboarding/task.json", headers=headers, json=body)
            r.raise_for_status()
        except Exception:
            raise InvalidOTP

    async def edit_profile(self, name: str = "", bio: str = "", location: str = "", avatar: bytes = None):
        if avatar:
            headers = {
                "Referer": "https://twitter.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "X-Csrf-Token": self.csrf_token,
                "X-Twitter-Auth-Type": "OAuth2Session"
            }
            headers.update(self.graphql_headers)
            params = {
                "command": "INIT",
                "total_bytes": len(avatar),
                "media_type": "image/jpeg"
            }
            r = await self._private_client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers)
            r.raise_for_status()
            media_id = r.json()["media_id"]

            files = {
                "media": ("blob", avatar, "application/octet-stream")
            }
            params = {
                "command": "APPEND",
                "media_id": media_id,
                "segment_index": 0
            }
            r = await self._private_client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers, files=files)
            r.raise_for_status()

            params = {
                "command": "FINALIZE",
                "media_id": media_id,
                "original_md5": hashlib.md5(avatar).hexdigest()
            }
            r = await self._private_client.post("https://upload.twitter.com/i/media/upload.json", params=params, headers=headers)
            r.raise_for_status()

            body = {
                "include_profile_interstitial_type": "1",
                "include_blocking": "1",
                "include_blocked_by": "1",
                "include_followed_by": "1",
                "include_want_retweets": "1",
                "include_mute_edge": "1",
                "include_can_dm": "1",
                "include_can_media_tag": "1",
                "include_ext_has_nft_avatar": "1",
                "include_ext_is_blue_verified": "1",
                "include_ext_verified_type": "1",
                "include_ext_profile_image_shape": "1",
                "skip_status": "1",
                "return_user": True,
                "media_id": media_id
            }
            r = await self._private_client.post("https://api.twitter.com/1.1/account/update_profile_image.json", headers=headers, data=body)
            r.raise_for_status()

        if name or bio or location:
            headers = {
                "Referer": "https://twitter.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "X-Csrf-Token": self.csrf_token,
                "X-Twitter-Auth-Type": "OAuth2Session"
            }
            headers.update(self.graphql_headers)
            body = {
                "displayNameMaxLength": "50",
                "name": name,
                "description": bio,
                "location": location
            }
            r = await self._private_client.post("https://api.twitter.com/1.1/account/update_profile.json", headers=headers, data=body)
            r.raise_for_status()

            await self.solve_captcha()

    async def like(self, tweet_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "tweet_id": tweet_id
            },
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet", headers=headers, json=body)
        r.raise_for_status()

    async def follow(self, user_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        params = {
            "user_id": user_id
        }
        r = await self._private_client.post("https://twitter.com/i/api/1.1/friendships/create.json", headers=headers, params=params)
        r.raise_for_status()

    async def reply(self, tweet_id: int, text: str):
        headers = {
            "Referer": "https://xcom/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Transaction-Id": "XMQjF972qC24OICkSQl2sowfDR0X2Yr7OldJ0ZPALLOfljyK4NpNRIdoPMwtdhkaUYy1GV7Ire7k7qdxXg2k0lKb6PmTXw",
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
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
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "articles_preview_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "oB-5XsHNAbjvARJEc8CZFw"
        }
        r = await self._private_client.post("https://x.com/i/api/graphql/oB-5XsHNAbjvARJEc8CZFw/CreateTweet", headers=headers, json=body)
        r.raise_for_status()

    async def retweet(self, tweet_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet", headers=headers, json=body)
        r.raise_for_status()

    async def quote(self, url: str, text: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "tweet_text": text,
                "attachment_url": url,
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
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": "sgqau0P5BUJPMU_lgjpd_w"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/sgqau0P5BUJPMU_lgjpd_w/CreateTweet", headers=headers, json=body)
        r.raise_for_status()

    async def bookmark(self, tweet_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "tweet_id": tweet_id,
            },
            "queryId": "aoDbu3RHznuiSkQ9aNM67Q"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark", headers=headers, json=body)
        r.raise_for_status()

    async def vote(self, tweet_id: int, card_id: int, choice: int):
        headers = {
            "Referer": "https://twitter.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "twitter": {
                "string": {
                    "card_uri": card_id,
                    "response_card_name": "poll3choice_text_only",
                    "cards_platform": "Web-12",
                    "selected_choice": choice
                },
                "long": {
                    "original_tweet_id": tweet_id
                }
            }
        }
        r = await self._private_client.post("https://caps.twitter.com/v2/capi/passthrough/1", headers=headers, data=body)
        r.raise_for_status()

    async def watch_space(self, id: str, sleep_m: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        r = await self._private_client.get("https://twitter.com/i/api/1.1/oauth/authenticate_periscope.json", headers=headers)
        r.raise_for_status()
        r_json = r.json()
        token = r_json["token"]

        body = {
            "jwt": token,
            "vendor_id": "m5-proxsee-login-a2011357b73e",
            "create_user": False,
            "direct": True
        }
        r = await self._private_client.post("https://proxsee.pscp.tv/api/v2/loginTwitterToken", headers=headers, json=body)
        r.raise_for_status()
        r_json = r.json()
        cookie = r_json["cookie"]

        space = await self.get_space_info(id)
        media_key = space["metadata"]["media_key"]

        r = await self._private_client.get(f"https://twitter.com/i/api/1.1/live_video_stream/status/{media_key}?client=web&use_syndication_guest_id=False&cookie_set_host=twitter.com", headers=headers)
        r.raise_for_status()
        r_json = r.json()
        chat_token = r_json["chatToken"]
        life_cycle_token = r_json["lifecycleToken"]

        body = {
            "chat_token": chat_token,
            "cookie": cookie
        }
        r = await self._private_client.post("https://proxsee.pscp.tv/api/v2/twitter/accessChat", headers=headers, json=body)
        r.raise_for_status()

        body = {
            "cookie": cookie,
            "service": "guest"
        }
        r = await self._private_client.post("https://proxsee.pscp.tv/api/v2/twitter/authorizeToken", headers=headers, json=body)
        r.raise_for_status()

        body = {
            "auto_play": False,
            "cookie": cookie,
            "life_cycle_token": life_cycle_token
        }
        r = await self._private_client.post("https://proxsee.pscp.tv/api/v2/twitter/startWatching", headers=headers, json=body)
        r.raise_for_status()
        r_json = r.json()
        session = r_json["session"]

        for _ in range(sleep_m * 2):
            body = {
                "cookie": cookie,
                "session": session
            }
            r = await self._private_client.post("https://proxsee.pscp.tv/api/v2/twitter/pingWatching", headers=headers, json=body)
            r.raise_for_status()
            await asyncio.sleep(30)

    async def create_tweet(self, text: str):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
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
        r = await self._private_client.post("https://twitter.com/i/api/graphql/5V_dkq1jfalfiFOEZ4g47A/CreateTweet", headers=headers, json=body)
        r.raise_for_status()

    async def delete_tweet(self, tweet_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "VaenaVgh5q5ih7kvyVjgtg"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/VaenaVgh5q5ih7kvyVjgtg/DeleteTweet", headers=headers, json=body)
        r.raise_for_status()

    async def delete_retweet(self, tweet_id: int):
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session"
        }
        headers.update(self.graphql_headers)
        body = {
            "variables": {
                "source_tweet_id": tweet_id,
                "dark_request": False
            },
            "queryId": "iQtK4dl5hBmXewYZuEOKVw"
        }
        r = await self._private_client.post("https://twitter.com/i/api/graphql/iQtK4dl5hBmXewYZuEOKVw/DeleteRetweet", headers=headers, json=body)
        r.raise_for_status()

    def get_tweet_id(self, url: str):
        return re.search(r"\/status\/(\d+)", url).group(1)

    def get_space_id(self, url: str):
        return re.search(r"\/spaces\/([A-Za-z0-9]+)", url).group(1)

    async def get_space_info(self, space_id: str):
        headers = {
            "Referer": f"https://twitter.com/i/spaces/{space_id}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
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
        r = await self._private_client.get("https://twitter.com/i/api/graphql/MZwo_AA10ZpJfbY4ZekqQA/AudioSpaceById", headers=headers, params=params)
        r.raise_for_status()
        return r.json()["data"]["audioSpace"]

    async def get_tweet_info(self, tweet_id: int) -> Tweet:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "focalTweetId": tweet_id,
                "with_rux_injections": False,
                "includePromotedContent": True,
                "withCommunity": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withBirdwatchNotes": True,
                "withVoice": True,
                "withV2Timeline": True
            }),
            "features": json.dumps({
                "rweb_lists_timeline_redesign_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False
            }),
            "fieldToggles": json.dumps({
                "withArticleRichContentState": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/3XDB26fBve-MmjHaWTUZxA/TweetDetail", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]:
            raise TweetNotFound
        for instruction in r.json()["data"]["threaded_conversation_with_injections_v2"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return Tweet(**instruction["entries"][0]["content"]["itemContent"]["tweet_results"]["result"])

    async def get_tweet_likes(self, tweet_id: int) -> list[User]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "tweetId": tweet_id,
                "count": 20,
                "includePromotedContent": True
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/3Y3356PTjeY9RfKYULEtng/Favoriters", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["favoriters_timeline"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    User(**user["content"]["itemContent"]["user_results"]["result"])
                    for user in instruction["entries"]
                    if user["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_tweet_retweets(self, tweet_id: int) -> list[User]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "tweetId": tweet_id,
                "count": 20,
                "includePromotedContent": True
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/EvCvYif_Wh6UgW1nQunmLA/Retweeters", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["retweeters_timeline"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    User(**user["content"]["itemContent"]["user_results"]["result"])
                    for user in instruction["entries"]
                    if user["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_tweet_quotes(self, tweet_id: int) -> list[Tweet]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "rawQuery": f"quoted_tweet_id:{tweet_id}",
                "count": 20,
                "querySource": "tdqt",
                "product":" Top"
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/flaR-PUMshxFWZWPNpq4zA/SearchTimeline", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["search_by_raw_query"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    Tweet(**tweet["content"]["itemContent"]["tweet_results"]["result"])
                    for tweet in instruction["entries"]
                    if tweet["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_user_info(self, username: str) -> User:
        headers = {
            "Referer": f"https://twitter.com/{username}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "screen_name": username,
                "withSafetyModeUserFields": True
            }),
            "features": json.dumps({
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "responsive_web_twitter_article_notes_tab_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }),
            "fieldToggles": json.dumps({
                "withAuxiliaryUserLabels": False
            }),
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/k5XapwcSikNsEsILW5FvgA/UserByScreenName", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]:
            raise UserNotFound
        return User(**r.json()["data"]["user"]["result"])

    async def get_user_tweets(self, user_id: int) -> list[Tweet]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "userId": user_id,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_home_pinned_timelines_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/VgitpdpNZ-RUIp5D1Z_D-A/UserTweets", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]["user"]:
            raise TweetNotFound
        for instruction in r.json()["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    Tweet(**tweet["content"]["itemContent"]["tweet_results"]["result"])
                    for tweet in instruction["entries"]
                    if tweet["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_user_followers(self, user_id: int) -> list[User]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "userId": user_id,
                "count": 20,
                "includePromotedContent": False
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/Uc7ZOJrxsJAzMVCcaxis8Q/Followers", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    User(**user["content"]["itemContent"]["user_results"]["result"])
                    for user in instruction["entries"]
                    if user["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_user_following(self, user_id: int) -> list[User]:
        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Csrf-Token": self.csrf_token,
            "X-Twitter-Auth-Type": "OAuth2Session",
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "userId": user_id,
                "count": 20,
                "includePromotedContent": False
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._private_client.get("https://twitter.com/i/api/graphql/PiHWpObvX9tbClrUl6rL9g/Following", headers=headers, params=params)
        r.raise_for_status()
        for instruction in r.json()["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [
                    User(**user["content"]["itemContent"]["user_results"]["result"])
                    for user in instruction["entries"]
                    if user["content"]["entryType"] == "TimelineTimelineItem"
                ]

    async def get_space_info_public(self, space_id: str):
        if not self.guest_token:
            await self._refresh_guest_token()

        headers = {
            "Referer": f"https://twitter.com/i/spaces/{space_id}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Guest-Token": self.guest_token
        }
        headers.update(self.graphql_headers)
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
        r = await self._public_client.get("https://twitter.com/i/api/graphql/MZwo_AA10ZpJfbY4ZekqQA/AudioSpaceById", headers=headers, params=params)
        r.raise_for_status()
        return r.json()["data"]["audioSpace"]

    async def get_user_info_public(self, username: str) -> User:
        if not self.guest_token:
            await self._refresh_guest_token()

        headers = {
            "Referer": f"https://twitter.com/{username}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Guest-Token": self.guest_token
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "screen_name": username,
                "withSafetyModeUserFields": True
            }),
            "features": json.dumps({
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "responsive_web_twitter_article_notes_tab_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }),
            "fieldToggles": json.dumps({
                "withAuxiliaryUserLabels": False
            }),
        }
        r = await self._public_client.get("https://api.twitter.com/graphql/k5XapwcSikNsEsILW5FvgA/UserByScreenName", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]:
            raise UserNotFound
        return User(**r.json()["data"]["user"]["result"])

    async def get_user_tweets_public(self, user_id) -> list[Tweet]:
        if not self.guest_token:
            await self._refresh_guest_token()

        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Guest-Token": self.guest_token
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "userId": user_id,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            }),
            "features": json.dumps({
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_enhance_cards_enabled": False
            })
        }
        r = await self._public_client.get("https://api.twitter.com/graphql/eS7LO5Jy3xgmd3dbL044EA/UserTweets", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]["user"]:
            raise TweetNotFound
        for instruction in r.json()["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]:
            if instruction["type"] == "TimelineAddEntries":
                return [Tweet(**tweet["content"]["itemContent"]["tweet_results"]["result"]) for tweet in instruction["entries"]]

    async def get_tweet_info_public(self, tweet_id: int) -> Tweet:
        if not self.guest_token:
            await self._refresh_guest_token()

        headers = {
            "Referer": "https://twitter.com/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Guest-Token": self.guest_token
        }
        headers.update(self.graphql_headers)
        params = {
            "variables": json.dumps({
                "tweetId": tweet_id,
                "withCommunity": False,
                "includePromotedContent": False,
                "withVoice": False
            }),
            "features": json.dumps({
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
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
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }),
            "fieldToggles": json.dumps({
                "withArticleRichContentState": False
            })
        }
        r = await self._public_client.get("https://api.twitter.com/graphql/OUKdeWm3g4tDbW5hffX_QA/TweetResultByRestId", headers=headers, params=params)
        r.raise_for_status()
        if not r.json()["data"]["tweetResult"]:
            raise TweetNotFound
        return Tweet(**r.json()["data"]["tweetResult"]["result"])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._private_client.aclose()
        await self._public_client.aclose()
