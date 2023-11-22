from pydantic import BaseModel, Field, AliasPath


class User(BaseModel):
    id: str = Field(validation_alias=AliasPath("rest_id"))
    name: str = Field(validation_alias=AliasPath("legacy", "name"))
    username: str = Field(validation_alias=AliasPath("legacy", "screen_name"))
    followers_count: int = Field(validation_alias=AliasPath("legacy", "followers_count"))
    following_count: int = Field(validation_alias=AliasPath("legacy", "friends_count"))

class Tweet(BaseModel):
    id: str = Field(None, validation_alias=AliasPath("content", "itemContent", "tweet_results", "result", "rest_id"))
    views_count: str = Field(None, validation_alias=AliasPath("content", "itemContent", "tweet_results", "result", "views", "count"))
    retweets_count: int = Field(None, validation_alias=AliasPath("content", "itemContent", "tweet_results", "result", "legacy", "retweet_count"))
    likes_count: int = Field(None, validation_alias=AliasPath("content", "itemContent", "tweet_results", "result", "legacy", "favorite_count"))
    replies_count: int = Field(None, validation_alias=AliasPath("content", "itemContent", "tweet_results", "result", "legacy", "reply_count"))
