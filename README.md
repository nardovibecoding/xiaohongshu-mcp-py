# xiaohongshu-mcp-py

MCP server for **小红书 (Xiaohongshu / RedNote)** — lets Claude and other AI assistants search, publish, and interact with XHS content via the Model Context Protocol.

Built with Patchright (anti-detection Chromium) to avoid bot detection.

XHS has no public API. Getting data out — or publishing — means fighting browser automation. This wraps the whole platform as MCP tools so you can search, post, and manage content from Claude Code directly.

## Tools (13)

| Tool | What it does |
|---|---|
| `check_login_status` | Check if cookies are valid |
| `get_login_qrcode` | Get QR code for WeChat login |
| `delete_cookies` | Reset login session |
| `list_feeds` | Get homepage feed |
| `search_feeds` | Search notes by keyword, sort, type, date |
| `get_feed_detail` | Get note content + comments |
| `user_profile` | Get user info and posts |
| `like_feed` | Like / unlike a note |
| `favorite_feed` | Save / unsave a note |
| `post_comment_to_feed` | Post a comment |
| `reply_comment_in_feed` | Reply to a specific comment |
| `publish_content` | Publish image note with title, tags |
| `publish_with_video` | Publish video note |

## Quick Start

```bash
git clone https://github.com/nardovibecoding/xiaohongshu-mcp-py
cd xiaohongshu-mcp-py
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python server.py --port 18060
```

Then add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "xiaohongshu": { "url": "http://localhost:18060/mcp" }
  }
}
```

## Login

On first run, call `get_login_qrcode` and scan with WeChat. Cookies are saved to `cookies.json` automatically.

## Hot-reload

Reload cookies without restarting the server:

```bash
# Via HTTP
curl -X POST http://localhost:18060/api/v1/reload

# Via signal
kill -HUP $(pgrep -f "server.py --port 18060")
```

## Requirements

- Python 3.11+
- Patchright + Chromium

## License

AGPL-3.0 — see [LICENSE](LICENSE)
