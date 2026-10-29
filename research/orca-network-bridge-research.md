# Orca 跨內外網溝通研究

> 歷史研究紀錄：後續決定及原始碼發現請以 [交接文件](handoff.md)、[跨網設計書](orca-cross-network-mail-design.md) 和 [Orca 原生架構](orca-native-architecture.md) 為準。本文的格式與橋接建議並非最終決策。

調查日期：2026-10-30。本機 `orca --version` 為 `1.4.244`；內外網實際安裝版本及網路環境尚未驗證。

## 結論

外網到內網的 FTP 與內網到外網的 `itcp` 加網路芳鄰，可以承載非同步的雙向訊息。建議在兩邊各放一個橋接程式，將訊息寫成檔案、傳輸、驗證與去重，再交給各自的 Orca agent。這是建議架構，尚未實作或在公司環境測試。

現有 Orca 支援 agent orchestration 與連線中的遠端 worker，但已查到的版本說明沒有描述 FTP 或 `itcp` 作為 transport。兩邊完全沒有可連線的 Orca runtime 時，不能直接假設兩個獨立 Run 的 mailbox 會互通。相關依據是本機 `orca orchestration send --help`、`orca orchestration check --help` 與 `orca skills get orchestration`。Orca 的官方專案及 CLI 介紹見 [官方 repository](https://github.com/stablyai/orca)。

## 已確認的 Orca 介面

- `orca orchestration run-create --objective <text>` 建立並綁定 Run；`orca orchestration run-use --id <run_id>` 恢復 coordinator 的 Run。Run 是 namespace 和 coordinator inbox，建立 Run 本身不會安排 worker。（本機 `orca orchestration run-create --help`、`run-use --help`）
- `orca orchestration send --to run:<id> --subject <text> --body <text> --type status --json` 可以向指定 Run 傳訊；`--to dispatch:<id>` 供 coordinator 對特定 attempt 傳訊，文件稱可 relay 到已連線的 worker server。（本機 `orca orchestration send --help`）
- 成功 send 只證明訊息已持久排入，喚醒通知是 best effort，不能證明收件者已讀或接受。（本機 `orca skills get orchestration`）
- `orca orchestration check --run <run_id> --json` 可查詢 Run 的 oldest FIFO delivery；處理完一批後，用 `--ack <delivery_id>` 確認。未確認會重播，且 `--peek`、`--all` 不會 drain mailbox。（本機 `orca orchestration check --help`；實際呼叫仍需符合 Run 綁定與 caller 身分限制。）
- CLI 的 `--environment`、`--pairing-code` 可指定遠端 Orca server；terminal handle 屬於發出它的 server。這需要可用的 runtime 連線，並非文件傳輸協定。（本機上述指令的 `--help`）
- `orca terminal send --terminal <handle> --text <text> --enter --json` 可向既有 terminal 送文字；handle 是 runtime 範圍，重啟或 stale 後需重新列出。是否可直接用於特定 agent，要看其實際 surface、狀態及終端機語意。（本機 `orca skills get orca-cli`）

## 建議橋接流程

1. 外網 agent 將任務內容和唯一 ID 寫入本機 outbox，由外網 bridge 上傳到 FTP；內網 bridge 定期掃描 FTP 的到件資料夾。
2. 內網 bridge 確認檔案已完整到達、驗證格式與來源、記錄 ID，然後交給內網 agent。agent 的回覆帶原任務 ID，交由 bridge 呼叫公司的 `itcp`，將檔案傳到指定資料夾。
3. 外網 bridge 定期讀取網路芳鄰資料夾，驗證與去重後交給外網 agent；雙方各自記錄處理狀態及回覆。

兩邊的 bridge 和 agent 可以先用明確的檔案收件匣契約整合；如需顯示在 Orca 的 agent 信箱，再依兩側版本與 Run/身分規則測試用 `orchestration send` 注入。該介面只將訊息排入 Orca，不能單憑成功回傳斷言 agent 已執行任務。避免直接修改 Orca 內部資料庫；若要 fork Orca 加入 transport，需要另行檢查版本對應的原始碼與維護成本。

## 協定與可靠性

每筆訊息至少包含 `version`、`message_id`、`correlation_id`、`from`、`to`、`type`、`created_at`、`body`；另設 `ack` 或結果訊息，對應原訊息 ID。持久保存處理紀錄，接收端以 ID 去重，傳送端逾時重送。傳輸成功、接收確認與任務完成是三個不同狀態。重試可能重複執行外部副作用，因此要為動作設計 idempotency，不能宣稱一般情況下 exactly-once。

發送端先寫暫存檔，完成後再以目的系統支援的原子改名或獨立完成標記表示可讀；要先確認 FTP、`itcp` 與目的檔案系統是否支援該語意。完成標記應帶預期大小與 hash；未完成或驗證不符時不處理。若無可用的原子改名，採資料檔完成並驗證後才傳完成標記。上述協定屬設計建議，尚待實測。

## 信任邊界與未知事項

- 兩條傳輸路徑必須符合公司內外網資料傳輸政策。尤其內網輸出需資料分類、最小必要資訊與必要審核；外網內容視為不可信資料，不自動執行任意命令。
- 每個方向應限制 bridge 帳號及目的路徑，驗證傳送者、訊息完整性並保留稽核紀錄；hash 只能檢查完整性，若需要驗證來源或防篡改，需用核准的簽章或 MAC 並妥善管理金鑰。FTP 本身是否提供安全保護需要確認。
- 未知項目包括 `itcp` 的實際語法、成功回傳代表的意義與交付完成語意、FTP 操作權限與原子改名、SMB 讀取及刪除權限、可傳檔案類型/大小、掃描頻率、agent 在內網能否連到合規模型服務、資料外送審核。以上需在公司環境中驗證。
