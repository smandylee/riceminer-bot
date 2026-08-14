from scrapling.fetchers import AsyncFetcher

from crawlers.base import Crawler, Post


class ArcaCrawler(Crawler):
    site_code = "arca"
    list_url = "https://arca.live/b/hotdeal"

    async def fetch(self) -> str:
        response = await AsyncFetcher.get(self.list_url)
        return self._check_status(response)

    def parse(self, html: str) -> list[Post]:
        page = self._page(html)
        posts: list[Post] = []
        for row in page.css("div.vrow.hybrid"):
            title_el = row.css("a.title.hybrid-title")
            if not title_el:
                continue
            title_el = title_el[0]
            href = title_el.attrib.get("href")
            if not href:
                continue
            texts = [str(t).strip() for t in title_el.xpath("./text()")]
            title = next((t for t in texts if t), None)
            if not title:
                continue
            thumb_el = row.css("a.title.preview-image img")
            src = thumb_el[0].attrib.get("src") if thumb_el else None
            thumbnail = ("https:" + src) if src and src.startswith("//") else src
            price_el = row.css("span.deal-price")
            price = str(price_el[0].text).strip() if price_el else None
            shipping_el = row.css("span.deal-delivery")
            shipping = str(shipping_el[0].text).strip() if shipping_el else None
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
