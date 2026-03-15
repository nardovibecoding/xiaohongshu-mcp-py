"""FastAPI REST API routes — 14 endpoints matching Go implementation."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models import (
    SearchFeedsArgs, FeedDetailArgs, UserProfileArgs,
    PostCommentArgs, ReplyCommentArgs, LikeFeedArgs, FavoriteFeedArgs,
    PublishContentArgs, PublishVideoArgs, FilterOption,
)
from cookie_manager import delete_cookies as _delete_cookies, get_cookie_path
from xhs_actions.login import check_login_status, get_login_qrcode
from xhs_actions.feeds import list_feeds
from xhs_actions.search import search_feeds
from xhs_actions.feed_detail import get_feed_detail
from xhs_actions.user_profile import user_profile
from xhs_actions.like_favorite import like_feed, favorite_feed
from xhs_actions.comment import post_comment, reply_comment
from xhs_actions.publish_image import publish_content
from xhs_actions.publish_video import publish_with_video

router = APIRouter(prefix="/api/v1")


def _ok(data: dict) -> JSONResponse:
    return JSONResponse({"code": 0, "data": data})


def _err(msg: str, code: int = 500) -> JSONResponse:
    return JSONResponse({"code": code, "message": msg}, status_code=code)


# --- Login ---

@router.get("/login/status")
async def login_status_handler():
    try:
        result = await check_login_status()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.get("/login/qrcode")
async def login_qrcode_handler():
    try:
        result = await get_login_qrcode()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.delete("/login/cookies")
async def delete_cookies_handler():
    try:
        path = _delete_cookies()
        return _ok({"cookie_path": path, "message": "Cookies deleted"})
    except Exception as e:
        return _err(str(e))


# --- Feeds ---

@router.get("/feeds/list")
async def list_feeds_handler():
    try:
        result = await list_feeds()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.get("/feeds/search")
@router.post("/feeds/search")
async def search_feeds_handler(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
        else:
            body = dict(request.query_params)

        keyword = body.get("keyword", "")
        if not keyword:
            return _err("keyword is required", 400)

        filters_data = body.get("filters")
        filters = FilterOption(**filters_data) if filters_data else None

        result = await search_feeds(keyword, filters)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.post("/feeds/detail")
async def feed_detail_handler(request: Request):
    try:
        body = await request.json()
        args = FeedDetailArgs(**body)
        result = await get_feed_detail(
            args.feed_id, args.xsec_token, args.load_all_comments,
            args.limit, args.click_more_replies, args.reply_limit, args.scroll_speed,
        )
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# --- User ---

@router.post("/user/profile")
async def user_profile_handler(request: Request):
    try:
        body = await request.json()
        args = UserProfileArgs(**body)
        result = await user_profile(args.user_id, args.xsec_token)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.get("/user/me")
async def my_profile_handler():
    """Get current logged-in user's profile."""
    try:
        login = await check_login_status()
        if not login.get("is_logged_in"):
            return _err("Not logged in", 401)
        return _ok(login)
    except Exception as e:
        return _err(str(e))


# --- Interactions ---

@router.post("/feeds/comment")
async def post_comment_handler(request: Request):
    try:
        body = await request.json()
        args = PostCommentArgs(**body)
        result = await post_comment(args.feed_id, args.xsec_token, args.content)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.post("/feeds/comment/reply")
async def reply_comment_handler(request: Request):
    try:
        body = await request.json()
        args = ReplyCommentArgs(**body)
        result = await reply_comment(
            args.feed_id, args.xsec_token, args.content,
            args.comment_id, args.user_id,
        )
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.post("/feeds/like")
async def like_feed_handler(request: Request):
    try:
        body = await request.json()
        args = LikeFeedArgs(**body)
        result = await like_feed(args.feed_id, args.xsec_token, args.unlike)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.post("/feeds/favorite")
async def favorite_feed_handler(request: Request):
    try:
        body = await request.json()
        args = FavoriteFeedArgs(**body)
        result = await favorite_feed(args.feed_id, args.xsec_token, args.unfavorite)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# --- Publishing ---

@router.post("/publish")
async def publish_handler(request: Request):
    try:
        body = await request.json()
        args = PublishContentArgs(**body)
        result = await publish_content(
            args.title, args.content, args.images, args.tags,
            args.schedule_at, args.is_original, args.visibility, args.products,
        )
        return _ok(result)
    except Exception as e:
        return _err(str(e))


@router.post("/publish_video")
async def publish_video_handler(request: Request):
    try:
        body = await request.json()
        args = PublishVideoArgs(**body)
        result = await publish_with_video(
            args.title, args.content, args.video, args.tags,
            args.schedule_at, args.visibility, args.products,
        )
        return _ok(result)
    except Exception as e:
        return _err(str(e))
