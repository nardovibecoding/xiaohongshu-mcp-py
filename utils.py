"""Shared helpers for XHS actions."""

import asyncio
import random
import json
import logging
from patchright.async_api import Page

logger = logging.getLogger("xhs.utils")


async def sleep_random(min_s: float = 0.5, max_s: float = 1.5):
    """Random sleep to appear human."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def extract_initial_state(page: Page, path: str) -> dict | list | None:
    """Extract data from window.__INITIAL_STATE__ by dotted path.

    Example: extract_initial_state(page, "feed.feeds") extracts
    window.__INITIAL_STATE__.feed.feeds (tries both .value and ._value).
    """
    js = f"""() => {{
        try {{
            let obj = window.__INITIAL_STATE__;
            const parts = "{path}".split(".");
            for (const p of parts) {{
                if (!obj) return null;
                obj = obj[p];
            }}
            if (obj && obj._value !== undefined) obj = obj._value;
            else if (obj && obj.value !== undefined) obj = obj.value;
            if (obj) return JSON.stringify(obj);
            return null;
        }} catch(e) {{
            return null;
        }}
    }}"""
    result = await page.evaluate(js)
    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None
    return None


async def wait_for_navigation(page: Page, url: str, timeout: int = 60000):
    """Navigate to URL and wait for load."""
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    await sleep_random(1.5, 2.5)


def parse_note_card(item: dict) -> dict:
    """Parse a raw note card from __INITIAL_STATE__ into a clean dict."""
    note_card = item.get("noteCard") or item.get("note_card") or {}
    if not note_card:
        # item itself might be the note card
        note_card = item

    user = note_card.get("user") or {}
    cover = note_card.get("cover") or {}
    interact_info = note_card.get("interactInfo") or note_card.get("interact_info") or {}

    return {
        "note_id": item.get("id") or note_card.get("noteId") or note_card.get("note_id") or "",
        "xsec_token": item.get("xsec_token") or item.get("xsecToken") or "",
        "title": note_card.get("displayTitle") or note_card.get("display_title") or note_card.get("title") or "",
        "description": note_card.get("desc") or note_card.get("description") or "",
        "type": note_card.get("type") or "",
        "liked_count": interact_info.get("likedCount") or interact_info.get("liked_count") or "0",
        "cover_url": cover.get("urlDefault") or cover.get("url_default") or cover.get("url") or "",
        "author_id": user.get("userId") or user.get("user_id") or "",
        "author_name": user.get("nickname") or user.get("nickName") or "",
        "author_avatar": user.get("avatar") or "",
    }


async def extract_feeds_from_dom(page: Page) -> list[dict]:
    """Extract feed cards directly from DOM elements (fallback when __INITIAL_STATE__ unavailable)."""
    result = await page.evaluate("""() => {
        const feeds = [];
        // Try note-item cards (search results and homepage)
        const cards = document.querySelectorAll('section.note-item, [class*="note-item"]');
        cards.forEach(card => {
            // Prefer link with xsec_token (search_result links have it)
            let link = card.querySelector('a[href*="xsec_token"]');
            if (!link) link = card.querySelector('a[href*="/search_result/"], a[href*="/explore/"]');
            if (!link) return;

            const href = link.getAttribute('href') || '';

            // Extract note_id from URL
            let note_id = '';
            const idMatch = href.match(/(?:explore|search_result)\\/([a-f0-9]+)/);
            if (idMatch) note_id = idMatch[1];

            // Extract xsec_token from URL
            let xsec_token = '';
            const tokenMatch = href.match(/xsec_token=([^&]+)/);
            if (tokenMatch) xsec_token = tokenMatch[1];

            // Title
            const titleEl = card.querySelector('.title, [class*="title"], span.title');
            const title = titleEl ? titleEl.textContent.trim() : '';

            // Author
            const authorLink = card.querySelector('a.author, a[href*="/user/profile/"]');
            const authorEl = card.querySelector('.author-wrapper .name, [class*="author"] .name, .nickname, a.author .name');
            const author_name = authorEl ? authorEl.textContent.trim() : '';

            // Author ID from profile link
            let author_id = '';
            if (authorLink) {
                const authorHref = authorLink.getAttribute('href') || '';
                const authorMatch = authorHref.match(/profile\/([^?]+)/);
                if (authorMatch) author_id = authorMatch[1];
            }

            // Author avatar
            const avatarEl = card.querySelector('.author-wrapper img, [class*="author"] img, a.author img');
            const author_avatar = avatarEl ? (avatarEl.getAttribute('src') || '') : '';

            // Like count
            const likeEl = card.querySelector('.like-wrapper .count, [class*="like"] .count, span.count');
            const liked_count = likeEl ? likeEl.textContent.trim() : '0';

            // Cover image
            const coverEl = card.querySelector('img.cover, a.cover img, img');
            const cover_url = coverEl ? (coverEl.getAttribute('src') || '') : '';

            // Type (video indicator)
            const videoIcon = card.querySelector('[class*="video"], svg[class*="video"]');
            const type = videoIcon ? 'video' : 'normal';

            if (note_id) {
                feeds.push({
                    note_id, xsec_token, title, description: '',
                    type, liked_count, cover_url,
                    author_id, author_name, author_avatar,
                });
            }
        });
        return JSON.stringify(feeds);
    }""")
    try:
        return json.loads(result) if result else []
    except json.JSONDecodeError:
        return []


async def safe_close_page(page: Page):
    """Close page, ignoring errors."""
    try:
        await page.close()
    except Exception:
        pass
