"""List homepage feeds."""

import logging
from browser_manager import get_browser
from utils import extract_initial_state, parse_note_card, wait_for_navigation, safe_close_page

logger = logging.getLogger("xhs.feeds")

XHS_HOME = "https://www.xiaohongshu.com"


async def list_feeds() -> dict:
    """Get homepage feed list. Returns {feeds, count}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await wait_for_navigation(page, XHS_HOME)

        feeds_data = await extract_initial_state(page, "feed.feeds")
        if not feeds_data or not isinstance(feeds_data, list):
            return {"feeds": [], "count": 0}

        feeds = [parse_note_card(item) for item in feeds_data if isinstance(item, dict)]
        return {"feeds": feeds, "count": len(feeds)}
    finally:
        await safe_close_page(page)
