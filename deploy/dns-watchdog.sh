#!/bin/bash
# DNS가 먹통이 되면 봇은 죽지 않고 재접속만 무한 반복해서 오프라인 상태로 남는다.
# systemd의 Restart=always로는 잡히지 않으므로, 이름 해석을 주기적으로 확인해 리졸버를 되살린다.

set -u

PROBE_HOST="discord.com"

if getent hosts "$PROBE_HOST" >/dev/null 2>&1; then
    exit 0
fi

logger -t dns-watchdog "DNS 해석 실패 ($PROBE_HOST) — systemd-resolved 재시작"
systemctl restart systemd-resolved
sleep 5

if getent hosts "$PROBE_HOST" >/dev/null 2>&1; then
    logger -t dns-watchdog "DNS 복구 — riceminer-bot 재시작"
    systemctl restart riceminer-bot
else
    logger -t dns-watchdog "DNS 복구 실패 — 다음 주기에 재시도"
fi
