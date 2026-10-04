# ASRock A620AI WiFi NCT6686D 風扇控制

**開發中（0.1.1）**：控制核心已通過主機模擬測試；本版完整 Linux 模組編譯與候選通道辨識尚待驗證。單一 DKMS .deb 的服務、備份與復原工具整合仍待完成，現有套件只交付驅動原始碼。此快照不是已完成實機驗收的版本。

SPEC-0004 的 C Linux hwmon 驅動、DKMS 與 Proxmox CoolerControl 整合。僅接受 ASRock A620AI WiFi / NCT6686D / customer ID 0x1633。

**目前預設唯讀。CHA_FAN1 的通道、電氣極性與 BIOS 接管仍須實機確認，不能假設 pwm4 是 CHA_FAN1。**

## 建置與安裝

在目標 Proxmox 上：
```sh
apt-get install build-essential dkms proxmox-headers-$(uname -r)
make test
make modules
sh tools/build-deb.sh
sh tools/install.sh
systemctl start asrock-nct6686.service
sh tools/install-coolercontrol.sh
```

install.sh 保存設定到 /var/lib/asrock-nct6686-backup.*，建立 DKMS 原始碼與服務但不載入模組。service 首次只載入唯讀驅動。DKMS 嘗試重建未來核心；未經載入與實機測試的核心不宣稱相容。主機重啟尚待安排。

build-deb.sh 建立原始碼 DKMS 套件；安裝套件需要當前核心 headers，只建置/安裝模組，不設定 service 或載入。要使用服務及備份工具，另執行 install.sh。套件與腳本使用相同 DKMS 名稱，請選定一種管理方式，移除時依 [復原說明](docs/recovery.md)。

## 遠端介面

CoolerControl 僅綁本機；在工作站開啟 SSH 通道：
```sh
ssh -N -L 11987:127.0.0.1:11987 root@PROXMOX_HOST
```
再開啟 http://127.0.0.1:11987 。私鑰及認證依工作站既有 SSH 設定，專案不保存秘密。

唯讀時 PWM 控制應為不可寫。無 tach 的 CHA_FAN1 沒有可用 RPM；數字 0 不能證明風扇停轉，也不能換算成真實轉速。CPU_FAN 的 tach 仍保留原讀數。

## 啟用條件

模組參數 enable_control、cha_fan_channel（1 到 8）、channel_verified、polarity_verified、invert_pwm 均只能在載入時設定，權限 0400。只有身分、有效通道、channel_verified 與 polarity_verified 全部成立才提供該通道的寫入權限。invert_pwm 僅在觀察證明需要時設為 1。

這些旗標是管理者對實測的聲明，模組不能自行證明接線。尚未確認前請使用 service 的唯讀設定。啟用程序需先停止 CoolerControl、回 BIOS、卸載再載入；具體通道值與反向設定必須取自實測紀錄。不能把猜測值寫進開機設定。

標準 pwmN 為 0 到 255，pwmN_enable=1 為手動、2 為 BIOS。寫入只改選定通道；失敗回報 errno，有限等待後嘗試回 BIOS。控制命令握手仍須本板實測。正常停止/卸載會嘗試釋放，硬體或核心崩潰不能由模組保證復原。

## 原始碼與驗證

- src/fan_control.c：控制交易與錯誤復原，可用模擬 EC 測試。
- src/nct6686_hwmon.c：Linux hwmon、硬體辨識、鎖與感測器介面。
- tests/modules/fan-control/：公開介面的通道隔離、唯讀、反向及失敗測試。
- validation/：驗收計畫；artifacts/validation/：固定執行紀錄。
- [實機驗證計畫](validation/plan.md)、[復原說明](docs/recovery.md)。

硬體介面源自 [Linux v7.0 nct6683](https://github.com/torvalds/linux/blob/v7.0/drivers/hwmon/nct6683.c)，保留其授權與作者資訊。控制握手參考 [nct6686d](https://github.com/s25g5d4/nct6686d)，該專案測試的是另一款主機板，不構成本板相容性證據。[hwmon 標準](https://docs.kernel.org/hwmon/sysfs-interface.html)；[CoolerControl 安裝](https://docs.coolercontrol.org/installation/debian)及[監聽設定](https://docs.coolercontrol.org/daemon/address)。

GPL-2.0-or-later；完整授權見 [LICENSE](LICENSE)，各來源保留 SPDX 與作者資訊。

## home-dev 測試及發佈

home-dev 或其他 Linux 開發環境可跑 `make test`，不需要 NCT6686D。模擬測試不能確認實際風扇通道。
建置給 Proxmox 的模組時，需準備目標核心完整 headers（包含配置與 Module.symvers），使用
`make KERNEL=7.0.14-11-pve`；不必讓 home-dev 開機使用該核心。不能用 home-dev 自身核心的模組替代。
目前 `tools/build-deb.sh` 產生 DKMS 原始碼安裝包：只傳該 .deb 即可，但安裝主機會編譯。
預先編譯模組則只適用於匹配的核心／架構／配置，更新核心必須重新建置與驗證。

Git 保存原始碼、測試、打包工具及說明；`artifacts/`、`specs/`、`spec-governance/`、`.build-tools/` 與模組建置產物不提交。
本專案不保存 SSH 私鑰或登入認證。發佈 GPL 衍生模組時一併提供對應的完整原始碼及授權資訊。

## 單次候選 pwm4 辨識

此為 SPEC-0004 REQ-012 的明確授權例外，不能代替通道及極性驗證。正常安裝／服務不啟用此路徑。
只有在有人現場觀察且已授權一次辨識時，載入 `identify_once=1` 並保持其餘控制參數為預設。
驅動要求精確板型／晶片／customer ID、active pwm4、初值165、BIOS模式及EC非busy；
只設原始值160，維持3000ms，恢復165後交回BIOS。hwmon duty／模式介面全程唯讀。
檢查 `identify_result` 及核心日誌；載入成功不等於辨識成功。失敗不得自動重複辨識。
若 `handoff_pending=1`，先執行 `tools/restore-bios.sh`；恢復165／BIOS未驗證前不可卸載。
此測試無 tach 回授，只有實際觀察可確認變速的是哪一顆風扇以及變化方向。
