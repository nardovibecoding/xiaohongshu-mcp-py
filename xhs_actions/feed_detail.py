"""Get feed detail with comments."""

import json
import logging
from patchright.async_api import Page

from browser_manager import get_browser
from utils import extract_initial_state, sleep_random, safe_close_page

logger = logging.getLogger("xhs.feed_detail")

DETAIL_URL = "https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}"


def _parse_detail(detail_map: dict, feed_id: str) -> dict:
    """Parse note detail from __INITIAL_STATE__.note.noteDetailMap."""
    # The map is keyed by note ID
    entry = detail_map.get(feed_id, {})
    note = entry.get("note") or entry
    if not note:
        return {}

    user = note.get("user") or {}
    interact_info = note.get("interactInfo") or {}
    image_list = note.get("imageList") or []
    tag_list = note.get("tagList") or []
    video = note.get("video") or {}

    return {
        "note_id": note.get("noteId") or note.get("note_id") or feed_id,
        "title": note.get("title") or "",
        "description": note.get("desc") or "",
        "type": note.get("type") or "",
        "ip_location": note.get("ipLocation") or "",
        "time": note.get("time") or "",
        "last_update_time": note.get("lastUpdateTime") or "",
        "liked_count": interact_info.get("likedCount") or "0",
        "collected_count": interact_info.get("collectedCount") or "0",
        "comment_count": interact_info.get("commentCount") or "0",
        "share_count": interact_info.get("shareCount") or "0",
        "liked": interact_info.get("liked", False),
        "collected": interact_info.get("collected", False),
        "images": [
            {
                "url": img.get("urlDefault") or img.get("url") or "",
                "width": img.get("width") or 0,
                "height": img.get("height") or 0,
            }
            for img in image_list
        ],
        "tags": [
            {"id": t.get("id", ""), "name": t.get("name", "")}
            for t in tag_list
        ],
        "video_url": video.get("media", {}).get("stream", {}).get("h264", [{}])[0].get("masterUrl", "") if video else "",
        "author": {
            "user_id": user.get("userId") or "",
            "nickname": user.get("nickname") or "",
            "avatar": user.get("avatar") or "",
        },
    }


async def _load_comments(page: Page, load_all: bool, limit: int,
                          click_more_replies: bool, reply_limit: int,
                          scroll_speed: str) -> list[dict]:
    """Load comments from the feed detail page by scrolling."""
    comments = []

    # Speed mapping
    speed_delay = {"slow": 1.5, "normal": 0.8, "fast": 0.3}.get(scroll_speed, 0.8)

    try:
        # Wait for comments section
        await page.wait_for_selector(".comments-container, .comment-list", timeout=5000)
    except Exception:
        logger.debug("No comments container found")
        return comments

    last_count = 0
    stagnant = 0
    attempts = 0
    max_attempts = 100 if load_all else 5

    while attempts < max_attempts:
        attempts += 1

        # Extract current comments via JS
        raw = await page.evaluate("""() => {
            const comments = [];
            document.querySelectorAll('.parent-comment, .comment-item-wrap').forEach(el => {
                const userEl = el.querySelector('.author-wrapper .name, .user-name');
                const contentEl = el.querySelector('.note-text, .content');
                const likeEl = el.querySelector('.like-count, .count');
                const idAttr = el.getAttribute('data-comment-id') || el.id || '';

                if (contentEl) {
                    const subComments = [];
                    el.querySelectorAll('.reply-item, .sub-comment-item').forEach(sub => {
                        const subUser = sub.querySelector('.author-wrapper .name, .user-name');
                        const subContent = sub.querySelector('.note-text, .content');
                        const subLike = sub.querySelector('.like-count, .count');
                        if (subContent) {
                            subComments.push({
                                user: subUser ? subUser.textContent.trim() : '',
                                content: subContent.textContent.trim(),
                                likes: subLike ? subLike.textContent.trim() : '0',
                            });
                        }
                    });

                    comments.push({
                        id: idAttr,
                        user: userEl ? userEl.textContent.trim() : '',
                        content: contentEl.textContent.trim(),
                        likes: likeEl ? likeEl.textContent.trim() : '0',
                        replies: subComments,
                    });
                }
            });
            return JSON.stringify(comments);
        }""")

        try:
            current = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            current = []

        if len(current) >= limit:
            comments = current[:limit]
            break

        if len(current) == last_count:
            stagnant += 1
            if stagnant >= 10:
                break
        else:
            stagnant = 0
        last_count = len(current)

        if not load_all and attempts >= 3:
            comments = current
            break

        # Click "more replies" if requested
        if click_more_replies:
            try:
                more_btns = await page.query_selector_all('.show-more-reply, .expand-reply, [class*="more-reply"]')
                for btn in more_btns:
                    try:
                        await btn.click()
                        await sleep_random(0.3, 0.5)
                    except Exception:
                        pass
            except Exception:
                pass

        # Scroll down to load more
        await page.evaluate("window.scrollBy(0, 500)")
        await sleep_random(speed_delay * 0.8, speed_delay * 1.2)

        comments = current

    # Check end container
    try:
        end = await page.query_selector('.comments-end, .no-more-comments')
        if end:
            logger.debug("Reached end of comments")
    except Exception:
        pass

    return comments[:limit]


async def _extract_detail_from_dom(page: Page, feed_id: str) -> dict:
    """Extract note detail directly from DOM elements."""
    result = await page.evaluate("""(feedId) => {
        const detail = { note_id: feedId };

        // Title
        const titleEl = document.querySelector('#detail-title, .title, [class*="note-title"]');
        detail.title = titleEl ? titleEl.textContent.trim() : document.title.split(' - ')[0] || '';

        // Description
        const descEl = document.querySelector('#detail-desc, .desc, [class*="note-text"], [class*="content"] .note-text');
        detail.description = descEl ? descEl.textContent.trim() : '';

        // Author info
        const authorNameEl = document.querySelector('.author-wrapper .username, .author-container .username, a.name');
        detail.author = {
            nickname: authorNameEl ? authorNameEl.textContent.trim() : '',
            user_id: '',
            avatar: '',
        };
        const authorLink = document.querySelector('a[href*="/user/profile/"]');
        if (authorLink) {
            const m = authorLink.getAttribute('href').match(/profile\/([^?]+)/);
            if (m) detail.author.user_id = m[1];
        }
        const authorAvatar = document.querySelector('.author-wrapper img, .author-container img');
        if (authorAvatar) detail.author.avatar = authorAvatar.getAttribute('src') || '';

        // Interaction counts
        const likeEl = document.querySelector('.like-wrapper .count, [class*="like"] .count');
        const collectEl = document.querySelector('.collect-wrapper .count, [class*="collect"] .count');
        const commentEl = document.querySelector('.chat-wrapper .count, [class*="comment"] .count');
        const shareEl = document.querySelector('.share-wrapper .count, [class*="share"] .count');
        detail.liked_count = likeEl ? likeEl.textContent.trim() : '0';
        detail.collected_count = collectEl ? collectEl.textContent.trim() : '0';
        detail.comment_count = commentEl ? commentEl.textContent.trim() : '0';
        detail.share_count = shareEl ? shareEl.textContent.trim() : '0';

        // Check if liked/collected (active state)
        const likeActive = document.querySelector('.like-wrapper.active, [class*="like"].active');
        const collectActive = document.querySelector('.collect-wrapper.active, [class*="collect"].active');
        detail.liked = !!likeActive;
        detail.collected = !!collectActive;

        // Images
        detail.images = [];
        document.querySelectorAll('.swiper-slide img, .carousel img, [class*="slide"] img').forEach(img => {
            const src = img.getAttribute('src') || '';
            if (src && !src.includes('avatar')) {
                detail.images.push({ url: src, width: img.naturalWidth || 0, height: img.naturalHeight || 0 });
            }
        });

        // Tags
        detail.tags = [];
        document.querySelectorAll('.tag, a.tag, [class*="hashtag"]').forEach(tag => {
            detail.tags.push({ id: '', name: tag.textContent.trim().replace(/^#/, '') });
        });

        // Date/time
        const dateEl = document.querySelector('.date, .time, [class*="publish-date"]');
        detail.time = dateEl ? dateEl.textContent.trim() : '';

        // IP location
        const ipEl = document.querySelector('.ip-info, [class*="location"]');
        detail.ip_location = ipEl ? ipEl.textContent.trim() : '';

        // Video
        const videoEl = document.querySelector('video source, video');
        detail.video_url = videoEl ? (videoEl.getAttribute('src') || videoEl.querySelector('source')?.getAttribute('src') || '') : '';

        detail.type = detail.video_url ? 'video' : 'normal';

        return JSON.stringify(detail);
    }""", feed_id)
    try:
        return json.loads(result) if result else {}
    except json.JSONDecodeError:
        return {}


async def get_feed_detail(feed_id: str, xsec_token: str,
                           load_all_comments: bool = False,
                           limit: int = 20,
                           click_more_replies: bool = False,
                           reply_limit: int = 10,
                           scroll_speed: str = "normal") -> dict:
    """Get feed detail with comments. Returns full note data + comments list."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(feed_id=feed_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Extract note detail — try __INITIAL_STATE__ first, fallback to DOM
        detail_map = await extract_initial_state(page, "note.noteDetailMap")
        detail = {}
        if detail_map and isinstance(detail_map, dict):
            detail = _parse_detail(detail_map, feed_id)

        if not detail or not detail.get("title"):
            logger.info("__INITIAL_STATE__ unavailable, extracting detail from DOM")
            detail = await _extract_detail_from_dom(page, feed_id)

        # Load comments
        comments = await _load_comments(
            page, load_all_comments, limit,
            click_more_replies, reply_limit, scroll_speed
        )

        detail["comments"] = comments
        detail["comment_loaded_count"] = len(comments)
        return detail
    finally:
        await safe_close_page(page)
