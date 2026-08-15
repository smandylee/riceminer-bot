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

## 사이트별 접속 제약

FM코리아는 데이터센터 IP를 HTTP 430으로 차단한다. AWS 서울처럼 한국 리전이어도
막히며, 브라우저 위장(`impersonate`)으로도 우회되지 않는다. 주거용 회선에서만
열리므로 기본값이 꺼짐이고, 집에서 돌릴 때 `/site on fmkorea`로 켜면 된다.

퀘이사존은 해외 IP에서 403이 나므로 한국 리전에서 돌려야 한다.

## AWS Lightsail (서울) 배포

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/smandylee/riceminer-bot.git
cd riceminer-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`.env`에 `DISCORD_TOKEN`을 채운 뒤 systemd에 등록한다.

```bash
sudo cp riceminer-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now riceminer-bot
```

상태 확인은 `systemctl status riceminer-bot`, 로그는 `journalctl -u riceminer-bot -f`.
코드를 갱신할 때는 `git pull` 후 `sudo systemctl restart riceminer-bot`.

### 서버 안정화 (`deploy/`)

Lightsail 최소 사양 인스턴스는 DNS 서버가 VPC 리졸버 하나뿐이고 스왑이 없다.
리졸버가 흔들리면 봇이 죽지 않은 채 재접속만 반복하며 오프라인 상태로 남으므로
(`Temporary failure in name resolution`) 아래를 함께 설정한다.

```bash
# 스왑 1GB
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# DNS 예비 서버 (VPC 리졸버 + Cloudflare + Google)
sudo cp deploy/99-dns-fallback.yaml /etc/netplan/
sudo chmod 600 /etc/netplan/99-dns-fallback.yaml
sudo netplan apply

# 이름 해석이 실패하면 리졸버와 봇을 되살리는 감시 타이머 (2분 주기)
sudo install -m 755 deploy/dns-watchdog.sh /usr/local/bin/
sudo install -m 644 deploy/dns-watchdog.service deploy/dns-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now dns-watchdog.timer
```

`99-dns-fallback.yaml`의 인터페이스명(`ens5`)과 VPC 리졸버 주소는 인스턴스마다 다르므로
`resolvectl status`로 확인 후 맞춘다.

## Railway 배포

1. 이 폴더를 GitHub 저장소로 push
2. Railway 대시보드 → New Project → Deploy from GitHub repo → 이 저장소 선택
   - `Dockerfile`이 있으므로 Railway가 자동으로 Docker 빌드를 사용함
3. 서비스의 **Variables** 탭에서 `DISCORD_TOKEN` 등록
4. (권장) **Volume**을 추가해 `/app` 경로에 마운트
   - 마운트하지 않으면 재배포 시 SQLite DB(`riceminer.db`)가 초기화되어
     사이트 on/off·주기 설정과 중복 방지 이력이 리셋됨
5. 배포 완료 후 Discord에서 봇이 온라인 상태인지, 슬래시 명령이 뜨는지 확인
