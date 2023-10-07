import httpx
import json
import re
import secrets
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import urllib.parse
import capsolver
import hashlib


class Twitter:
    def __init__(self, proxy: str = None, capsolver_api_key: str = None):
        self._capsolver_api_key = capsolver_api_key
        self._client = httpx.Client(proxies=f"http://{proxy}" if proxy else None)
        csrf_token = "".join([hex(x)[-1] for x in secrets.token_bytes(32)])
        ua = UserAgent()
        self._client.headers.update({
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "X-Csrf-Token": csrf_token,
            "User-Agent": ua.chrome,
        })
        self._client.cookies.update({
            "ct0": csrf_token
        })

    def _get_user_id(self, username: str):
        params = {
            "variables": json.dumps({
                "screen_name": username,
                "withSafetyModeUserFields": True
            }),
            "features": json.dumps({
                "hidden_profile_likes_enabled": False,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": False,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }),
            "fieldToggles": json.dumps({
                "withAuxiliaryUserLabels": False
            }),
        }
        r = self._client.get("https://twitter.com/i/api/graphql/SAMkL5y_N9pmahSw8yy6gw/UserByScreenName", params=params)
        r.raise_for_status()
        return r.json()["data"]["user"]["result"]["rest_id"]

    def _get_tweet_id(self, url: str):
        return re.search(r"\/status\/(\d+)", url).group(1)

    def login(self, auth_token: str):
        self._client.cookies.update({
            "auth_token": auth_token
        })

    def solve_captcha(self):
        headers = {
            "Authorization": "",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        r = self._client.get("https://twitter.com/account/access", headers=headers, follow_redirects=True)
        if "access" in str(r.url):
            soup = BeautifulSoup(r.text, "html.parser")
            authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
            assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")

            headers.update({
                "Referer": "https://twitter.com/account/access",
                "Content-Type": "application/x-www-form-urlencoded"
            })

            if not soup.find("form", {"id": "arkose_form"}):
                body = f"authenticity_token={authenticity_token}&assignment_token={assignment_token}&lang=en&flow="
                r = self._client.post("https://twitter.com/account/access", headers=headers, data=body)
                soup = BeautifulSoup(r.text, "html.parser")
                authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
                assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")

            for _ in range(3):
                capsolver.api_key = self._capsolver_api_key
                token = capsolver.solve({
                    "type": "FunCaptchaTaskProxyLess",
                    "websitePublicKey": "0152B4EB-D2DC-460A-89A1-629838B529C9",
                    "websiteURL": "https://twitter.com/account/access",
                })["token"]
                body = f"authenticity_token={authenticity_token}&assignment_token={assignment_token}&lang=en&flow=&verification_string={urllib.parse.quote(token)}&language_code=en"
                r = self._client.post("https://twitter.com/account/access?lang=en", headers=headers, data=body)
                soup = BeautifulSoup(r.text, "html.parser")
                if not soup.find("form", {"id": "arkose_form"}):
                    break
                authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")
                assignment_token = soup.find("input", {"name": "assignment_token"}).get("value")
            else:
                raise Exception("Failed to solve captcha")

            body = f"authenticity_token={authenticity_token}&assignment_token={assignment_token}&lang=en&flow="
            r = self._client.post("https://twitter.com/account/access?lang=en", headers=headers, data=body)

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
            body = f"include_profile_interstitial_type=1&include_blocking=1&include_blocked_by=1&include_followed_by=1&include_want_retweets=1&include_mute_edge=1&include_can_dm=1&include_can_media_tag=1&include_ext_has_nft_avatar=1&include_ext_is_blue_verified=1&include_ext_verified_type=1&include_ext_profile_image_shape=1&skip_status=1&return_user=true&media_id={media_id}"
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

    def tweet(self, url: str, text: str):
        body = {
            "variables": {
                "tweet_text": text,
                "reply": {
                    "in_reply_to_tweet_id": self._get_tweet_id(url),
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
        self._client.post("https://twitter.com/i/api/graphql/SoVnbfCycZ7fERGCwpZkYA/CreateTweet", json=body).raise_for_status()

    def retweet(self, url: str):
        body = {
            "variables": {
                "tweet_id": self._get_tweet_id(url),
                "dark_request": False
            },
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        }
        self._client.post("https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet", json=body).raise_for_status()

    def like_tweet(self, url: str):
        body = {
            "variables": {
                "tweet_id": self._get_tweet_id(url)
            },
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        }
        self._client.post("https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet", json=body).raise_for_status()

    def follow_user(self, username: str):
        params = {
            "user_id": self._get_user_id(username)
        }
        self._client.post("https://twitter.com/i/api/1.1/friendships/create.json", params=params).raise_for_status()

    def get_tweet(self, url: str):
        params = {
            "variables": json.dumps({
                "focalTweetId": self._get_tweet_id(url),
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
        r = self._client.get("https://twitter.com/i/api/graphql/3XDB26fBve-MmjHaWTUZxA/TweetDetail", params=params)
        data = r.json()
        if r.status_code != 200 or "errors" in data:
            raise Exception(data["errors"][0]["message"])
        entries = data["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"]
        tweets = []
        for entry in entries:
            if "tweet" in entry["entryId"]:
                try:
                    try:
                        data_legacy = entry["content"]["itemContent"]["tweet_results"]["result"]["legacy"]
                    except KeyError:
                        data_legacy = entry["content"]["itemContent"]["tweet_results"]["result"]["tweet"]["legacy"]
                except KeyError:
                    continue
                for tweet in data_legacy["extended_entities"]["media"]:
                    if tweet["type"] == "photo":
                        tweets.append({"Type": "image", "media": tweet["media_url_https"], "thumbnail": tweet["media_url_https"]})
                    elif tweet["type"] == "video" or tweet["type"] == "animated_gif":
                        for video in sorted(tweet["video_info"]["variants"], key=lambda x: x.get("bitrate", 0), reverse=True):
                            if video["content_type"] == "video/mp4":
                                tweets.append({"Type": "video", "media": video["url"], "thumbnail": tweet["media_url_https"]})
                                break
        return {"media": tweets, "possibly_sensitive": data_legacy["possibly_sensitive"]}

    def signup(self):
        email = "icucoaoosus@hldrive.com"
        password = "zarazrazraz@@131"

        headers = {
            "X-Guest-Token": "1710641940763480275"
        }

        body = {
            "input_flow_data": {
                "requested_variant": "{\"signup_type\":\"phone_email\"}",
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {
                        "location": "unknown"
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
            "display_name": "Mehdi",
            "flow_token": flow_token
        }
        r = self._client.post("https://api.twitter.com/1.1/onboarding/begin_verification.json", headers=headers, json=body)
        r.raise_for_status()

        otp = input("OTP: ")
        capsolver.api_key = self._capsolver_api_key
        token = capsolver.solve({
            "type": "FunCaptchaTaskProxyLess",
            "websitePublicKey": "2CB16598-CB82-4CF7-B332-5990DB66F3AB",
            "websiteURL": "https://twitter.com/i/flow/signup",
        })["token"]
        body = {
            "flow_token": flow_token,
            "subtask_inputs": [
                {
                    "subtask_id": "Signup",
                    "sign_up": {
                        "js_instrumentation": {
                            "response": "{\"rf\":{\"aec29a33abb6d501d849f8764f07a717f2a1af91b4016a54ddff27d61ad12904\":0,\"b284d610ea4a6c28fcf9d8f080dc620d47e95e0f52ef0e59474f6565fec72c16\":73,\"a795edb67b41a593988756fa347d1d8ea229b930fef131d1d485604b2b413f61\":-1,\"a9c47edacfa61fa4ea26d89720ca8f51da1a70192b4495bb773e06028025700e\":0},\"s\":\"GkcsR5JHI7K9v_BviYnQEZN89MfKyxK-RjMoYCrqqjbLZlrVqxe50K98KKIKjiTQxPN8I32yVs5sAiLDUYLpV-My7h8qa9azG1zYckUaga-f4jkuQdyDzBvgxNHH4aKMC9nsJ0w794xqBTHA5c-ocreDWYWuwUWSXchHdp9HtAdQzCVQY4JrucVggxZZVphm1HCbi7ylqyvXa4Tp0SfOBYsu1ZzAYvaSux2q_dteHW26uoWrjhlBdBJGzSoSovw4TMbTJRMo0MiFUhBWlKw2HMJdlt3eBxaPdbPBVySyAagWbEwjQOt6rYgeCnj9ukS7-i2xBbufkH8KbA_-SOW_qwAAAYsKCiZW\"}"
                        },
                        "link": "email_next_link",
                        "name": "Mehdi",
                        "email": email,
                        "birthday": {
                            "day": 8,
                            "month": 5,
                            "year": 2003
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
        print(r.text)
        print(r.cookies)
