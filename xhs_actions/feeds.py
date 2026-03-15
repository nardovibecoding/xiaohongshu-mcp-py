"""List homepage feeds."""

import logging
from browser_manager import get_browser
from utils import extract_initial_state, extract_feeds_from_dom, parse_note_card, wait_for_navigation, sleep_random, safe_close_page

logger = logging.getLogger("xhs.feeds")

XHS_HOME = "https://www.xiaohongshu.com"


async def list_feeds() -> dict:
    """Get homepage feed list. Returns {feeds, count}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await wait_for_navigation(page, XHS_HOME)

        # Try __INITIAL_STATE__ first
        feeds_data = await extract_initial_state(page, "feed.feeds")
        if feeds_data and isinstance(feeds_data, list) and len(feeds_data) > 0:
            feeds = [parse_note_card(item) for item in feeds_data if isinstance(item, dict)]
            return {"feeds": feeds, "count": len(feeds)}

        # Fallback: extract from DOM
        await sleep_random(1, 2)
        feeds = await extract_feeds_from_dom(page)
        return {"feeds": feeds, "count": len(feeds)}
    finally:
        await safe_close_page(page)
