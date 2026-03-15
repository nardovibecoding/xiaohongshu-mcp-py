"""MCP tool definitions — 13 tools matching the Go implementation."""

from mcp.server.fastmcp import FastMCP

from models import FilterOption
from cookie_manager import delete_cookies as _delete_cookies, get_cookie_path
from xhs_actions.login import check_login_status as _check_login, get_login_qrcode as _get_qrcode
from xhs_actions.feeds import list_feeds as _list_feeds
from xhs_actions.search import search_feeds as _search_feeds
from xhs_actions.feed_detail import get_feed_detail as _get_feed_detail
from xhs_actions.user_profile import user_profile as _user_profile
from xhs_actions.like_favorite import like_feed as _like_feed, favorite_feed as _favorite_feed
from xhs_actions.comment import post_comment as _post_comment, reply_comment as _reply_comment
from xhs_actions.publish_image import publish_content as _publish_content
from xhs_actions.publish_video import publish_with_video as _publish_video

mcp = FastMCP("xiaohongshu")


@mcp.tool()
async def check_login_status() -> dict:
    """Check WeChat login status."""
    return await _check_login()


@mcp.tool()
async def get_login_qrcode() -> dict:
    """Get QR code for login (Base64 image + timeout)."""
    return await _get_qrcode()


@mcp.tool()
async def delete_cookies() -> dict:
    """Delete cookies file to reset login status."""
    path = _delete_cookies()
    return {"cookie_path": path, "message": "Cookies deleted"}


@mcp.tool()
async def list_feeds() -> dict:
    """Get homepage Feeds list."""
    return await _list_feeds()


@mcp.tool()
async def search_feeds(keyword: str, sort_by: str = "综合",
                        note_type: str = "不限", publish_time: str = "不限",
                        search_scope: str = "不限", location: str = "不限") -> dict:
    """Search Xiaohongshu content (requires login).

    Args:
        keyword: Search keyword
        sort_by: 综合|最新|最多点赞|最多评论|最多收藏
        note_type: 不限|视频|图文
        publish_time: 不限|一天内|一周内|半年内
        search_scope: 不限|已看过|未看过|已关注
        location: 不限|同城|附近
    """
    filters = FilterOption(
        sort_by=sort_by, note_type=note_type, publish_time=publish_time,
        search_scope=search_scope, location=location,
    )
    return await _search_feeds(keyword, filters)


@mcp.tool()
async def get_feed_detail(feed_id: str, xsec_token: str,
                           load_all_comments: bool = False,
                           limit: int = 20,
                           click_more_replies: bool = False,
                           reply_limit: int = 10,
                           scroll_speed: str = "normal") -> dict:
    """Get feed detail with comments.

    Args:
        feed_id: Note ID
        xsec_token: Access token from feed list
        load_all_comments: Load all comments (default: false, loads ~10)
        limit: Max comments to load (default: 20)
        click_more_replies: Expand sub-comment replies
        reply_limit: Skip comments with > N replies (default: 10)
        scroll_speed: slow|normal|fast
    """
    return await _get_feed_detail(feed_id, xsec_token, load_all_comments,
                                   limit, click_more_replies, reply_limit, scroll_speed)


@mcp.tool()
async def user_profile(user_id: str, xsec_token: str) -> dict:
    """Get user profile (basic info, followers, likes, posts).

    Args:
        user_id: User ID from feed list
        xsec_token: Access token
    """
    return await _user_profile(user_id, xsec_token)


@mcp.tool()
async def like_feed(feed_id: str, xsec_token: str, unlike: bool = False) -> dict:
    """Like or unlike a feed (smart: skips if already in target state).

    Args:
        feed_id: Note ID
        xsec_token: Access token
        unlike: true = unlike, false = like
    """
    return await _like_feed(feed_id, xsec_token, unlike)


@mcp.tool()
async def favorite_feed(feed_id: str, xsec_token: str, unfavorite: bool = False) -> dict:
    """Favorite or unfavorite a feed (smart: skips if already in target state).

    Args:
        feed_id: Note ID
        xsec_token: Access token
        unfavorite: true = unfavorite, false = favorite
    """
    return await _favorite_feed(feed_id, xsec_token, unfavorite)


@mcp.tool()
async def post_comment_to_feed(feed_id: str, xsec_token: str, content: str) -> dict:
    """Post a comment on a feed.

    Args:
        feed_id: Note ID
        xsec_token: Access token
        content: Comment text
    """
    return await _post_comment(feed_id, xsec_token, content)


@mcp.tool()
async def reply_comment_in_feed(feed_id: str, xsec_token: str, content: str,
                                  comment_id: str = "", user_id: str = "") -> dict:
    """Reply to a specific comment on a feed.

    Args:
        feed_id: Note ID
        xsec_token: Access token
        content: Reply text
        comment_id: Target comment ID (optional if user_id provided)
        user_id: Target user ID (optional if comment_id provided)
    """
    return await _reply_comment(feed_id, xsec_token, content, comment_id, user_id)


@mcp.tool()
async def publish_content(title: str, content: str, images: list[str],
                           tags: list[str] = None, schedule_at: str = "",
                           is_original: bool = False, visibility: str = "",
                           products: list[str] = None) -> dict:
    """Publish Xiaohongshu image content.

    Args:
        title: Post title (max 20 Chinese chars)
        content: Post text content
        images: List of image URLs or local paths (min 1)
        tags: Hashtag list
        schedule_at: ISO8601 scheduled time (1h to 14d from now)
        is_original: Declare as original content
        visibility: 公开可见|仅自己可见|仅互关好友可见
        products: Product keywords for affiliate links
    """
    return await _publish_content(title, content, images, tags, schedule_at,
                                   is_original, visibility, products)


@mcp.tool()
async def publish_with_video(title: str, content: str, video: str,
                              tags: list[str] = None, schedule_at: str = "",
                              visibility: str = "", products: list[str] = None) -> dict:
    """Publish video content (local file only).

    Args:
        title: Post title (max 20 Chinese chars)
        content: Post text content
        video: Local video file absolute path
        tags: Hashtag list
        schedule_at: ISO8601 scheduled time
        visibility: 公开可见|仅自己可见|仅互关好友可见
        products: Product keywords for affiliate links
    """
    return await _publish_video(title, content, video, tags, schedule_at,
                                 visibility, products)
