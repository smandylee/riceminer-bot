import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"환경변수 {name}이(가) 설정되어 있지 않습니다")
    return value


DISCORD_TOKEN = _require("DISCORD_TOKEN")

# 하한선은 의도적으로 하드코딩된 상수 — .env로도 우회 불가 (DDoS 감지 방지)
MIN_INTERVAL_SEC = 60
DEFAULT_INTERVAL_SEC = 180

SITE_CODES = ("arca", "quasarzone", "fmkorea")

# FM코리아는 데이터센터 IP를 HTTP 430으로 차단한다. 주거용 회선에서만 열리므로
# 기본값을 꺼짐으로 두고, 집에서 돌릴 때만 /site on 으로 켠다.
DEFAULT_DISABLED_SITES = ("fmkorea",)
