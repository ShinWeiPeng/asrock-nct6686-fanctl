# SPEC-0004 驗證計畫

## 固定範圍與判定
目標 ASRock A620AI WiFi / NCT6686D customer 0x1633，Proxmox 7.0.14-11-pve。
模擬 EC 與建置通過只是部分證據，不能代替通道/極性/風扇反應及 BIOS 接管觀察。所有 AC 的 Pending 保持到完整驗收。

| AC | 可自動執行 | 必須補齊的實機證據 |
| --- | --- | --- |
| AC-001 | 身分 guard 檢查、唯讀權限、前後 duty/mode | 現場確認 BIOS 原行為 |
| AC-002 | 8 通道位元隔離、超時/錯誤注入 | CHA_FAN1 小幅度反應及 CPU_FAN 未變 |
| AC-003 | sysfs 範圍/模式與 API 識別 | 通道、電氣極性、UI 與無 tach 顯示 |
| AC-004 | GCC/MSVC 公開介面測試、核心/DKMS/.deb | 新核心及重啟另排，不推定相容 |
| AC-005 | 模擬失敗復原、唯讀停止/卸載 | 控制後 BIOS 接管、物理風扇行為 |
| AC-006 | systemd 次序、API、loopback listener/config | 已驗證可寫通道載入後重啟服務 |
| AC-007 | 前後 qm status 101/103、設定摘要 | 主機重啟及未来核心未測標示 |
| AC-008 | 精確165→120→165交易、3秒、初值拒絕、restore失敗重試、全程readonly | 唯一次候選pwm4觀察、CPU_FAN未变、BIOShandoff、前後VM狀態 |

## 唯讀載入 smoke
初始 stock nct6683 loaded，記錄 name、pwm、pwm_enable、CPU fan 與 VM 狀態。確認新模組安裝後首次只讀，所有 PWM 無寫權限；模式/duty 不變。停止及卸載新模組，再載回 stock；比較模式/duty。此測試不能驗收帶控制的 BIOS 接管。

## 控制與現場觀察
先請使用者在主機旁確認 CHA_FAN1 接線與可見風扇，準備 BIOS 或緊急停止。除 REQ-012 單次明確授權例外外，未確認通道不得寫任一 pwm。可在安排的 BIOS 維護時以既有 BIOS 設定辨識通道，前後記錄 Linux raw 值；不自動全範圍校準，也不自行重啟。

確認後仅啟用該通道，依已知電氣範圍選小幅變動，觀察方向並與其他通道及 CPU_FAN 比對。沒有 tach 時記錄可見/可聽反應，不填虛構 RPM。固定 run 保存來源、UTC 時間、參數、前後值與使用者事實。

控制測試結束切回 pwmN_enable=2，回讀並現場確認 BIOS 接管，再停服務/卸載/復原 stock。任何超時、錯誤或異常散熱立即停止測試並保留證據。

## 證據保存
每次執行使用唯一 artifacts/tests 或 artifacts/validation 目錄；完成後保存來源 SHA-256、工具版本、命令、退出碼、原始輸出、各項判定和未覆蓋項目。不要改寫既有完成 run，也不要用最新版目錄代替固定引用。

## 本次 120 單次辨識例外
先前165→160測試已執行並復原，但使用者未注意到風扇反應，無法確認通道與方向；保留該次紀錄，不重用其nonce或防重試標記。
使用者另授權一次候選 pwm4 165→120 維持3秒、先恢復165再交回 BIOS。使用新的module hash、run與防重試標記，辨識仍需現場可觀察。
使用 `identify_once=1` 並保持其他控制參數預設；不得使用 channel_verified／polarity_verified 冒充已驗證。
載入前後記錄 raw PWM1/2/4、control_mode_raw、identify_result、所有pwm*_enable權限與 VM 101/103。
核心日誌應有實際讀值的 begin／hold／end，hold期間raw120、模式僅選定位元暫改，end須165且原模式、pending=0。
載入成功不是辨識成功；拒絕、超時或回讀不符不自動重試一次性 pulse。復原失敗先透過restore_bios恢復。
詢問使用者哪顆風扇有反應、方向、CPU_FAN及回復原行為；沒有清楚反應不得宣稱通道或極性確認。
本機 C 模擬僅驗證演算法，不能代替核心編譯、DKMS及硬體驗收。

## 0.2.0 完整控制驗證
既有120辨識已由現場觀察確認 pwm4→CHA_FAN1、原始值降低時變快、CPU_FAN未變、兩顆恢復；保存其固定run，不能當成0.2.0完整驗收。

home-dev先執行C模擬（含ASan／UBSan）、服務公開介面、套件維護入口及目標headers編譯。服務測試涵蓋：備份先於停服務、備份失敗不變動、未確認核心唯讀、啟用失敗復原、CoolerControl啟動失敗復原、獨立復原輸出预算與待復原時禁止卸載。同版套件需強制重新建置當前核心；編譯失敗不啟用服務。

以唯一run保存0.2.0來源與.deb hash。Proxmox先從同一.deb原始碼原生編譯並測試，保存私人備份後移除舊DKMS，安裝單一套件；首次服務仍唯讀，設定及VM保持。
實際控制只用已觀察raw120～165：反向hwmon值90～135；UI測點也必須落於該範圍。驗證其他PWM唯讀、CPU未變、無tach不造RPM、手動與BIOS接管、停止CC／驅動／移除及重裝。有人現場觀察才能進行短暫變速。
保存套件維護、服務、loopback、CC/API/UI及前後VM證據。最後請使用者一次確認完整物理事實表，未知項明確保留。重啟、新核心及長時間運行未執行，不由同版重裝或單次控制推定。
