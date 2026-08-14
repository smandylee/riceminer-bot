"""현재 IP에서 각 사이트가 차단되는지, 파싱이 되는지 확인하는 진단 스크립트.

SSL을 가로채는 백신·프록시가 깔린 PC에서는 INSECURE_SSL=1 을 주고 실행한다.
"""

import asyncio
import os

from scrapling.fetchers import AsyncFetcher

from crawlers.arca import ArcaCrawler
from crawlers.fmkorea import FmkoreaCrawler
from crawlers.quasarzone import QuasarzoneCrawler

CRAWLERS = [ArcaCrawler(), QuasarzoneCrawler(), FmkoreaCrawler()]

VERIFY_SSL = os.environ.get("INSECURE_SSL") != "1"


async def check(crawler) -> None:
    label = crawler.site_code
    for mode, kwargs in (
        ("plain", {}),
        ("impersonate", {"impersonate": "chrome", "stealthy_headers": True}),
    ):
        try:
            response = await AsyncFetcher.get(
                crawler.list_url, retries=1, verify=VERIFY_SSL, **kwargs
            )
        except Exception as exc:
            print(f"{label:12} {mode:12} EXCEPTION {type(exc).__name__}: {exc}")
            continue

        status = response.status
        if status != 200:
            print(f"{label:12} {mode:12} HTTP {status}")
            continue

        try:
            posts = crawler.parse(response.html_content)
        except Exception as exc:
            print(f"{label:12} {mode:12} HTTP 200, PARSE FAIL {type(exc).__name__}: {exc}")
            continue

        sample = posts[0].title[:40] if posts else "-"
        print(f"{label:12} {mode:12} HTTP 200, {len(posts)}건, 예시: {sample}")


async def main() -> None:
    for crawler in CRAWLERS:
        await check(crawler)


if __name__ == "__main__":
    asyncio.run(main())
