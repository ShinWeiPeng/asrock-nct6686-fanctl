# 停止與復原

正常停止先讓 CoolerControl 停止寫入，再交回 BIOS：
```sh
systemctl stop coolercontrold
/usr/local/libexec/asrock-nct6686/restore-bios.sh
systemctl stop asrock-nct6686
```
工具只把已確認通道的 pwmN_enable 設為2並回讀。若 handoff_pending=1，先透過 restore_bios=2 完成待復原交易；單次辨識則要求原始165及 BIOS。失敗會留下驅動並中止，不繼續卸載。唯讀且沒有待復原交易時不寫控制暫存器。成功停止會卸載自寫模組並載回原 nct6683 force=1；此 force 是既有 stock 唯讀感測設定。

若只要保留工具、停用寫入：
```sh
/usr/local/libexec/asrock-nct6686/driver-service.py disable
```
它先備份、停止控制服務、回 BIOS、重載唯讀驅動，再恢復原本運行的 CoolerControl。切換失敗時嘗試恢復原設定與服務；復原不完整時明確報錯，不宣稱已恢復。

## 移除套件

```sh
sh tools/uninstall.sh
# 等同 apt-get remove asrock-nct6686-fanctl-dkms
```
套件移除腳本先停止／停用 CoolerControl、回 BIOS、停止驅動、載回 stock、停用保存的寫入設定並移除本版 DKMS 登錄。復原失敗會中止移除。dpkg 會移除它擁有的原始碼及工具；remove 會保留 conffile，purge 可移除它。私有備份目錄另行保留，不受套件移除影響。檢查 dkms status，不可把仍有其他版本的狀態當成完成。

## 備份

安裝與控制設定切換前會建立新的 /var/lib/asrock-nct6686-backup.XXXXXXXX 目錄，權限0700，內有 state.tar、kernel.txt 及 dkms-status.txt。state.tar 保存當時已存在的本專案原始碼、工具、控制設定、模組設定、CoolerControl 設定與相關服務。設定可能含私密資訊，不上傳 Git 或公開驗證紀錄。

先在主機上檢查目錄與版本，只選擇確定要恢復的檔案；不要把整份 state.tar 覆蓋其他工作後來修改的設定。本專案不改 VM、modprobe.d 或 modules-load.d 設定。備份保留的是設定與來源，不是 VM 磁碟備份，也不保證套件管理器狀態自動回滾。

移除 CoolerControl 整合時，依實際需要處理本專案的 drop-in；若移除 CoolerControl 套件或來源設定，只處理本次新增且已核對的檔案，不刪除原先設定與其他服務。

## 舊版迁移至0.2.0

先使用目前已安裝版本的工具停止 CoolerControl、確認 BIOS 復原及卸載成功；保存上述備份。
0.1.x 不同版本的 DKMS 登錄必須按舊版管理方式移除，確認 `dkms status -m asrock-nct6686-fanctl` 已無舊版，才安裝0.2.0。舊版服務及 drop-in 可能被 dpkg 視為使用者修改；比對備份後採用0.2.0的服務，避免保留以 load-readonly.sh 啟動的舊服務而形成遞迴切換。不要使用新版本移除工具冒充舊版移除。

0.2.0同版重裝也先停止並卸載；安裝會重新編譯、停用寫入設定，但不載入模組。重新啟動是唯讀，必須由管理者明確啟用。新核心即使 DKMS 編譯成功，服務仍會因實測核心不匹配而降為唯讀，重新實測前不得更改實測核心標記。

若控制器無回應，保留模組與錯誤紀錄，現場確認風扇與散熱後安排維護；不要強制卸載。本次不重啟主機、不變更 VM 設定；既有 VM 必須維持運行。
