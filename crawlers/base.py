from abc import ABC, abstractmethod
from dataclasses import dataclass

from scrapling.parser import Adaptor


@dataclass
class Post:
    site: str
    title: str
    url: str
    thumbnail: str | None
    price: str | None = None
    shipping: str | None = None


class BlockedError(Exception):
    """비정상 HTTP 상태 코드 — 사이트 차단으로 추정될 때 발생시킨다."""

    def __init__(self, status: int):
        self.status = status
        super().__init__(f"차단 추정 (HTTP {status})")


class Crawler(ABC):
    site_code: str
    list_url: str

    @abstractmethod
    async def fetch(self) -> str:
        """목록 페이지 HTML을 가져온다 (네트워크 I/O)."""

    @abstractmethod
    def parse(self, html: str) -> list[Post]:
        """HTML 문자열을 파싱해 Post 목록을 반환한다. 순수 함수 — 네트워크 호출 없음."""

    def _page(self, html: str) -> Adaptor:
        return Adaptor(html, url=self.list_url)

    def _check_status(self, response) -> str:
        if response.status != 200:
            raise BlockedError(response.status)
        return response.html_content

    async def run(self) -> list[Post]:
        html = await self.fetch()
        return self.parse(html)
