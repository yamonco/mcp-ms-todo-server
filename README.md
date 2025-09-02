
# 라이선스 및 오픈소스 안내

이 프로젝트는 우리조직 명의로 MIT 라이선스로 공개됩니다. 누구나 자유롭게 사용, 수정, 배포, 상업적 이용이 가능합니다. 자세한 내용은 LICENSE 파일을 참고하세요.

# MCP-MS-TODO-SERVER

Microsoft To Do(Graph API)를 MCP(Microsoft Cloud Platform) 기반으로 연동하는 API 서버입니다. Docker 환경에서 빠르게 배포 및 운영할 수 있으며, Streamable HTTP(SSE)와 REST, PowerShell(Microsoft.Graph) 실행을 지원합니다.

---

## 프로젝트 구조

```
mcp-ms-todo-server/
├── .env.example         # 환경 변수 예시 파일
├── Dockerfile           # 도커 이미지 빌드 설정
├── README.md            # 프로젝트 설명 및 사용법
├── app/                 # 서버 애플리케이션 코드
├── docker-compose.yml   # 도커 컴포즈 설정
├── pwsh/                # PowerShell 관련 스크립트/모듈
```

---

## 주요 기능

- **Microsoft To Do(Graph API) 연동**: 인증 및 CRUD 작업 지원
- **Streamable HTTP(SSE)**: 실시간 진행 로그 스트리밍
- **REST/PowerShell 실행**: REST 기본, 옵션으로 PowerShell(Microsoft.Graph)
- **Docker 기반 배포**: .env 환경설정, 토큰/로그 영속 볼륨 지원

---

## 빠른 시작

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

---

## 인증 흐름 (Device Code)

1. 클라이언트에서 MCP 도구 `auth.start_device_code` 호출
2. 서버가 `user_code`, `verification_uri`를 SSE로 반환
3. 브라우저에서 코드 입력 후 승인
4. `auth.status`로 인증 완료 확인

---

## 주요 API 사용 예시

### 태스크 생성
`POST /mcp/tools/call` (SSE 또는 일반 JSON)

```json
{
  "tool": "todo.create_task",
  "params": {
    "list_id": "<LIST_ID>",
    "title": "회의 준비",
    "body": "안건 정리",
    "due": "2025-09-05T09:00:00",
    "time_zone": "Asia/Seoul"
  }
}
```

### 지원 도구/엔드포인트

- 인증: `auth.start_device_code`, `auth.status`, `auth.logout`
- 리스트: `todo.list_lists`, `todo.create_list`, `todo.update_list`
- 태스크: `todo.list_tasks`, `todo.get_task`, `todo.create_task`, `todo.update_task`, `todo.delete_task`
- 변경 감지: `todo.delta_lists`, `todo.delta_tasks`

---

## 환경 변수(.env) 설명

- `TENANT_ID`: organizations|consumers|common 또는 실제 테넌트 ID
- `CLIENT_ID`: 앱 등록 시 지정, 비워두면 퍼스널/공용 클라이언트 사용
- `SCOPES`: 권장값 `Tasks.ReadWrite offline_access`
- `EXECUTOR_MODE`: `rest`(권장) 또는 `pwsh`

---

## 실행 방법 및 문제 해결

1. `.env.example`을 복사해 `.env` 파일 생성 후 환경 변수 설정
2. 도커 이미지 빌드 및 실행
3. 인증 후 API 호출로 Microsoft To Do 연동
4. PowerShell 모드 사용 시, pwsh/ 내 스크립트 및 모듈 참고

### 자주 묻는 질문

- 인증이 안 될 때: `TENANT_ID`, `CLIENT_ID`, `SCOPES` 값 확인
- SSE 로그가 수신되지 않을 때: 클라이언트 SSE 지원 여부 확인
- PowerShell 모드 오류: pwsh/ 내 모듈 및 의존성 확인

---

## 확장 및 참고

- Graph API 공식 문서: https://docs.microsoft.com/ko-kr/graph/api/overview
- MCP 서버 구조 및 확장: app/ 폴더 내 코드 참고

---

문의 및 피드백은 이슈로 남겨주세요.
- PORT: 컨테이너 내부 8080 고정 — 외부 포트는 이 값으로 공개
- TZ, LOG_LEVEL

## 주의
- To Do는 **위임(Delegated) 권한** 기반으로 동작한다. Application 권한은 공식적으로 지원되지 않는다.
- 조직 MFA/보안 정책에 따라 주기적 재로그인이 필요할 수 있다.
- `.env`와 `data/` 디렉토리는 비공개로 관리하라.
