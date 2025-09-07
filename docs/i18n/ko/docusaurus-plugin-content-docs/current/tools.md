---
sidebar_position: 4
---

# 툴 사용법 (JSON‑RPC)

## 목록
```json
{ "method": "tools/list", "params": {} }
```

## 실행
```json
{ "method": "tools/call", "params": { "name": "<tool_name>", "arguments": { /* 스키마에 따름 */ } } }
```

## 예시
```json
{ "method": "tools/call", "params": { "name": "todo.create_task", "arguments": { "list_id": "<LIST_ID>", "title": "Prepare" } } }
```

주의
- 실제 스키마는 `tools/list` 결과의 `inputSchema`에서 확인합니다.
- 허가된 툴만 보이고 실행됩니다(키의 역할/허용툴 기준).

