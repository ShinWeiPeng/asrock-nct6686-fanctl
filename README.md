# ASRock A620AI WiFi NCT6686D 風扇控制

**0.2.0：已完成目前核心的有界實機驗收。** C Linux hwmon 驅動、DKMS、服務與 CoolerControl 整合僅接受 ASRock A620AI WiFi / NCT6686D / customer ID 0x1633。在 7.0.14-11-pve 已驗證標準手動控制、CoolerControl 手動／未管理切換、BIOS 接管、停止與移除後恢復原驅動，以及單一安裝包重裝。實測範圍限原始值 120～165；CPU 通道未改寫，VM 持續運作。主機重啟、新核心與長時間運行尚未驗證。

本板實測已確認 pwm4 是 CHA_FAN1：原始值165降至120時機殼風扇變快、CPU風扇沒有變速，恢復165及 BIOS 後兩顆恢復原狀。這是兩個設定點的方向證據，沒有 RPM 校正、全範圍或新核心相容性證據。

## 開發與快速測試

可在 home-dev 等 Linux 環境編輯，不需要每次傳到 Proxmox 才知道編譯錯誤：
```sh
make test CC=gcc-14
python3 tests/flows/driver-lifecycle/test_service.py
python3 tests/flows/driver-lifecycle/test_package.py
make modules CC=gcc-14 KERNEL=7.0.14-11-pve \
  KDIR="$PWD/.build-tools/pve-7.0.14-11/usr/src/linux-headers-7.0.14-11-pve" W=1
sh tools/build-deb.sh
```
KDIR 必須先準備完整的目標核心 headers、配置及 Module.symvers。編譯測試不載入驅動。home-dev 的 Ubuntu GCC14.3 與目標 Debian GCC14.2 不同，Kbuild 可能提示版本差異；缺少 pahole/vmlinux 時沒有 BTF。這些檢查不能替代實際風扇、EC 握手及 CoolerControl 驗證。

## 單一 DKMS 安裝包

只需傳送 build-deb.sh 產生的 .deb 到 Proxmox。套件包含對應 GPL 原始碼、服務、控制工具及復原說明；目標主機會用當前核心 headers 編譯：
```sh
apt-get install build-essential dkms python3 proxmox-headers-$(uname -r)
apt-get install ./asrock-nct6686-fanctl-dkms_0.2.0_all.deb
systemctl start asrock-nct6686.service
```
亦可在原始碼目錄執行 `sh tools/install.sh`，它建置並安裝同一套件。首次安裝與重裝都把控制設定設為停用；安裝不載入模組、不調整風扇。啟動服務預設唯讀，明確使用 identify_once=0。

安裝前保存原有模組、CoolerControl、服務、控制設定及本專案 DKMS 原始碼到 root 私有備份目錄。已載入本專案模組或不同版本 DKMS 登錄會阻擋安裝；舊版迁移按 [復原說明](docs/recovery.md) 處理。同版重裝會重新建置／安裝當前核心模組，不沿用舊建置。

DKMS 可在核心更新後嘗試重建。若控制設定所記錄的實測核心與開機核心不同，服務降為唯讀；重新實測前不自動開啟寫入。重啟、新核心及長時間運行需要另行驗證。

## 已確認通道的控制

完成實體辨識後，由管理者明確啟用；VERIFIED_RUN_ID 是保存該次實測的32位小寫十六進位識別碼：
```sh
/usr/local/libexec/asrock-nct6686/driver-service.py enable \
  --channel 4 --invert --verification-run VERIFIED_RUN_ID
/usr/local/libexec/asrock-nct6686/driver-service.py status
```
工具先保存可復原備份，再停止 CoolerControl、交回 BIOS、切換驅動並重啟原先運行的服務。設定存於 root 擁有、0600 權限的 /var/lib/asrock-nct6686/control.json。旗標與識別碼是管理者對實测的聲明，程式無法自行證明接線。

啟用後只有 pwm4 及 pwm4_enable 可寫，其他通道唯讀。標準 pwm4 是0～255，使用反向映射 `raw = 255 - pwm4`；例如 pwm4=90 對應 raw165、pwm4=135 對應 raw120。畫面百分比表示控制量，不能換算成真實 RPM；已觀察的範圍以外尚未校正。pwm4_enable=1 是手動、2 是 BIOS 接管。載入模組本身不改 duty。

停用寫入並回到唯讀：
```sh
/usr/local/libexec/asrock-nct6686/driver-service.py disable
```
復原失敗會回報錯誤、保留驅動及待復原狀態，不強制卸載。軟體不能保證硬體故障或核心崩潰時復原。

## CoolerControl 介面

依 [CoolerControl 安裝說明](https://docs.coolercontrol.org/installation/debian) 安裝；本專案 drop-in 讓它依賴驅動服務，停止時交回 BIOS，僅綁 loopback。
工作站透過 SSH 通道使用：
```sh
ssh -N -L 11987:127.0.0.1:11987 root@PROXMOX_HOST
```
開啟 http://127.0.0.1:11987 。無 tach 的 CHA_FAN1 沒有可用 RPM；0不能證明停轉。CPU_FAN 仍保留原 tach 讀數。唯讀狀態不能寫入 duty。此版本提供手動設定與 BIOS 接管，未建立溫度曲線。

## 原始碼與驗證

- src/fan_control.c：控制交易、通道隔離及錯誤復原。
- src/nct6686_hwmon.c：Linux hwmon、身分辨識、同步及感測器。
- tools/driver-service.py：啟用、停用、狀態、備份及服務復原。
- tests/modules/fan-control/：C 公開介面與模擬 EC 測試。
- tests/flows/driver-lifecycle/：服務與單一套件的公開介面測試。
- [實機驗證計畫](validation/plan.md)、[停止與復原](docs/recovery.md)。

Git 保存原始碼、測試、打包工具及說明；artifacts/、specs/、spec-governance/、.build-tools/、私鑰、認證及建置產物不提交。其他 checkout 用一般 Git commit/push、pull --ff-only 同步。

硬體介面源自 [Linux v7.0 nct6683](https://github.com/torvalds/linux/blob/v7.0/drivers/hwmon/nct6683.c)，保留授權與作者資訊。握手參考 [nct6686d](https://github.com/s25g5d4/nct6686d)，另一款主機板的測試不能證明本板相容。[hwmon 標準](https://docs.kernel.org/hwmon/sysfs-interface.html)、[CoolerControl 監聽設定](https://docs.coolercontrol.org/daemon/address)。

GPL-2.0-or-later，完整授權見 [LICENSE](LICENSE)。

## 保留的單次辨識入口

僅供已有明確授權、有人現場觀察的一次候選 pwm4 辨識；正常安裝、服务及控制流程均不啟用它。identify_once=1 只在精確身分、active pwm4、原始值165、BIOS模式及EC非busy成立時執行165→120→165→BIOS，設定維持3000ms，實際握手與復原會增加整體耗時。hwmon duty／模式入口全程唯讀。失敗不得自動重複；handoff_pending=1 時先復原，未驗證165及 BIOS 前不可卸載。既有實體辨識已完成，不應自動再次執行。
