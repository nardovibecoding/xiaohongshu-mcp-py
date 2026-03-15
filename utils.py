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


async def safe_close_page(page: Page):
    """Close page, ignoring errors."""
    try:
        await page.close()
    except Exception:
        pass
