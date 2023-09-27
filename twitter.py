import httpx
import json
import re
import secrets


class Twitter:
    def __init__(self, auth_token: str, proxy: str = None):
        self.client = httpx.Client(proxies=f"http://{proxy}" if proxy else None)
        csrf_token = "".join([hex(x)[-1] for x in secrets.token_bytes(32)])
        self.client.headers.update({
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "X-Csrf-Token": csrf_token
        })
        self.client.cookies.update({
            "auth_token": auth_token,
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
        r = self.client.get("https://twitter.com/i/api/graphql/SAMkL5y_N9pmahSw8yy6gw/UserByScreenName", params=params)
        r.raise_for_status()
        return r.json()["data"]["user"]["result"]["rest_id"]

    def _get_tweet_id(self, url: str):
        return re.search(r"\/status\/(\d+)", url).group(1)

    def tweet(self, url: str, text: str):
        json = {
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
        self.client.post("https://twitter.com/i/api/graphql/SoVnbfCycZ7fERGCwpZkYA/CreateTweet", json=json).raise_for_status()

    def retweet(self, url: str):
        json = {
            "variables": {
                "tweet_id": self._get_tweet_id(url),
                "dark_request": False
            },
            "queryId": "ojPdsZsimiJrUGLR1sjUtA"
        }
        self.client.post("https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet", json=json).raise_for_status()

    def like_tweet(self, url: str):
        json = {
            "variables": {
                "tweet_id": self._get_tweet_id(url)
            },
            "queryId": "lI07N6Otwv1PhnEgXILM7A"
        }
        self.client.post("https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet", json=json).raise_for_status()

    def follow_user(self, username: str):
        self.client.post("https://twitter.com/i/api/1.1/friendships/create.json", params={"user_id": self._get_user_id(username)}).raise_for_status()

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
        r = self.client.get("https://twitter.com/i/api/graphql/3XDB26fBve-MmjHaWTUZxA/TweetDetail", params=params)
        data = r.json()
        if r.status_code != 200 or "errors" in data:
            raise Exception(data["errors"][0]["message"])
        entries = data["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"]
        print(entries)
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
