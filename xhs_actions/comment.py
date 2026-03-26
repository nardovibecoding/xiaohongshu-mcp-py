# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Post comments and replies."""

import logging
from browser_manager import get_browser
from utils import sleep_random, safe_close_page

logger = logging.getLogger("xhs.comment")

DETAIL_URL = "https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={xsec_token}"
COMMENT_INPUT_TRIGGER = "div.input-box div.content-edit span"
COMMENT_INPUT = "div.input-box div.content-edit p.content-input"
SUBMIT_BTN = "div.bottom button.submit"


async def post_comment(feed_id: str, xsec_token: str, content: str) -> dict:
    """Post a comment on a feed."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(feed_id=feed_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        try:
            # Click the input trigger to focus
            trigger = await page.wait_for_selector(COMMENT_INPUT_TRIGGER, timeout=5000)
            if trigger:
                await trigger.click()
                await sleep_random(0.3, 0.5)

            # Type into the actual input
            input_el = await page.wait_for_selector(COMMENT_INPUT, timeout=5000)
            if not input_el:
                return {"feed_id": feed_id, "success": False, "message": "Comment input not found"}

            await input_el.fill(content)
            await sleep_random(0.3, 0.5)

            # Click submit
            submit = await page.wait_for_selector(SUBMIT_BTN, timeout=5000)
            if submit:
                await submit.click()
                await sleep_random(1, 2)
                return {"feed_id": feed_id, "success": True, "message": "Comment posted"}
            else:
                return {"feed_id": feed_id, "success": False, "message": "Submit button not found"}
        except Exception as e:
            return {"feed_id": feed_id, "success": False, "message": str(e)}
    finally:
        await safe_close_page(page)


async def reply_comment(feed_id: str, xsec_token: str, content: str,
                         comment_id: str = "", user_id: str = "") -> dict:
    """Reply to a specific comment on a feed."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(feed_id=feed_id, xsec_token=xsec_token)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Scroll to comments
        await page.evaluate("document.querySelector('.comments-container, .comment-list')?.scrollIntoView()")
        await sleep_random(0.5, 1.0)

        # Find the target comment
        found = False
        last_count = 0
        stagnant = 0

        for attempt in range(100):
            comments = await page.query_selector_all(".parent-comment")

            for comment_el in comments:
                # Check by comment ID
                el_id = await comment_el.get_attribute("data-comment-id") or await comment_el.get_attribute("id") or ""
                # Check by user ID
                el_user = await comment_el.evaluate("""(el) => {
                    const userLink = el.querySelector('.author-wrapper a, .user-name a');
                    if (userLink) {
                        const href = userLink.getAttribute('href') || '';
                        const match = href.match(/profile\\/([^?]+)/);
                        return match ? match[1] : '';
                    }
                    return '';
                }""")

                match = False
                if comment_id and el_id and comment_id in el_id:
                    match = True
                elif user_id and el_user and user_id == el_user:
                    match = True

                if match:
                    # Scroll into view and click reply button
                    await comment_el.scroll_into_view_if_needed()
                    await sleep_random(0.3, 0.5)

                    reply_btn = await comment_el.query_selector(".right .interactions .reply, .reply-btn")
                    if reply_btn:
                        await reply_btn.click()
                        await sleep_random(0.5, 0.8)

                        # Type reply
                        input_el = await page.wait_for_selector(COMMENT_INPUT, timeout=5000)
                        if input_el:
                            await input_el.fill(content)
                            await sleep_random(0.3, 0.5)

                            submit = await page.wait_for_selector(SUBMIT_BTN, timeout=5000)
                            if submit:
                                await submit.click()
                                await sleep_random(1, 2)
                                return {
                                    "feed_id": feed_id,
                                    "target_comment_id": comment_id,
                                    "target_user_id": user_id,
                                    "success": True,
                                    "message": "Reply posted",
                                }

                    return {
                        "feed_id": feed_id,
                        "target_comment_id": comment_id,
                        "target_user_id": user_id,
                        "success": False,
                        "message": "Reply button not found on target comment",
                    }

            current_count = len(comments)
            if current_count == last_count:
                stagnant += 1
                if stagnant >= 10:
                    break
            else:
                stagnant = 0
            last_count = current_count

            # Scroll down to load more comments
            await page.evaluate("window.scrollBy(0, 500)")
            await sleep_random(0.6, 1.0)

        return {
            "feed_id": feed_id,
            "target_comment_id": comment_id,
            "target_user_id": user_id,
            "success": False,
            "message": "Target comment not found",
        }
    finally:
        await safe_close_page(page)
