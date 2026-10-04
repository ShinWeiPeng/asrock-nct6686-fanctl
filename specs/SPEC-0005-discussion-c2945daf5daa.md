---
spec_version: 1
spec_id: SPEC-0005
revision: 5
status: implemented
change_set: discussion-c2945daf5daa
working_id: WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa
task_ref: coolercontrol-lan-access
---
# CoolerControl 區域網路連線

## Problem
Windows重開或SSH通道中断後，使用者無法透過localhost網頁存取Proxmox CoolerControl。使用者要求直接從區域網路存取，背景曲線仍照常運作。

## Solution
在Proxmox新增持久的systemd TCP socket與systemd-socket-proxyd服務，僅綁定既有LAN位址192.168.2.10的11987，轉送到既有127.0.0.1:11987。入口僅允許192.168.2.0/24及loopback來源，使用systemd IPAddressAllow/IPAddressDeny並驗證BPF生效。既有CoolerControl 5.0.1服務和11988 gRPC仍綁loopback。網頁入口不依賴Windows、SSH程序或使用者登入。不改寫daemon配置或風扇曲線，不重啟daemon；若存取限制不支援，停止LAN入口並保留原方式。

## User Stories
- 使用者可以直接開啟http://[REDACTED: personal data]:11987，Windows重開後不需重建SSH通道。
- Proxmox啟動後由systemd提供LAN網頁入口，風扇控制沿用既有服務與曲線。

## Requirements
| ID | Requirement |
| --- | --- |
| REQ-001 | 在192.168.2.10:11987提供直接HTTP網頁與其REST API，使用既有CoolerControl登入機制，無需SSH通道。 |
| REQ-002 | LAN入口socket開機啟用；socket使用FreeBind=yes以容忍LAN位址尚未指派，代理Requires/After coolercontrold.service並轉送127.0.0.1:11987。 |
| REQ-003 | 僅接受192.168.2.0/24與localhost來源，代理出站僅localhost；限制需驗證生效。11988保持loopback，不開WAN、不修改其他防火牆、VM、SSH或網路介面。 |
| REQ-004 | 保留目前風扇曲線、認證、驅動、BIOS復原機制及原localhost入口；部署前備份變更目標，失敗只移除/停用新LAN入口並恢復其原始檔，不重啟主機或操作風扇。 |

## Decisions
| ID | Decision | Rationale | Source |
| --- | --- | --- | --- |
| DEC-001 | 採用直接LAN網頁存取取代使用者每次依賴Windows SSH通道。 | 使用者明確要求「我要改成區域網路連線」。 | 01a106a2-55c9-7a61-923d-42de8ba825f1 |
| DEC-002 | 使用系統已安裝的systemd-socket-proxyd提供單一網頁埠的受限入口，保持daemon loopback。 | 已查得CoolerControl 5.0.1的HTTP/gRPC共用監聽位址；獨立網頁入口避免同時開放11988，並避免重啟正在控制風扇的daemon。屬實作選擇，不是使用者另選方案。 | Proxmox唯讀systemctl、ss與檔案檢查；本次需求01a106a2-55c9-7a61-923d-42de8ba825f1 |

## Acceptance Criteria
| ID | Requirements | Criterion | Validation Method | Evidence |
| --- | --- | --- | --- | --- |
| AC-001 | REQ-001 | Windows直接連LAN網址取得網頁HTTP200並可讀取風扇頁面或登入頁；不依賴localhost轉送。 | 直接LAN HTTP請求及瀏覽器檢查；使用192.168.2.10網址，不使用SSH轉送位址。 | PASS — [fixed LAN acceptance](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/evidence.json), [criterion checks](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/checks.json); actual Windows/browser, systemd restart and kernel BPF evidence; true host reboot not tested. |
| AC-002 | REQ-002 | 新socket為enabled/active，啟動設定可通過systemd-analyze verify；停用與重新啟動新入口後LAN頁仍可連。 | 目標systemd單元驗證、is-enabled/is-active、僅重啟入口後HTTP檢查；真實主機重啟不在此驗證範圍。 | PASS — [fixed LAN acceptance](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/evidence.json), [criterion checks](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/checks.json); actual Windows/browser, systemd restart and kernel BPF evidence; true host reboot not tested. |
| AC-003 | REQ-003 | 新入口僅綁192.168.2.10:11987，11988仍只有loopback；來源限制生效、無BPF不支援警告。 | ss與systemctl欄位、kernel/cgroup BPF掛載證據與規則檢查；若無法證實限制，保持入口停用，不宣稱成功。 | PASS — [fixed LAN acceptance](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/evidence.json), [criterion checks](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/checks.json); actual Windows/browser, systemd restart and kernel BPF evidence; true host reboot not tested. |
| AC-004 | REQ-004 | daemon PID/配置雜湊與fan4曲線設定保留，CPU仍為BIOS控制；入口回復步驟可還原部署前狀態。 | 前後配置雜湊/PID/唯讀hwmon與服務狀態比較；保存原始目標與停用/還原指令，不做風扇變速或主機重啟。 | PASS — [fixed LAN acceptance](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/evidence.json), [criterion checks](../artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/checks.json); actual Windows/browser, systemd restart and kernel BPF evidence; true host reboot not tested. |

## Acceptance Mapping
```json
{
  "AC-001": {"evidence_claims":["host-semantics"],"contract_dimensions":["input-output-units"],"execution_changes":[],"rationale":"驗證作業系統服務配置的IP/port/HTTP回應語意，仍須實際Windows至Proxmox連線及瀏覽器證據；沒有共用real/Fake外部Port介面要比較，因此adapter-conformance歸類不適用。原Criterion與Validation Method完全保留。"},
  "AC-002": {"evidence_claims":["host-semantics"],"contract_dimensions":["state-transition"],"execution_changes":[],"rationale":"驗證既有systemd狀態與啟動定義，實際目標入口重啟檢查不變；不以此代替真實主機重開驗收。"},
  "AC-003": {"evidence_claims":["host-semantics"],"contract_dimensions":["input-output-units"],"execution_changes":[],"rationale":"驗證作業系統配置語意及真實cgroup BPF掛載/限制，原來源限制與target evidence要求完全保留；不是共用real/Fake Port比較，也不是風扇硬體變更。"},
  "AC-004": {"evidence_claims":["host-semantics"],"contract_dimensions":["error-reset"],"execution_changes":[],"rationale":"驗證配置保存及復原語意，原實際目標雜湊/PID/CPU模式檢查完全保留；無新增控制演算法或real/Fake Port比較。"}
}
```

## Relationships
- refines: SPEC-0004，新增使用者要求的LAN網頁入口；SPEC-0004既有daemon本機監聽與風扇保護不改寫。
- depends_on: SPEC-0004已實作的背景服務與曲線。
- conflicts_with: None.
- supersedes: None.

## Out Of Scope
主機重開測試、全範圍風扇測試、曲線修改、CPU控制、密碼重設、公開網際網路、路由器設定、TLS憑證部署、其他VM/網路/防火牆更動、公開Git推送。

## Open Decisions
None.

## Routing/Gates
Spec review: PASS
工程技能0.20.0，明確CLI保存，hooks實際信任/載入/觸發未驗證。工程入口要求本規格呈現後取得本次exact「開始執行」，既有SPEC-0004授權不沿用。變更前managed admission/status、systemd配置檢查，變更後LAN存取、來源限制與原服務不變檢查；純連線設定不需重跑核心編譯或風扇脈衝。

## Intended Non-Spec Diff
只新增本機部署工具/操作文件與Proxmox /etc/systemd/system/coolercontrol-lan.socket、coolercontrol-lan.service。部署工具在現有受支持的managed入口下建立，先保存目標存在狀態與雜湊，檢查單元、再啟用socket；任何失敗停止新增入口并恢復目標。原packaging/coolercontrold.conf和/etc/coolercontrol/config.toml不修改。這次不提交或推送Git。

預計socket設定：ListenStream=[REDACTED: personal data]:11987、FreeBind=yes、NoDelay=true、IPAddressDeny=any、IPAddressAllow=localhost、IPAddressAllow=192.168.2.0/24、WantedBy=sockets.target。

預計service設定：Requires/After=coolercontrold.service、ExecStart=/usr/lib/systemd/systemd-socket-proxyd 127.0.0.1:11987、NoNewPrivileges=yes、PrivateTmp=yes、ProtectSystem=strict、ProtectHome=yes、IPAddressDeny=any、IPAddressAllow=localhost；socket的來源限制適用傳入socket，service限制新建出站socket。

## Revision History
- 2026-10-04：依使用者要求新增LAN入口規格；尚未變更Proxmox或產品檔案。
| 5 | 2026-10-04 | Recorded implementation PASS evidence. |

## Discussion Context
### DISC-001: 改為LAN存取
- **Source:** 01a106a2-55c9-7a61-923d-42de8ba825f1
- **Situation:** 已確認Proxmox服務在重開後正常運作，但Windows SSH轉送未自動恢復。
- **Question:** 原訊息直接要求變更，未另提設計選單。
- **Options and tradeoffs:** LAN網址不依賴Windows通道；保留daemon本機位址以避免擴大gRPC存取及干擾正在執行的風扇曲線。
- **User answer:** 我要改成區域網路連線
- **Explicit rationale:** 使用者未另述理由，不推測。
- **Resulting impact:** REQ-001、REQ-002、REQ-003、REQ-004、DEC-001、DEC-002、AC-001、AC-002、AC-003、AC-004。

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

- 01a106a2-55c9-7a61-923d-42de8ba825f1: 我要改成區域網路連線。將 Proxmox [REDACTED: personal data] CoolerControl 網頁改為直接區域網路存取11987，保留風扇曲線，這是已實作SPEC-0004的後續獨立設定變更。
- 01a106a2-55c9-7a61-923d-42de8ba825f1: 使用者要求LAN存取；已唯讀確認Proxmox [REDACTED: personal data]/24、CoolerControl5.0.1 loopback11987/11988、systemd257+BPF以及socket-proxyd已存在。已備妥獨立受限LAN socket代理規格、驗證與復原範圍；尚未修改產品或外部配置，呈現完整方案等待本次確認及精確開始執行。
- 01a106ab-40fc-7102-9d96-fe33071b0940: 開始執行
- 01a106ab-40fc-7102-9d96-fe33071b0940: 使用者已於完整LAN方案呈現後確認並回覆開始執行。修正沒有real/Fake Port比較的驗證歸類為OS host-semantics，四項AC及target HTTP/BPF/原配置保存門檻完全保留，不新增功能需求。現在確認同一方案，接續managed authorization。
- 01a106ab-40fc-7102-9d96-fe33071b0940: 本次LAN部署與四項AC、Standards/Spec review和managed acceptance全部PASS。直接Windows HTTP200，瀏覽器登入頁，socket開機enabled/active，10項BPF封包允許/拒絕測試，原daemon PID944和曲線雜湊/CPU BIOS模式保留。未重開主機，未發布Git。舊本聊天UI SSH通道已結束，LAN不依賴它。

### Source and Revision Audit

```jsonl
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"24a1c93205f787981bae6505fed0da5ae3c850cda3ad710ee22ea94612f0e3a1","event_type":"start","event_version":1,"open_decisions":[],"previous_event_hash":null,"previous_snapshot_hash":null,"recorded_at":"2026-10-04T11:18:42.265442+00:00","relationships":[],"revision":1,"snapshot_hash":"98309d8f55effc113449b93c77e9419782e646f4dea1420aec121d906b3442ff","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"goal":"我要改成區域網路連線。將 Proxmox [REDACTED: personal data] CoolerControl 網頁改為直接區域網路存取11987，保留風扇曲線，這是已實作SPEC-0004的後續獨立設定變更。","historical_entry_evidence":"not-inferred","kind":"entry","source_ref":"01a106a2-55c9-7a61-923d-42de8ba825f1","task_ref":"coolercontrol-lan-access","turn_id":"01a106a2-541e-7961-b88e-30194c21a9c7"},"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"4dd35697aba3f0d1176406f51ebd56f33f52c26792ce85cd9dab6727ed1e04e6","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"24a1c93205f787981bae6505fed0da5ae3c850cda3ad710ee22ea94612f0e3a1","previous_snapshot_hash":"98309d8f55effc113449b93c77e9419782e646f4dea1420aec121d906b3442ff","recorded_at":"2026-10-04T11:18:42.293903+00:00","relationships":[],"revision":1,"snapshot_hash":"98309d8f55effc113449b93c77e9419782e646f4dea1420aec121d906b3442ff","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":["AC-001","AC-002","AC-003","AC-004","DEC-001","DEC-002","DISC-001","REQ-001","REQ-002","REQ-003","REQ-004"],"conflicts":[],"continuity":"continuous","delta":{"acceptance_changes":[],"added_ids":["AC-001","AC-002","AC-003","AC-004","DEC-001","DEC-002","DISC-001","REQ-001","REQ-002","REQ-003","REQ-004"],"changed_ids":[],"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"5a6efaf5d0318f64461f39ff6c5ce521576b934eedc3ee009aed8f11a8f10f32","event_type":"reconcile","event_version":1,"open_decisions":[],"previous_event_hash":"4dd35697aba3f0d1176406f51ebd56f33f52c26792ce85cd9dab6727ed1e04e6","previous_snapshot_hash":"98309d8f55effc113449b93c77e9419782e646f4dea1420aec121d906b3442ff","recorded_at":"2026-10-04T11:23:28.718923+00:00","relationships":[],"revision":2,"snapshot_hash":"0e60c5e21b039b7149de47a77b255c741db1259e8f9fd70766ab67bce3cfc3fd","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"acceptance_changes":[],"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"4841d370e57d71ac6418a69f2a5f14b0d2ab4bdd76571334a2a4f0b293693427","event_type":"reconcile","event_version":1,"open_decisions":[],"previous_event_hash":"5a6efaf5d0318f64461f39ff6c5ce521576b934eedc3ee009aed8f11a8f10f32","previous_snapshot_hash":"0e60c5e21b039b7149de47a77b255c741db1259e8f9fd70766ab67bce3cfc3fd","recorded_at":"2026-10-04T11:25:00.888843+00:00","relationships":[],"revision":3,"snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"binding":{"revision":3,"snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"},"candidates":[],"completeness_review":null,"identified_items":{"LAN-REQUEST":{"id":"LAN-REQUEST","kind":"accepted","source_ref":"01a106a2-55c9-7a61-923d-42de8ba825f1","text":"使用者要求改成區域網路連線，直接開啟Proxmox上的CoolerControl，不再依賴Windows SSH通道。"}},"item_bindings":{"LAN-REQUEST":["DEC-001","REQ-001","REQ-002"]},"kind":"saved","reply_sha256":"a648d20b3f8ef46eb9e0389ff1abbb479301c534e08c9c977ca1bc338a05e2eb","reply_stage":"prepared-until-host-stop","reviewed_sources":["01a106a2-55c9-7a61-923d-42de8ba825f1"],"source_ref":"01a106a2-55c9-7a61-923d-42de8ba825f1","summary":"使用者要求LAN存取；已唯讀確認Proxmox [REDACTED: personal data]/24、CoolerControl5.0.1 loopback11987/11988、systemd257+BPF以及socket-proxyd已存在。已備妥獨立受限LAN socket代理規格、驗證與復原範圍；尚未修改產品或外部配置，呈現完整方案等待本次確認及精確開始執行。","task_ref":"coolercontrol-lan-access","turn_id":"01a106a2-541e-7961-b88e-30194c21a9c7"},"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"fdf24c0c07c088992d4b26f8c99d21893f30277383b4d3710afe348ca3e7b678","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"4841d370e57d71ac6418a69f2a5f14b0d2ab4bdd76571334a2a4f0b293693427","previous_snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","recorded_at":"2026-10-04T11:25:31.193748+00:00","relationships":[],"revision":3,"snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"goal":"開始執行","historical_entry_evidence":"not-inferred","kind":"entry","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940","task_ref":"coolercontrol-lan-access","turn_id":"01a106ab-3f35-7bd2-ba71-c3a43a5e6f33"},"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"102ab34f4685593f7c245f2f4ee505c5b2575d01251ab060aaa36372dfdcbaa2","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"fdf24c0c07c088992d4b26f8c99d21893f30277383b4d3710afe348ca3e7b678","previous_snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","recorded_at":"2026-10-04T11:28:06.116959+00:00","relationships":[],"revision":3,"snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"acceptance_changes":[],"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"468d12a8a241d248fa1d643066dcc3e5b0726d6724e985a8f3ff4472c4cc1a45","event_type":"reconcile","event_version":1,"open_decisions":[],"previous_event_hash":"102ab34f4685593f7c245f2f4ee505c5b2575d01251ab060aaa36372dfdcbaa2","previous_snapshot_hash":"f14141223521381460fde7744415026804de423057296757bcd82f0f2368e36c","recorded_at":"2026-10-04T11:30:44.711712+00:00","relationships":[],"revision":4,"snapshot_hash":"6d0d0023225ba16afc2230c0fe209afdec575f1696c77cca7421271ca958a80d","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"0f5eebab2fdaa4d80130c8eecf4aa13b3ea914506557a5763e0e05c481511586","event_type":"materialize","event_version":1,"open_decisions":[],"previous_event_hash":"468d12a8a241d248fa1d643066dcc3e5b0726d6724e985a8f3ff4472c4cc1a45","previous_snapshot_hash":"6d0d0023225ba16afc2230c0fe209afdec575f1696c77cca7421271ca958a80d","recorded_at":"2026-10-04T11:31:15.874016+00:00","relationships":[],"revision":4,"snapshot_hash":"4ce71957df1e95bec137e07d1b991d2f66756fb564b70eef93eb196098036444","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":[],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":[],"discussion":{"binding":{"revision":4,"snapshot_hash":"4ce71957df1e95bec137e07d1b991d2f66756fb564b70eef93eb196098036444","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"},"candidates":[],"completeness_review":{"acceptance":{"evidence":"四項AC包含直接Windows連線、入口重啟、BPF掛載與原PID/曲線雜湊/CPU模式檢查，均要求實際證據。","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940"},"behavior":{"evidence":"LAN HTTP11987、開機啟用、source allow192.168.2.0/24、localhostbackend。","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940"},"exceptions":{"evidence":"來源限制不能證實則停用入口、保留原方式；不重啟主機、daemon或風扇測試。","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940"},"goal":{"evidence":"直接LAN存取，不依賴Windows SSH。","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940"},"scope":{"evidence":"僅新增LAN socket/proxy、部署工具和操作文件，保留原配置。","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940"}},"identified_items":{"LAN-EXECUTION":{"id":"LAN-EXECUTION","kind":"fact","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940","text":"使用者在SPEC-0005第3版完整方案呈現後明確回覆開始執行，同時確認該方案並授權此範圍實作與部署。"}},"item_bindings":{"LAN-EXECUTION":[]},"kind":"saved","reply_sha256":"a1f5689c5dd89ec4533c77907bf7b66f23d489e63a3b6ddb9f979b13b72dd44a","reply_stage":"prepared-until-host-stop","reviewed_sources":["01a106ab-40fc-7102-9d96-fe33071b0940"],"source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940","summary":"使用者已於完整LAN方案呈現後確認並回覆開始執行。修正沒有real/Fake Port比較的驗證歸類為OS host-semantics，四項AC及target HTTP/BPF/原配置保存門檻完全保留，不新增功能需求。現在確認同一方案，接續managed authorization。","task_ref":"coolercontrol-lan-access","turn_id":"01a106ab-3f35-7bd2-ba71-c3a43a5e6f33"},"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"19870823fc20a3c91699b0bb1644e694b32c75f08eebdee6bf9b34047acfd23b","event_type":"discussion","event_version":1,"open_decisions":[],"previous_event_hash":"0f5eebab2fdaa4d80130c8eecf4aa13b3ea914506557a5763e0e05c481511586","previous_snapshot_hash":"4ce71957df1e95bec137e07d1b991d2f66756fb564b70eef93eb196098036444","recorded_at":"2026-10-04T11:31:15.895312+00:00","relationships":[],"revision":4,"snapshot_hash":"4ce71957df1e95bec137e07d1b991d2f66756fb564b70eef93eb196098036444","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
{"affected_ids":["AC-001","AC-002","AC-003","AC-004"],"conflicts":[],"continuity":"continuous","delta":{"added_ids":[],"changed_ids":["AC-001","AC-002","AC-003","AC-004"],"discussion":{"evidence_ref":"artifacts/validation/e3a59f0b3b614b8bb12ddf8457c58506/manifest.json","kind":"implementation-complete","source_ref":"01a106ab-40fc-7102-9d96-fe33071b0940","summary":"本次LAN部署與四項AC、Standards/Spec review和managed acceptance全部PASS。直接Windows HTTP200，瀏覽器登入頁，socket開機enabled/active，10項BPF封包允許/拒絕測試，原daemon PID944和曲線雜湊/CPU BIOS模式保留。未重開主機，未發布Git。舊本聊天UI SSH通道已結束，LAN不依賴它。","task_ref":"coolercontrol-lan-access","turn_id":"01a106ab-3f35-7bd2-ba71-c3a43a5e6f33"},"removed_ids":[]},"epoch":"1416b7dfbba44f3e9ac6be1d721b5c6e","event_hash":"2271b7ece75cdd3d277ae15b402555cddf7289157eea149faec8071130eeb93c","event_type":"implementation-complete","event_version":1,"open_decisions":[],"previous_event_hash":"19870823fc20a3c91699b0bb1644e694b32c75f08eebdee6bf9b34047acfd23b","previous_snapshot_hash":"4ce71957df1e95bec137e07d1b991d2f66756fb564b70eef93eb196098036444","recorded_at":"2026-10-04T11:52:28.908701+00:00","relationships":[],"revision":5,"snapshot_hash":"87f38804b1afd793a60987e215c0c8c1946970d318d32b124819dbee4541aad4","verdict":"PASS","working_id":"WORKING-SPEC-1eb5741826a0-discussion-c2945daf5daa"}
```
<!-- spec-audit:end -->
