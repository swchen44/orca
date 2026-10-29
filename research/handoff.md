# 交接：Orca 內外網非同步通訊研究

交接日期：2026-10-30  
狀態：研究與設計草案；尚未實作或在公司環境驗證。面向後續在公司環境工作的 agent 與工程師。

## 從這裡開始

1. 閱讀 [Orca 原生架構](orca-native-architecture.md)：先了解 Orca 現有的 Run、Task、Dispatch、mailbox、遠端機制、sequence 與 ACK，以及圖解和版本限制。
2. 閱讀 [跨網通訊設計書](orca-cross-network-mail-design.md)：掌握使用者的目標、FTP／`itcp` 方向、polling、`seq`、`retry`、狀態未知與實測清單。此文件是目前方案的主要依據。
3. 需要研究過去的異常案例或設計取捨時，查閱 [可靠投遞歷史研究](orca-bridge-reliability-design.md) 和 [早期橋接研究](orca-network-bridge-research.md)。兩份都是歷史稿，包含使用者後來沒有選定或已修改的內容，不可當成現行實作要求。
4. 調查與修改程式碼前，先讀 repo 自身的 `AGENTS.md`／適用的本地規範及公司 Orca 版本的內建 CLI／skill 說明；將實際 Orca 版本、commit 和本研究基準的差異記錄下來。

## 使用者已決定

- 儘量沿用 Orca 原有 agent、協作、權限、人工操作、顯示與 log，不預設重做一套 orchestration。需要新增的範圍是 FTP 發送、FTP 落地資料夾 polling、`itcp` 發送、網路芳鄰資料夾 polling，以及跨網訊息的 `seq` 和 `retry`。實際接入位置待原始碼研究與實測。
- 外網 → 內網：FTP 傳入；內網 → 外網：執行 `itcp` 傳至指定資料夾，外網 Windows 從網路芳鄰讀取。`itcp` 實際語法、目的地及完成語意目前未知；在公司環境自行查詢並驗證，查不到再問使用者。
- Polling 活動時約 1 秒、idle 時 5 秒，均可設定；idle 判斷門檻仍待驗證。設計應保持輕量。
- 每個發送節點 → 接收節點方向各自有 `seq`，一般訊息和 receipt 都編號。接收端只檢查並記錄異常，照收到順序處理，不因缺號等待；重送沿用訊息 ID 和 `seq`，`retry` 遞增。
- 使用者不希望另存 `seq`，重啟後希望與對端重新同步；同步來源、協議與無法同步時的處理須核對 Orca 實際能力。兩端沒有可核對紀錄時不能聲稱舊序號可恢復，應標記新區段及狀態未知。
- 如果無法確定訊息是否收過或工作是否已執行，由人員決定是否重送；不可把狀態未知當成工作沒有執行。使用者允許 agent 修改程式碼、部署與操作正式環境，權限及確認照 Orca 原有機制和公司設定；人員也可繼續操作。
- 安全方案希望簡單並符合公司規範；歷史文件的 Ed25519 設計不是已選定方案。內網結果用 `itcp` 傳回，實際規則、資料外送政策及認證方式在公司確認。
- Linux 可能只能 SSH。優先驗證 Linux `orca serve` 加 Windows browser client；若不通，再驗證內網 Windows Orca 桌面版經 SSH 操作 Linux。browser 連線路徑、SSH forwarding 和功能可用性未實測。

## 已確認的事實與重要差異

- 研究時本機 Orca 為 1.4.244；官方 `v1.4.244` tag 指向 commit `b8ec5c8d170bcb9988e65de547a3a4e98b2885a9`。主架構文件連結此固定版本來源；公司版本可能不同。
- Orca 本地 mailbox 的 `send` 成功表示訊息入列，不代表已讀或工作完成；`check` 的 ACK 是本地 delivery batch 確認，不等於跨網收件確認。原生 worker 完成受 Dispatch 身分與權限約束，不能在隔離 runtime 之間直接偽造 `worker_done`。
- **Orca 原生 federation 內部已有 sequence 與 ACK**，且該版本 import 遇到不連續序號會拒絕。這與使用者選擇的跨網 `seq` 僅記 log、按到達順序處理不同。不可直接假設兩種 sequence 相同或相容；釐清適配層和原生 relay 的關係。
- 已查資料未顯示 Orca 提供直接配置 FTP／`itcp` 的公開 transport，也未找到外部適配器寫 Orca 原生 log／GUI 的公開標準 API；這是有限查核結果，不是對完整原始碼的不存在證明。
- `retry` 每次增加會改變 JSON bytes，不能沿用歷史稿的「整份 bytes 永遠相同」去重規則；固定訊息內容與傳輸計數如何分開或比較，須在實作前確定。不可默默把整份 JSON hash 不同視為不同工作。

## 後續工作與完成條件

1. **勘查公司環境。** 唯讀確認 Orca 版本、作業系統、執行帳號、FTP 落地及讀寫權限、網路芳鄰讀取／清理行為、`itcp` 命令說明與返回值、Linux SSH、agent／模型可用性與公司政策。產出逐項實測證據及仍未知事項；未取得授權前不改正式環境。
2. **追查 Orca 原生接點。** 從固定版本及公司實際版本檢查 runtime RPC、orchestration、federation relay 的 send/pull/import/ack、身分及 Dispatch 語意，並搜尋有無可插拔 transport、訊息 API、持久資料與 log 接口。產出「可直接沿用／需適配／不可保證」對照表，不直接修改 Orca 內部 DB。
3. **判定相容方案。** 比較最薄外掛 bridge 與修改 Orca transport；釐清原生 federation 強制連續序號與使用者要求只記 log 的衝突，明確區分外層觀察序號與原生 relay 序號是否可共存。未驗證前不要宣稱完整原生 federation 或全部控制功能可以跨檔案運作。
4. **定稿訊息與恢復。** 定義 JSON 欄位、receipt 是否可沿用原生機制、來源與目的、穩定 ID、`seq` 同步基準、重啟後同步失敗的區段識別、`retry` 比較方式、完成檔案判定，以及對端確認和工作完成的區別。以實際 Orca 資料持有與重啟測試判斷可恢復程度；不另存 `seq` 的限制需保留。
5. **驗證 Linux 網頁方案。** 在公司許可範圍測試 Linux `orca serve`、Windows browser client、配對、SSH forwarding、登入與 agent、Orca UI 功能；不行時驗證 Windows 桌面 Orca + SSH。不要將可 SSH 直接推論為瀏覽器可連。
6. **建立最小可驗證原型。** 依使用者範圍接上兩條單向通道與 polling，優先用 Orca 標準接口；記錄實作的邊界和未支援原生功能。涉及正式環境修改依現場授權與公司規範處理。
7. **執行雙向與故障測試。** 測 active 約 1 秒／idle 5 秒、FTP 與 `itcp` 成功和失敗、半檔、重複、receipt 遺失、retry 遞增、seq 跳號與倒序、外網關機與重啟、雙端同時重啟、狀態未知、人員繼續操作、多節點及 SSH 斷線。驗證結果保留實測紀錄；不能保證的項目明寫限制。
8. **更新設計與回報。** 在主設計書修正過期假設，標註版本和證據；以測試結果區分可用、失敗與未測，不把原生 federation 說成已支援 FTP。涉及序號語意、不可恢復工作或安全政策的實質選擇，帶具體證據請使用者決定。

## 已知風險與研究方向

- 網路芳鄰或中間系統可能清理檔案；兩端都關機時，沒有持久狀態或已遭清理的訊息不能保證恢復。需要證據確認 Orca 或通道實際保留哪些資料。
- 一個 Task 被重建成不同 message ID，或 agent 完成副作用後回覆遺失，都可能造成重複執行；先查 Orca 原生 request／Dispatch 恢復能力，無法查證時交人處理。
- 檔案完整性、已收確認、來源辨識和工作完成是不同問題。確認通道可行的交付標記及 Orca 原生功能後，再決定最小新增機制。
- 發送工具回報成功不等於對端已讀。polling 每秒不代表工作即時完成，且不可令同步失敗阻止使用者要求的正常收到順序。
- 研究 `orca serve` browser 支援時，確認實際版本的配對與可用功能；避免在未經公司允許時曝露網路服務或繞過內外網限制。
