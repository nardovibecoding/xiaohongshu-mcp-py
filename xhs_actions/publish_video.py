"""Publish video content to XHS."""

import os
import logging
from patchright.async_api import Page

from browser_manager import get_browser
from utils import sleep_random, safe_close_page
from xhs_actions.publish_image import (
    _fill_title, _fill_content, _set_schedule, _set_visibility,
    _bind_products, PUBLISH_URL,
)

logger = logging.getLogger("xhs.publish_video")


async def publish_with_video(title: str, content: str, video: str,
                              tags: list[str] = None, schedule_at: str = "",
                              visibility: str = "", products: list[str] = None) -> dict:
    """Publish video content to XHS. Video must be a local file path."""
    tags = tags or []
    products = products or []

    if not os.path.exists(video):
        return {"title": title, "content": content, "video": video,
                "status": "failed", "post_id": "", "message": f"Video file not found: {video}"}

    bm = await get_browser()
    page = await bm.new_page()
    try:
        await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Click "上传视频" tab
        try:
            tabs = await page.query_selector_all('[class*="tab"], [class*="publish-type"]')
            for tab in tabs:
                text = await tab.text_content()
                if text and "视频" in text:
                    await tab.click()
                    await sleep_random(0.5, 0.8)
                    break
        except Exception:
            pass

        # Upload video
        upload_input = await page.query_selector(".upload-input") or await page.query_selector('input[type="file"]')
        if not upload_input:
            return {"title": title, "content": content, "video": video,
                    "status": "failed", "post_id": "", "message": "Upload input not found"}

        await upload_input.set_input_files(video)
        logger.info(f"Video file set: {video}")

        # Wait for publish button to become clickable (video processing, max 10 min)
        publish_btn = None
        for _ in range(600):  # 10 minutes at 1s intervals
            publish_btn = await page.query_selector(".publish-page-publish-btn button.bg-red")
            if publish_btn:
                is_disabled = await publish_btn.get_attribute("disabled")
                if not is_disabled:
                    break
            await sleep_random(0.8, 1.2)
        else:
            return {"title": title, "content": content, "video": video,
                    "status": "failed", "post_id": "", "message": "Timeout waiting for video processing"}

        # Fill title
        await _fill_title(page, title)

        # Fill content + tags
        await _fill_content(page, content, tags)

        # Set schedule
        await _set_schedule(page, schedule_at)

        # Set visibility
        await _set_visibility(page, visibility)

        # Bind products
        await _bind_products(page, products)

        # Click publish
        if publish_btn:
            await publish_btn.click()
            await sleep_random(3, 4)
            return {
                "title": title,
                "content": content,
                "video": video,
                "status": "published",
                "post_id": "",
            }
        else:
            return {"title": title, "content": content, "video": video,
                    "status": "failed", "post_id": "", "message": "Publish button not found"}
    finally:
        await safe_close_page(page)
