import aiohttp
import re

async def search_nhentai(query: str) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            search_url = f"https://nhentai.to/search/?q={query.replace(' ', '+')}"
            async with session.get(search_url) as resp:
                html = await resp.text()
                match = re.search(r'href="/g/(\d+)/"', html)
                if not match:
                    return None
                code = match.group(1)
                result_url = f"https://nhentai.to/g/{code}/"
                pdf_url = f"https://nhentai.to/g/{code}/download"
                thumbnail = f"https://t.nhentai.net/galleries/{code}/thumb.jpg"
                return {
                    "title": query,
                    "pdf_url": pdf_url,
                    "thumbnail": thumbnail
                }
    except Exception:
        return None
