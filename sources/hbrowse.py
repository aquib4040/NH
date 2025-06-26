import aiohttp
import re

async def search_hbrowse(query: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            search_url = f"https://hbrowse.com/search?q={query.replace(' ', '+')}"
            async with session.get(search_url) as resp:
                html = await resp.text()
                match = re.search(r'href="(/\d+)"', html)
                if not match:
                    return None
                path = match.group(1)
                result_url = f"https://hbrowse.com{path}"
                pdf_url = result_url + "/download"
                return {
                    "title": query,
                    "pdf_url": pdf_url,
                    "thumbnail": "https://hbrowse.com/static/img/hbrowse-icon.png"
                }
    except Exception:
        return None
