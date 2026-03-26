# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Get user profile."""

import logging
from browser_manager import get_browser
from utils import extract_initial_state, parse_note_card, sleep_random, safe_close_page

logger = logging.getLogger("xhs.user_profile")

PROFILE_URL = "https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={xsec_token}"


async def user_profile(user_id: str, xsec_token: str) -> dict:
    """Get user profile info, interactions, and recent feeds."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = PROFILE_URL.format(user_id=user_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        data = await extract_initial_state(page, "user.userPageData")
        if not data or not isinstance(data, dict):
            return {"error": "Failed to load user profile"}

        basic_info = data.get("basicInfo") or data.get("basic_info") or {}
        interactions = data.get("interactions") or []
        notes = data.get("notes") or []

        # Parse interactions (followers, following, likes, etc.)
        interaction_map = {}
        for item in interactions:
            name = item.get("name") or item.get("type") or ""
            count = item.get("count") or item.get("value") or "0"
            if name:
                interaction_map[name] = count

        # Parse user notes/feeds
        note_list = notes[0].get("noteList", []) if notes and isinstance(notes, list) and notes else []
        feeds = [parse_note_card(n) for n in note_list if isinstance(n, dict)]

        return {
            "userBasicInfo": {
                "nickname": basic_info.get("nickname") or "",
                "desc": basic_info.get("desc") or "",
                "gender": basic_info.get("gender") or "",
                "ip_location": basic_info.get("ipLocation") or "",
                "avatar": basic_info.get("imageb") or basic_info.get("image") or "",
                "red_id": basic_info.get("redId") or basic_info.get("red_id") or "",
            },
            "interactions": interaction_map,
            "feeds": feeds,
            "feeds_count": len(feeds),
        }
    finally:
        await safe_close_page(page)
