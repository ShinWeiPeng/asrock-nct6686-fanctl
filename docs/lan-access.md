# CoolerControl 區域網路存取

本機部署選項：在 Proxmox 上新增 `coolercontrol-lan.socket` 與 `coolercontrol-lan.service`，提供 `http://192.168.2.10:11987`。允許來源為 `192.168.2.0/24`；這個入口不需 Windows SSH 通道或使用者登入。

CoolerControl 本身維持 `127.0.0.1:11987` / `::1:11987`，gRPC 11988 保持本機。保留原登入機制、曲線與驅動配置。代理使用 systemd 的 socket 來源過濾，出站只允許 localhost；必須確認核心 BPF 限制真的掛載，不能只檢查單元文字。

## 部署與驗證

先保存 `/etc/systemd/system/coolercontrol-lan.socket` 和 `.service` 的原始內容、存在狀態、啟用狀態與執行狀態。自動部署只接受兩個單元皆不存在的情況；若已存在，停止部署並保留既有單元。部署對應的 packaging 檔案，執行 `systemd-analyze verify` 與 `systemctl daemon-reload`，再 `systemctl enable --now coolercontrol-lan.socket`。CoolerControl daemon 不需要重啟。

驗證 LAN HTTP、瀏覽器風扇頁或登入頁、socket enabled/active、實際監聽位置、BPF ingress/egress 掛載與來源允許/拒絕行為，並檢查 gRPC 未開放。比較 daemon PID、CoolerControl 配置雜湊與 CPU 風扇 BIOS 模式。只重啟 LAN 入口再次驗證；這不等於已實測 Proxmox 重新開機。

systemd 257 與支援 cgroup BPF 的核心為本次驗證環境。若限制無法確認或 LAN 入口無法運作，保持入口停用並回復原始檔案，不更動 daemon、原曲線、網路介面或其他防火牆。

## 停用與還原

執行 `systemctl disable --now coolercontrol-lan.socket`，再 `systemctl stop coolercontrol-lan.service`。依部署時的備份回復原始單元；若部署前不存在，僅移除這兩個新增單元，再執行 `systemctl daemon-reload`。若是手動維護既有入口，還原檔案後也必須依備份恢復每個單元的 enabled/disabled 與 active/inactive 狀態；部署前未啟用或未執行的單元不要額外啟動。原本的 localhost / SSH 存取方式仍可使用。

開機啟用的是 socket；第一次連線會啟動代理並依賴既有 coolercontrold 背景服務。沒有變更全機防火牆、路由器或 WAN 存取。
