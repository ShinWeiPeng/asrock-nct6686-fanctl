# 停止與復原

先停止 coolercontrold，避免停止後再有使用者要求寫入：
```sh
systemctl stop coolercontrold
/usr/local/libexec/asrock-nct6686/restore-bios.sh
systemctl stop asrock-nct6686
```
restore-bios.sh 先確認唯一控制器。若單次辨識有 handoff_pending=1，透過 restore_bios=2 重試恢復候選 pwm4 的165及 BIOS，失敗時拒絕卸載。一般控制時再只把已確認通道的 pwmN_enable 設成 2 並回讀。若失败會留下驅動，不繼續卸載。唯讀時不寫控制暫存器。stop-driver.sh 成功後卸載自寫模組並載回原 nct6683 force=1；此 force 僅恢復既有 stock 唯讀感測，不提供自寫模組硬體身分繞過。

若使用 install.sh 管理：
```sh
sh tools/uninstall.sh
```
工具停止服務、復原 BIOS、卸載及移除 DKMS；保留原始碼、備份與 service 供稽核。若透過 dpkg 安裝 .deb，完成上述停用且模組已卸載後，使用 apt-get remove asrock-nct6686-fanctl-dkms，再檢查 dkms status。

備份在 /var/lib/asrock-nct6686-backup.*。先列出 module-settings.tar 和 coolercontrol-config.tar（若原先存在）內容，再確認欲復原的版本及差異；不要整份覆蓋其他工作後來修改的設定。此實作不改動原 modules-load.d、modprobe.d 或 VM 直通設定。

移除本次新增的 CoolerControl 整合時，停止/停用 coolercontrold，移除 /etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf；按需要移除 coolercontrold 套件及本次新增的 coolercontrol.sources/keyring。不要刪除原先已有的設定、其他 repository 或其他服務。

若控制器無回應，軟體只能回報錯誤，不能保證實際 BIOS 已接管。先保留模組與紀錄，立即現場確認散熱與風扇，再安排維護；不要用強制卸載掩蓋失敗。本次沒有安排主機重啟，VM 101/103 必須保持運行。

## 0.1.0 升級到 0.1.1
0.1.1 安裝工具及套件 preinst 會拒絕不同版本的 DKMS 登錄，防止留下旧版本自動重建。
先停止 CoolerControl、執行目前已安裝的 restore-bios／stop-driver，确认復原及卸載成功。
使用旧版本的 uninstall.sh 或旧 .deb 的移除方式移除0.1.0；核對 `dkms status -m asrock-nct6686-fanctl` 為空，再安裝0.1.1。
不要用0.1.1的uninstall.sh冒充0.1.0移除工具；0.1.1移除後也會核對没有其他本專案版本。
唯讀服務明確載入 `identify_once=0`，並拒絕沿用辨識模組或待復原狀態；不得自動再辨識。
