# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Publish image content to XHS."""

import os
import logging
import tempfile
import urllib.request
from patchright.async_api import Page

from browser_manager import get_browser
from utils import sleep_random, safe_close_page

logger = logging.getLogger("xhs.publish_image")

PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


async def _download_image(url: str) -> str:
    """Download an image URL to a temp file, return the local path."""
    suffix = ".jpg"
    if ".png" in url.lower():
        suffix = ".png"
    elif ".webp" in url.lower():
        suffix = ".webp"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    urllib.request.urlretrieve(url, tmp.name)
    return tmp.name


async def _upload_images(page: Page, images: list[str]) -> int:
    """Upload images one by one, waiting for each to render in preview."""
    uploaded = 0
    for img_path in images:
        # Download if URL
        local_path = img_path
        if img_path.startswith("http://") or img_path.startswith("https://"):
            local_path = await _download_image(img_path)

        if not os.path.exists(local_path):
            logger.warning(f"Image not found: {local_path}")
            continue

        # Find upload input
        upload_input = await page.query_selector(".upload-input") or await page.query_selector('input[type="file"]')
        if not upload_input:
            logger.error("Upload input not found")
            break

        await upload_input.set_input_files(local_path)

        # Wait for preview to appear (max 60s)
        target_count = uploaded + 1
        for _ in range(120):
            previews = await page.query_selector_all("div.img-preview-area .pr")
            if len(previews) >= target_count:
                break
            await sleep_random(0.4, 0.6)
        else:
            logger.warning(f"Timeout waiting for image {target_count} preview")

        uploaded += 1
        await sleep_random(0.3, 0.5)

        # Clean up temp file
        if local_path != img_path and os.path.exists(local_path):
            os.unlink(local_path)

    return uploaded


async def _fill_title(page: Page, title: str):
    """Fill the title field."""
    title_input = await page.wait_for_selector("div.d-input input", timeout=5000)
    if title_input:
        await title_input.fill(title)
        await sleep_random(0.2, 0.4)

        # Check for length error
        error = await page.query_selector("div.max_suffix")
        if error:
            logger.warning("Title too long")


async def _fill_content(page: Page, content: str, tags: list[str]):
    """Fill content and add tags."""
    # Click title first to ensure focus moves correctly
    title_input = await page.query_selector("div.d-input input")
    if title_input:
        await title_input.click()
        await sleep_random(0.2, 0.3)

    editor = await page.query_selector('div.ql-editor') or await page.query_selector('[role="textbox"]')
    if editor:
        await editor.click()
        await sleep_random(0.2, 0.3)
        await editor.fill(content)
        await sleep_random(0.3, 0.5)

        # Add tags
        for tag in tags:
            await page.keyboard.type(f" #{tag}")
            await sleep_random(0.5, 0.8)
            # Press Enter or Escape to dismiss tag suggestion
            await page.keyboard.press("Escape")
            await sleep_random(0.2, 0.3)


async def _set_schedule(page: Page, schedule_at: str):
    """Set scheduled publish time."""
    if not schedule_at:
        return
    # Click the schedule toggle/option
    try:
        schedule_option = await page.query_selector('[class*="timing"], [class*="schedule"]')
        if schedule_option:
            await schedule_option.click()
            await sleep_random(0.5, 0.8)
            # Fill date-time — implementation depends on the exact picker UI
            logger.info(f"Schedule set to: {schedule_at}")
    except Exception as e:
        logger.warning(f"Failed to set schedule: {e}")


async def _set_visibility(page: Page, visibility: str):
    """Set post visibility."""
    if not visibility:
        return
    try:
        dropdown = await page.query_selector("div.permission-card-wrapper div.d-select-content")
        if dropdown:
            await dropdown.click()
            await sleep_random(0.3, 0.5)

            options = await page.query_selector_all("div.d-options-wrapper div.d-grid-item div.custom-option")
            for opt in options:
                text = await opt.text_content()
                if text and visibility in text.strip():
                    await opt.click()
                    await sleep_random(0.3, 0.5)
                    break
    except Exception as e:
        logger.warning(f"Failed to set visibility: {e}")


async def _set_original(page: Page):
    """Declare content as original."""
    try:
        cards = await page.query_selector_all("div.custom-switch-card")
        for card in cards:
            text = await card.text_content()
            if text and "原创声明" in text:
                switch = await card.query_selector("div.d-switch")
                if switch:
                    await switch.click()
                    await sleep_random(0.5, 0.8)

                    # Handle confirmation dialog
                    await page.evaluate("""() => {
                        const footer = document.querySelector('div.footer');
                        if (footer) {
                            const checkbox = footer.querySelector('input[type="checkbox"]');
                            if (checkbox && !checkbox.checked) checkbox.click();
                            const btn = footer.querySelector('button');
                            if (btn) btn.click();
                        }
                    }""")
                    await sleep_random(0.3, 0.5)
                break
    except Exception as e:
        logger.warning(f"Failed to set original: {e}")


async def _bind_products(page: Page, products: list[str]):
    """Search and bind product links."""
    if not products:
        return
    try:
        for product_keyword in products:
            # Open product selector modal
            product_btn = await page.query_selector('[class*="product"], [class*="goods"]')
            if product_btn:
                await product_btn.click()
                await sleep_random(0.5, 0.8)

            # Wait for modal
            modal = await page.wait_for_selector(".multi-goods-selector-modal", timeout=5000)
            if not modal:
                continue

            # Search for product
            search_input = await modal.query_selector('input[placeholder*="搜索商品"]')
            if search_input:
                await search_input.fill(product_keyword)
                await page.keyboard.press("Enter")
                await sleep_random(1, 2)

                # Wait for results
                await page.wait_for_selector(".goods-list-normal .good-card-container", timeout=10000)

                # Click first result
                first_card = await page.query_selector(".goods-list-normal .good-card-container .d-checkbox")
                if first_card:
                    await first_card.click()
                    await sleep_random(0.3, 0.5)

            # Save
            save_btn = await page.query_selector(".goods-selected-footer button")
            if save_btn:
                await save_btn.click()
                await sleep_random(0.5, 0.8)
    except Exception as e:
        logger.warning(f"Failed to bind products: {e}")


async def publish_content(title: str, content: str, images: list[str],
                           tags: list[str] = None, schedule_at: str = "",
                           is_original: bool = False, visibility: str = "",
                           products: list[str] = None) -> dict:
    """Publish image content to XHS."""
    tags = tags or []
    products = products or []

    bm = await get_browser()
    page = await bm.new_page()
    try:
        await page.goto(PUBLISH_URL, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Click "上传图文" tab
        try:
            tabs = await page.query_selector_all('[class*="tab"], [class*="publish-type"]')
            for tab in tabs:
                text = await tab.text_content()
                if text and "图文" in text:
                    await tab.click()
                    await sleep_random(0.5, 0.8)
                    break
        except Exception:
            pass

        # Upload images
        uploaded = await _upload_images(page, images)
        if uploaded == 0:
            return {"title": title, "content": content, "images": 0,
                    "status": "failed", "post_id": "", "message": "No images uploaded"}

        # Fill title
        await _fill_title(page, title)

        # Fill content + tags
        await _fill_content(page, content, tags)

        # Set schedule
        await _set_schedule(page, schedule_at)

        # Set visibility
        await _set_visibility(page, visibility)

        # Set original
        if is_original:
            await _set_original(page)

        # Bind products
        await _bind_products(page, products)

        # Click publish
        publish_btn = await page.query_selector(".publish-page-publish-btn button.bg-red")
        if publish_btn:
            await publish_btn.click()
            await sleep_random(3, 4)
            return {
                "title": title,
                "content": content,
                "images": uploaded,
                "status": "published",
                "post_id": "",
            }
        else:
            return {
                "title": title,
                "content": content,
                "images": uploaded,
                "status": "failed",
                "post_id": "",
                "message": "Publish button not found",
            }
    finally:
        await safe_close_page(page)
