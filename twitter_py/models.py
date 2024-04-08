from pydantic import BaseModel, Field, AliasPath, AliasChoices


class User(BaseModel):
    id: str = Field(validation_alias=AliasPath("rest_id"))
    name: str = Field(validation_alias=AliasPath("legacy", "name"))
    username: str = Field(validation_alias=AliasPath("legacy", "screen_name"))
    followers_count: int = Field(validation_alias=AliasPath("legacy", "followers_count"))
    following_count: int = Field(validation_alias=AliasPath("legacy", "friends_count"))

class Tweet(BaseModel):
    id: str = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("rest_id"),
            AliasPath("tweet", "rest_id"),
            AliasPath("legacy", "retweeted_status_result", "result", "rest_id"),
            AliasPath("tweet", "legacy", "retweeted_status_result", "result", "rest_id")
        ))
    card_id: str = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("card", "rest_id"),
            AliasPath("tweet", "card", "rest_id")
        )
    )
    bookmark_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("legacy", "bookmark_count"),
            AliasPath("tweet", "legacy", "bookmark_count")
        )
    )
    like_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("legacy", "favorite_count"),
            AliasPath("tweet", "legacy", "favorite_count")
        )
    )
    reply_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("legacy", "reply_count"),
            AliasPath("tweet", "legacy", "reply_count")
        )
    )
    retweet_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("legacy", "retweet_count"),
            AliasPath("tweet", "legacy", "retweet_count")
        )
    )
    quote_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("legacy", "quote_count"),
            AliasPath("tweet", "legacy", "quote_count")
        )
    )
    views_count: int = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("views", "count"),
            AliasPath("tweet", "views", "count")
        )
    )
