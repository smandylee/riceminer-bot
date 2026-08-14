# riceminer-bot

아카라이브 / 퀘이사존 / FM코리아 핫딜 게시판을 크롤링해 Discord로 알림을 보내는 봇.
([HelloJamong/riceminer](https://github.com/HelloJamong/riceminer)의 구조를 참고해 제작, MIT License)

## 슬래시 명령어

- `/site on|off <code>` — 사이트별 크롤링 켜기/끄기
- `/site list` — 사이트별 상태·주기 확인
- `/interval set|get <code> <seconds>` — 크롤링 주기 조정 (최소 60초)
- `/channel set-post` — 이 채널을 새 글 알림 채널로 지정
- `/channel set-log` — 이 채널을 에러 로그 채널로 지정

## 로컬 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`.env`에 `DISCORD_TOKEN`을 채운 뒤:

```bash
python bot.py
```

Discord 서버에 봇을 초대할 때는 `applications.commands`, `bot` 스코프와
`Send Messages`, `Embed Links` 권한이 필요합니다.

## Railway 배포

1. 이 폴더를 GitHub 저장소로 push
2. Railway 대시보드 → New Project → Deploy from GitHub repo → 이 저장소 선택
   - `Dockerfile`이 있으므로 Railway가 자동으로 Docker 빌드를 사용함
3. 서비스의 **Variables** 탭에서 `DISCORD_TOKEN` 등록
4. (권장) **Volume**을 추가해 `/app` 경로에 마운트
   - 마운트하지 않으면 재배포 시 SQLite DB(`riceminer.db`)가 초기화되어
     사이트 on/off·주기 설정과 중복 방지 이력이 리셋됨
5. 배포 완료 후 Discord에서 봇이 온라인 상태인지, 슬래시 명령이 뜨는지 확인
