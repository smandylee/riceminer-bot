from scrapling.fetchers import AsyncFetcher

from crawlers.base import Crawler, Post


class QuasarzoneCrawler(Crawler):
    site_code = "quasarzone"
    list_url = "https://quasarzone.com/bbs/qb_saleinfo"

    async def fetch(self) -> str:
        response = await AsyncFetcher.get(self.list_url)
        return self._check_status(response)

    def parse(self, html: str) -> list[Post]:
        page = self._page(html)
        posts: list[Post] = []
        for row in page.css("div.market-info-list"):
            link_el = row.css("a.subject-link")
            if not link_el:
                continue
            link_el = link_el[0]
            href = link_el.attrib.get("href")
            if not href:
                continue
            title_span = link_el.css("span.ellipsis-with-reply-cnt")
            title = str(title_span[0].text).strip() if title_span else None
            if not title:
                continue
            thumb_el = row.css("div.thumb-wrap img")
            thumbnail = thumb_el[0].attrib.get("src") if thumb_el else None
            price_el = row.css(".market-info-sub .text-orange")
            price = str(price_el[0].text).strip() if price_el else None
            shipping = None
            for span in row.css(".market-info-sub p > span"):
                text = str(span.text or "").strip()
                if text.startswith("배송비"):
                    shipping = text.removeprefix("배송비").strip()
                    break
            posts.append(
                Post(
                    site=self.site_code,
                    title=title,
                    url=page.urljoin(href),
                    thumbnail=thumbnail,
                    price=price,
                    shipping=shipping,
                )
            )
        return posts
