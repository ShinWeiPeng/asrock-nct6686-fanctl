---
spec_version: 1
spec_id: SPEC-0006
revision: 2
status: confirmed
change_set: discussion-ffba3f5f233f
working_id: WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f
task_ref: git-publication-scope
---
# Git 公開追蹤範圍整理

## Problem
目前公開倉庫已有 .gitignore，但 tests/ 與 validation/ 仍是已追蹤檔案；specs/ 被忽略。使用者要求保留 spec，測試與驗證不用上傳。

## Solution
調整忽略規則；從 home-dev 的 Git 索引移除測試與驗證檔案，保留其工作目錄副本。將既有 canonical specs/SPEC-*.md 加入版本控制，更新 README、Makefile 及打包檔案清單，避免公開 clone 依賴未提交測試。依前次 commit + push 指令，從 home-dev 普通提交推送 main。既有已實作 SPEC 保留原文與狀態，其證據連結指向未公開的本機資料。

## User Stories
- 使用者可從 GitHub clone 程式、安裝工具、使用說明及 spec。
- 本機測試與驗證資料保留，但不再出現在公開倉庫目前版本。

## Requirements
| ID | Requirement |
| --- | --- |
| REQ-001 | Git 忽略 tests/、validation/、artifacts/、evidence/，維持 spec-governance/、.build-tools/、認證及建置產物的原忽略規則；specs/SPEC-*.md 不再忽略並納入公開版本。 |
| REQ-002 | 在 home-dev 移除已追蹤的 tests/ 與 validation/ 檔案索引，保留原檔案及內容；普通 commit + push 到已確認的 origin main，保留歷史。 |
| REQ-003 | 公開 Makefile 移除 test target，DKMS 打包清單不再包含 tests，README 改為原始碼建置流程與新的 Git 追蹤政策；不改動 src/、服務或風扇控制行為。 |

## Decisions
| ID | Decision | Rationale | Source |
| --- | --- | --- | --- |
| DEC-001 | spec 保留並公開，測試、驗證與證據不公開。 | 使用者明確回覆「test, evident。一些非程式必要的檔案。spec要保留，測試跟驗證都不用」。 | 01a106dc-4749-7733-8bb6-f29b5ff5a0c2 |
| DEC-002 | 使用 home-dev 的既有 main，普通 commit + push；移除追蹤而保留本機檔案。 | 先前使用者明確要求透過 SSH 操作 home-dev commit + push；本次只調整提交內容。不重寫已發布歷史。 | 01a106c2-ef66-7bf3-a612-5f0ca635a9c9；01a106dc-4749-7733-8bb6-f29b5ff5a0c2 |

## Acceptance Criteria
| ID | Requirements | Criterion | Validation Method | Evidence |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | GitHub main 含 .gitignore 及 canonical spec，沒有已追蹤 tests/、validation/、artifacts/、evidence/、spec-governance/ 或 .build-tools/。 | 檢查 staged 路徑清單、git check-ignore 與 push 後遠端 main。 | Pending execution. |
| AC-002 | REQ-002 | home-dev 原測試與驗證檔案內容雜湊不變；推送普通提交成功，遠端 main 與本機 HEAD 一致。 | 操作前後 SHA256 比較、git diff --cached --check、git ls-remote。 | Pending execution. |
| AC-003 | REQ-003 | 新 clone 的建置與打包流程不依賴未追蹤測試，安裝包不包含 tests/ 或 validation/；產品 src/、服務檔案內容不變。 | 在 home-dev 隔離匯出公開追蹤檔案，執行目標 headers 的模組編譯與 .deb 打包並檢查封裝清單及產品雜湊，不載入模組。 | Pending execution. |

## Acceptance Mapping
```json
{
  "AC-001":{"evidence_claims":["host-semantics"],"contract_dimensions":["input-output-units"],"execution_changes":[],"rationale":"Git 追蹤與忽略規則的實際檔案及遠端狀態檢查；不涉及硬體控制。"},
  "AC-002":{"evidence_claims":["host-semantics"],"contract_dimensions":["state-transition"],"execution_changes":[],"rationale":"實際索引與推送狀態、原始本機副本雜湊對照；保留歷史。"},
  "AC-003":{"evidence_claims":["host-semantics"],"contract_dimensions":["input-output-units"],"execution_changes":[],"rationale":"隔離匯出公開檔案，在既有 home-dev 環境實際建置打包並比對產品來源；不重新執行硬體風扇測試。"}
}
```

## Relationships
- refines: SPEC-0004，調整原始碼公開追蹤政策，保留原已實作規格。
- depends_on: SPEC-0005，保留已發布 LAN 設定檔與文件。
- conflicts_with: None.
- supersedes: None.

## Out Of Scope
刪除本機測試資料、重寫 Git 歷史或強制推送、修改已實作 SPEC 原文、改動驅動原始碼、風扇測試、Proxmox 部署、主機或服務重啟、修改曲線、刪除未指定的 architecture/。

## Open Decisions
None.

## Routing/Gates
spec-governance 保存與結構驗證。此為 Git 追蹤及建置文件整理；不建立新測試、不載入模組。執行前核對目前來源與 main；隔離公開匯出建置打包、索引範圍及原副本雜湊檢查。工程技能要求本次範圍呈現後取得 exact「開始執行」。hooks 的實際信任/載入/觸發未驗證，使用明確 owner CLI。

## Intended Non-Spec Diff
- 修改 .gitignore，移除 /specs/ 忽略規則，新增 /tests/、/validation/、/evidence/。
- Git 索引移除 tests/ 下三個已追蹤測試，以及 validation/layout.yaml、validation/plan.md，保留 home-dev 原檔案。
- 保留並公開 specs/SPEC-0004-proxmox-cha-fan1-control.md、SPEC-0005-discussion-c2945daf5daa.md 與本規格。
- Makefile 移除 OUT 及 test target，保留 modules/all/clean。
- tools/build-deb.sh 移除 tests 的封裝 glob。
- README 移除公開測試指令和 validation 連結，描述私有驗證保留及 spec 公開政策；補上既有 LAN 操作文件連結。

## Revision History
- 2026-10-04：依使用者回覆整理公開追蹤範圍；產品及 Git 索引尚未修改。

## Discussion Context
### DISC-001: 非必要檔案範圍
- **Source:** 01a106dc-4749-7733-8bb6-f29b5ff5a0c2
- **Situation:** 已核對 home-dev 與 GitHub main；.gitignore 已存在並被追蹤，tests/ 與 validation/ 已追蹤，artifacts/ 已忽略，specs/ 尚未公開。
- **Question:** 你看到哪些非必要檔案？請提供檔名或路徑，並註明是在 GitHub 還是 home-dev 看到；我會同時檢查目前的忽略設定。
- **Options and tradeoffs:** 測試與證據只保留本機，公開 clone 可建置打包但不含自動測試；spec 裡的本機證據連結保留且不代表證據已公開。
- **User answer:** test, evident。一些非程式必要的檔案。spec要保留，測試跟驗證都不用
- **Explicit rationale:** 一些非程式必要的檔案。
- **Resulting impact:** REQ-001、REQ-002、REQ-003、DEC-001、DEC-002、AC-001、AC-002、AC-003。

## Current Specification

See Problem, Solution, Requirements and Acceptance Criteria above.

## Decision History

See Decisions, Discussion Context and the sourced Discussion History below.

## Pending Discussion

None.

## Completeness Gaps

None.

<!-- spec-audit:start -->
## Discussion History

- 01a106dc-4749-7733-8bb6-f29b5ff5a0c2: 依使用者確認調整 Git 追蹤：spec 要保留，測試與驗證檔案不要上傳；在 home-dev 整理後 commit + push。保留本機副本及歷史，不修改驅動或主機服務。
- 01a106dc-4749-7733-8bb6-f29b5ff5a0c2: User clarified publication policy: retain spec; tests and validation not wanted. Inspected actual home-dev tree and existing .gitignore. Prepared exact patch and removals; no product/index/push changes performed.
- msg_083b467228e67c21016ac24691e7f487d0ad5c8323a59f6483: Canonical SPEC-0006 revision 2 confirmed scope and authorization state visibly presented; exact cleanup patches and Git path allowlist prepared. Actual home-dev main matches origin at 9265a81 and remains clean. No product edits, index removal or new push performed.
- 01a106f6-4614-7a70-af2b-05a97f413e5f: 開始執行
- 01a106f6-4614-7a70-af2b-05a97f413e5f: Actual current user message is exact execution instruction for presented SPEC-0006 revision 2. No requirement changes. Retain current confirmed binding.

### Source and Revision Audit

```jsonl
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"b6f7ac0e5133c585fe7dd9d73cec1e8d839534f5111e765904e65d7e3210e821","event_type":"start","event_version":1,"open_decisions":[],"previous_event_hash":null,"previous_snapshot_hash":null,"recorded_at":"2026-10-04T12:23:02.895074+00:00","relationships":[],"revision":1,"snapshot_hash":"5b51ce0fc9ee6a849ab7bcfa2a3db1346a0fdda74874883ff32331754e3bdc9d","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"goal":"依使用者確認調整 Git 追蹤：spec 要保留，測試與驗證檔案不要上傳；在 home-dev 整理後 commit + push。保留本機副本及歷史，不修改驅動或主機服務。","historical_entry_evidence":"not-inferred","kind":"entry","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2","task_ref":"git-publication-scope","turn_id":"01a106d8-ee2c-7473-ad71-7d74ba204aba"},"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"ae1809a7270d05a817d1c3ed9af09788ae6d13ed92a8da401a05a63a974abfe3","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"b6f7ac0e5133c585fe7dd9d73cec1e8d839534f5111e765904e65d7e3210e821","previous_snapshot_hash":"5b51ce0fc9ee6a849ab7bcfa2a3db1346a0fdda74874883ff32331754e3bdc9d","recorded_at":"2026-10-04T12:23:02.919315+00:00","relationships":[],"revision":1,"snapshot_hash":"5b51ce0fc9ee6a849ab7bcfa2a3db1346a0fdda74874883ff32331754e3bdc9d","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":["AC-001","AC-002","AC-003","DEC-001","DEC-002","DISC-001","REQ-001","REQ-002","REQ-003"],"conflicts":[],"continuity":"continuous","delta":{"acceptance_changes":[],"added_ids":["AC-001","AC-002","AC-003","DEC-001","DEC-002","DISC-001","REQ-001","REQ-002","REQ-003"],"changed_ids":[],"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"52950e825a8b5333df846292332049b9008ca1824926ecf1a8ce636f13ea61a6","event_type":"reconcile","event_version":1,"open_decisions":[],"previous_event_hash":"ae1809a7270d05a817d1c3ed9af09788ae6d13ed92a8da401a05a63a974abfe3","previous_snapshot_hash":"5b51ce0fc9ee6a849ab7bcfa2a3db1346a0fdda74874883ff32331754e3bdc9d","recorded_at":"2026-10-04T12:25:30.237135+00:00","relationships":[],"revision":2,"snapshot_hash":"189626c6d824aabe302b22b2a4c107657f8a2f839e490196ddb7203725790236","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"f9e5bf3a96a0ade062429a602f2579aff23de850f1c0c399bf139eac5c1c055b","event_type":"materialize","event_version":1,"open_decisions":[],"previous_event_hash":"52950e825a8b5333df846292332049b9008ca1824926ecf1a8ce636f13ea61a6","previous_snapshot_hash":"189626c6d824aabe302b22b2a4c107657f8a2f839e490196ddb7203725790236","recorded_at":"2026-10-04T12:27:19.203438+00:00","relationships":[],"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"binding":{"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"},"candidates":[],"completeness_review":{"acceptance":{"evidence":"Inspect tracked/ignored paths, preserved-file hashes, ordinary push identity and isolated public-source build/package.","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2"},"behavior":{"evidence":"Ignore local test/evidence paths; retain all originals and Git history; public build no longer requires tests.","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2"},"exceptions":{"evidence":"No driver or Proxmox changes; canonical historical specs remain immutable; private evidence not published.","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2"},"goal":{"evidence":"Keep canonical specifications public and omit tests/validation/evidence.","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2"},"scope":{"evidence":"Explicit five tracked removals, four supporting edits and canonical SPEC publication, via home-dev main.","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2"}},"identified_items":{"PUB-001":{"id":"PUB-001","kind":"accepted","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2","text":"spec 要保留，測試與驗證不用公開；依使用者要求調整 Git 追蹤並從 home-dev commit + push。"}},"item_bindings":{"PUB-001":["DEC-001","DEC-002","REQ-001","REQ-002","REQ-003","AC-001","AC-002","AC-003"]},"kind":"saved","reply_sha256":"f28a3e57b0b10a922059903d82b336dac85304a86dde9a8265a1604b749d7a27","reply_stage":"prepared-until-host-stop","reviewed_sources":["01a106dc-4749-7733-8bb6-f29b5ff5a0c2"],"source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2","summary":"User clarified publication policy: retain spec; tests and validation not wanted. Inspected actual home-dev tree and existing .gitignore. Prepared exact patch and removals; no product/index/push changes performed.","task_ref":"git-publication-scope","turn_id":"01a106d8-ee2c-7473-ad71-7d74ba204aba"},"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"eb22024d80c31f61dd638919e36ce8bef542809ed9a846ec7dbf20f55cbc8297","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"f9e5bf3a96a0ade062429a602f2579aff23de850f1c0c399bf139eac5c1c055b","previous_snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","recorded_at":"2026-10-04T12:27:19.224725+00:00","relationships":[],"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"binding":{"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"},"candidates":[],"completeness_review":null,"identified_items":{"PUB-001":{"id":"PUB-001","kind":"accepted","source_ref":"01a106dc-4749-7733-8bb6-f29b5ff5a0c2","text":"spec 要保留，測試與驗證不用公開；依使用者要求調整 Git 追蹤並從 home-dev commit + push。"}},"item_bindings":{"PUB-001":["DEC-001","DEC-002","REQ-001","REQ-002","REQ-003","AC-001","AC-002","AC-003"]},"kind":"saved","reply_sha256":"119b3077a07c931d5217d9fc558d3f08ac7443d9470a4a0aed7ea79b406a8aaf","reply_stage":"prepared-until-host-stop","reviewed_sources":["01a106dc-4749-7733-8bb6-f29b5ff5a0c2"],"source_ref":"msg_083b467228e67c21016ac24691e7f487d0ad5c8323a59f6483","summary":"Canonical SPEC-0006 revision 2 confirmed scope and authorization state visibly presented; exact cleanup patches and Git path allowlist prepared. Actual home-dev main matches origin at 9265a81 and remains clean. No product edits, index removal or new push performed.","task_ref":"git-publication-scope","turn_id":"01a106d8-ee2c-7473-ad71-7d74ba204aba"},"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"45274e3f62ace1706775ae870e245ccf908cd1196ccee3e0ddbe707a7801097d","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"eb22024d80c31f61dd638919e36ce8bef542809ed9a846ec7dbf20f55cbc8297","previous_snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","recorded_at":"2026-10-04T12:29:52.295647+00:00","relationships":[],"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"goal":"開始執行","historical_entry_evidence":"not-inferred","kind":"entry","source_ref":"01a106f6-4614-7a70-af2b-05a97f413e5f","task_ref":"git-publication-scope","turn_id":"01a106f6-43f1-73b0-9109-d4268348871f"},"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"2a0975227e64e550db384024557e169a371d420a1bb6da17cc65eb54487cb19d","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"45274e3f62ace1706775ae870e245ccf908cd1196ccee3e0ddbe707a7801097d","previous_snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","recorded_at":"2026-10-04T12:50:14.187633+00:00","relationships":[],"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"binding":{"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"},"candidates":[],"completeness_review":null,"identified_items":{},"item_bindings":{},"kind":"saved","reply_sha256":"a74af3e9ed392a8185d23a616f3420dd055ce837e988a73a3fadcfdd0644d9a8","reply_stage":"prepared-until-host-stop","reviewed_sources":["01a106f6-4614-7a70-af2b-05a97f413e5f"],"source_ref":"01a106f6-4614-7a70-af2b-05a97f413e5f","summary":"Actual current user message is exact execution instruction for presented SPEC-0006 revision 2. No requirement changes. Retain current confirmed binding.","task_ref":"git-publication-scope","turn_id":"01a106f6-43f1-73b0-9109-d4268348871f"},"removed_ids":[]},"epoch":"21c00d8c3c86408cbafc655fe5b739f9","event_hash":"5026d13dbec1c102d5c93b9ea900acb7b92183c28928f488bb94b436f8b719ce","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"2a0975227e64e550db384024557e169a371d420a1bb6da17cc65eb54487cb19d","previous_snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","recorded_at":"2026-10-04T12:51:09.350649+00:00","relationships":[],"revision":2,"snapshot_hash":"0e35345c3e6344d66f1ca376b053278f1b8854fd42cb3f4cc2d2c28d955c96cb","verdict":"PASS","working_id":"WORKING-SPEC-34fdc51490f1-discussion-ffba3f5f233f"}
```
<!-- spec-audit:end -->
