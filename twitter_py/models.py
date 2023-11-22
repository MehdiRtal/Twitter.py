from pydantic import BaseModel, Field, AliasPath, AliasChoices


class User(BaseModel):
    id: str = Field(validation_alias=AliasPath("rest_id"))
    name: str = Field(validation_alias=AliasPath("legacy", "name"))
    username: str = Field(validation_alias=AliasPath("legacy", "screen_name"))
    followers_count: int = Field(validation_alias=AliasPath("legacy", "followers_count"))
    following_count: int = Field(validation_alias=AliasPath("legacy", "friends_count"))

class Tweet(BaseModel):
    id: str = Field(None, validation_alias=AliasChoices(AliasPath("content", "itemContent", "tweet_results", "result", "rest_id"), AliasPath("content", "itemContent", "tweet_results", "result", "tweet", "rest_id")))
    retweet_id: str = Field(None, validation_alias=AliasChoices(AliasPath("content", "itemContent", "tweet_results", "result", "legacy", "retweeted_status_result", "result", "rest_id"), AliasPath("content", "itemContent", "tweet_results", "result", "tweet", "legacy", "retweeted_status_result", "result", "rest_id")))
