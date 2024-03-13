from pydantic import BaseModel, Field, AliasPath


class User(BaseModel):
    id: str = Field(validation_alias=AliasPath("rest_id"))
    name: str = Field(validation_alias=AliasPath("legacy", "name"))
    username: str = Field(validation_alias=AliasPath("legacy", "screen_name"))
    followers_count: int = Field(validation_alias=AliasPath("legacy", "followers_count"))
    following_count: int = Field(validation_alias=AliasPath("legacy", "friends_count"))

class Tweet(BaseModel):
    id: str = Field(None, validation_alias=AliasPath("rest_id"))
    bookmark_count: int = Field(None, validation_alias=AliasPath("legacy", "bookmark_count"))
    favorite_count: int = Field(None, validation_alias=AliasPath("legacy", "favorite_count"))
    reply_count: int = Field(None, validation_alias=AliasPath("legacy", "reply_count"))
    retweet_count: int = Field(None, validation_alias=AliasPath("legacy", "retweet_count"))
    retweet_id: str = Field(None, validation_alias=AliasPath("legacy", "retweeted_status_result", "result", "rest_id"))
