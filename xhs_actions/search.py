"""Search XHS feeds with filters."""

import logging
import urllib.parse
from patchright.async_api import Page

from browser_manager import get_browser
from models import FilterOption
from utils import extract_initial_state, parse_note_card, wait_for_navigation, sleep_random, safe_close_page

logger = logging.getLogger("xhs.search")

SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_note"

# Filter selectors — the Go code clicks filter dropdowns and selects options by text
FILTER_MAP = {
    "sort_by": {
        "container_idx": 0,
        "options": ["综合", "最新", "最多点赞", "最多评论", "最多收藏"],
    },
    "note_type": {
        "container_idx": 1,
        "options": ["不限", "视频", "图文"],
    },
    "publish_time": {
        "container_idx": 2,
        "options": ["不限", "一天内", "一周内", "半年内"],
    },
    "search_scope": {
        "container_idx": 3,
        "options": ["不限", "已看过", "未看过", "已关注"],
    },
    "location": {
        "container_idx": 4,
        "options": ["不限", "同城", "附近"],
    },
}


async def _apply_filter(page: Page, filter_name: str, value: str):
    """Apply a single search filter by clicking the dropdown and selecting the option."""
    if value == "不限" or value == "综合":
        return  # Default, skip

    info = FILTER_MAP.get(filter_name)
    if not info or value not in info["options"]:
        return

    try:
        # Click the filter dropdown
        dropdowns = await page.query_selector_all(".filter-box .filter-item")
        if len(dropdowns) <= info["container_idx"]:
            return
        await dropdowns[info["container_idx"]].click()
        await sleep_random(0.3, 0.6)

        # Find and click the matching option
        options = await page.query_selector_all(".filter-box .filter-item .option-list .option-item")
        for opt in options:
            text = await opt.text_content()
            if text and text.strip() == value:
                await opt.click()
                await sleep_random(0.5, 1.0)
                return
    except Exception as e:
        logger.warning(f"Failed to apply filter {filter_name}={value}: {e}")


async def search_feeds(keyword: str, filters: FilterOption | None = None) -> dict:
    """Search XHS by keyword with optional filters. Returns {feeds, count}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = SEARCH_URL.format(keyword=urllib.parse.quote(keyword))
        await wait_for_navigation(page, url)

        # Apply filters if provided
        if filters:
            for field in ["sort_by", "note_type", "publish_time", "search_scope", "location"]:
                val = getattr(filters, field, "不限")
                if val and val not in ("不限", "综合"):
                    await _apply_filter(page, field, val)

            # Wait for results to reload after filters
            await sleep_random(1.5, 2.5)

        feeds_data = await extract_initial_state(page, "search.feeds")
        if not feeds_data or not isinstance(feeds_data, list):
            return {"feeds": [], "count": 0}

        feeds = [parse_note_card(item) for item in feeds_data if isinstance(item, dict)]
        return {"feeds": feeds, "count": len(feeds)}
    finally:
        await safe_close_page(page)
