# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Pydantic models for XHS MCP server."""

from typing import Optional
from pydantic import BaseModel, Field


class NoteCard(BaseModel):
    note_id: str = ""
    xsec_token: str = ""
    title: str = ""
    description: str = ""
    type: str = ""
    liked_count: str = ""
    cover_url: str = ""
    author_id: str = ""
    author_name: str = ""
    author_avatar: str = ""


class FeedListResponse(BaseModel):
    feeds: list[NoteCard] = []
    count: int = 0


class LoginStatusResponse(BaseModel):
    is_logged_in: bool = False
    username: str = ""


class QrcodeResponse(BaseModel):
    timeout: str = "0s"
    is_logged_in: bool = False
    img: str = ""


class DeleteCookiesResponse(BaseModel):
    cookie_path: str = ""
    message: str = ""


class FilterOption(BaseModel):
    sort_by: str = Field(default="综合", description='综合|最新|最多点赞|最多评论|最多收藏')
    note_type: str = Field(default="不限", description='不限|视频|图文')
    publish_time: str = Field(default="不限", description='不限|一天内|一周内|半年内')
    search_scope: str = Field(default="不限", description='不限|已看过|未看过|已关注')
    location: str = Field(default="不限", description='不限|同城|附近')


class SearchFeedsArgs(BaseModel):
    keyword: str
    filters: Optional[FilterOption] = None


class FeedDetailArgs(BaseModel):
    feed_id: str
    xsec_token: str
    load_all_comments: bool = False
    limit: int = 20
    click_more_replies: bool = False
    reply_limit: int = 10
    scroll_speed: str = "normal"


class UserProfileArgs(BaseModel):
    user_id: str
    xsec_token: str


class PostCommentArgs(BaseModel):
    feed_id: str
    xsec_token: str
    content: str


class ReplyCommentArgs(BaseModel):
    feed_id: str
    xsec_token: str
    content: str
    comment_id: str = ""
    user_id: str = ""


class LikeFeedArgs(BaseModel):
    feed_id: str
    xsec_token: str
    unlike: bool = False


class FavoriteFeedArgs(BaseModel):
    feed_id: str
    xsec_token: str
    unfavorite: bool = False


class PublishContentArgs(BaseModel):
    title: str
    content: str
    images: list[str]
    tags: list[str] = []
    schedule_at: str = ""
    is_original: bool = False
    visibility: str = ""
    products: list[str] = []


class PublishVideoArgs(BaseModel):
    title: str
    content: str
    video: str
    tags: list[str] = []
    schedule_at: str = ""
    visibility: str = ""
    products: list[str] = []
