# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Like and favorite feed actions."""

import logging
from browser_manager import get_browser
from utils import sleep_random, safe_close_page

logger = logging.getLogger("xhs.like_favorite")

DETAIL_URL = "https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}"
LIKE_SELECTOR = ".interact-container .left .like-lottie"
FAVORITE_SELECTOR = ".interact-container .left .reds-icon.collect-icon"


async def like_feed(feed_id: str, xsec_token: str, unlike: bool = False) -> dict:
    """Like or unlike a feed. Smart: skips if already in target state."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(feed_id=feed_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        try:
            like_btn = await page.wait_for_selector(LIKE_SELECTOR, timeout=5000)
            if not like_btn:
                return {"feed_id": feed_id, "success": False, "message": "Like button not found"}

            # Check current state via class or aria attribute
            is_liked = await page.evaluate("""(el) => {
                const parent = el.closest('.like-wrapper, [class*="like"]');
                if (parent) {
                    return parent.classList.contains('active') ||
                           parent.classList.contains('liked') ||
                           parent.getAttribute('aria-pressed') === 'true';
                }
                return false;
            }""", like_btn)

            if unlike and not is_liked:
                return {"feed_id": feed_id, "success": True, "message": "Already not liked, skipped"}
            if not unlike and is_liked:
                return {"feed_id": feed_id, "success": True, "message": "Already liked, skipped"}

            await like_btn.click()
            await sleep_random(0.5, 1.0)

            action = "unliked" if unlike else "liked"
            return {"feed_id": feed_id, "success": True, "message": f"Successfully {action}"}
        except Exception as e:
            return {"feed_id": feed_id, "success": False, "message": str(e)}
    finally:
        await safe_close_page(page)


async def favorite_feed(feed_id: str, xsec_token: str, unfavorite: bool = False) -> dict:
    """Favorite or unfavorite a feed. Smart: skips if already in target state."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(feed_id=feed_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        try:
            fav_btn = await page.wait_for_selector(FAVORITE_SELECTOR, timeout=5000)
            if not fav_btn:
                return {"feed_id": feed_id, "success": False, "message": "Favorite button not found"}

            # Check current state
            is_favorited = await page.evaluate("""(el) => {
                const parent = el.closest('.collect-wrapper, [class*="collect"]');
                if (parent) {
                    return parent.classList.contains('active') ||
                           parent.classList.contains('collected') ||
                           parent.getAttribute('aria-pressed') === 'true';
                }
                // Check if icon itself indicates favorited state
                return el.classList.contains('active') || el.classList.contains('collected');
            }""", fav_btn)

            if unfavorite and not is_favorited:
                return {"feed_id": feed_id, "success": True, "message": "Already not favorited, skipped"}
            if not unfavorite and is_favorited:
                return {"feed_id": feed_id, "success": True, "message": "Already favorited, skipped"}

            await fav_btn.click()
            await sleep_random(0.5, 1.0)

            action = "unfavorited" if unfavorite else "favorited"
            return {"feed_id": feed_id, "success": True, "message": f"Successfully {action}"}
        except Exception as e:
            return {"feed_id": feed_id, "success": False, "message": str(e)}
    finally:
        await safe_close_page(page)
