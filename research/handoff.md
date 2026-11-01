# 交接：Orca 內外網非同步通訊研究

交接版本：3.1｜2026-10-30  
狀態：研究、設計與驗收規格已整理；尚未實作 adapter 或在公司環境驗證。面向公司 Agent 與工程師。現行主設計為 [3.1 草案](orca-cross-network-mail-design.md)。

## 1. 從哪些文件開始讀

| 順序 | 文件 | 內容與用途 |
| --- | --- | --- |
| 1 | [Orca 原生架構](orca-native-architecture.md) | 了解原有 Run／Task／Dispatch／mailbox、CLI／runtime、SSH／serve／federation、sequence／ACK；含原生 ARCH、flowchart、sequence diagram 與版本限制 |
| 2 | [內外網通訊主設計](orca-cross-network-mail-design.md) | 現行方案唯一主文件。讀 §2.2 接點表、§4 polling／順序／owner、§5 信封、§6 交接／receipt／ACK、§7 完整檔案、§8 恢復／保留；含跨網 Mermaid 圖 |
| 3 | [Review 對照與故障驗收](orca-bridge-acceptance.md) | 逐項對照 review，列出 26 個 C／O／T 案例；每案有預期、證據來源與自動重試界線，現況全部 not_run |
| 4 | [可靠投遞歷史研究](orca-bridge-reliability-design.md) | 過去較重的可靠性方案與取捨，僅供參考。不得採用其永久 seq 保存、固定重送 bytes、強制簽章等作為現行需求 |
| 5 | [早期橋接研究](orca-network-bridge-research.md) | 早期通道與部署研究背景；遇到差異以主設計及使用者後續指示為準 |

### 後續選型與通訊研究（2026-11-01）

這些文件補充現行3.1主設計，不取代主設計或驗收規格，也不表示已決定改用Herdr：

| 文件 | 閱讀用途 |
| --- | --- |
| [Herdr／Orca選型比較](herdr-vs-orca-study.md) | 需求對照、多主機與SSH、TUI/App/Core區分、改造gap、效能測試設計及社群快照；含stack、architecture、flowchart、sequence圖 |
| [Codex／Claude通訊專題](agent-communication-comparison.md) | CLI/API/PTY/mailbox分層、錯誤與重試、Orca 1.4.245 structured/terminal模式、worker保留及關閉UI後的恢復 |
| [Herdr TUI原始碼查核](herdr-source-findings.md) | 固定commit的SSH routing、NDJSON/bincode、agent lifecycle與ACK界線 |
| [Herdr Core messaging查核](herdr-core-messaging-findings.md) | 固定commit的hc send、parent/child、turn wait、notes/outbox、重啟與去重限制 |
| [Codex 多機操作指南](herdr-codex-multimachine-guide.md) | 使用者操作入口：本機 Codex coordinator、SSH Linux workers、App 查看／補充指令、免 SSH Windows 兩種待定方案；含架構、sequence、flowchart |
| [Core 連線與狀態補查](herdr-core-connection-status-notes.md) | Windows 拒絕 --via、named pipe 與連線限制、Codex 原生 OSC 7501、App 收納條件與固定來源 |

2026-11-02 補充：本次 Herdr 操作流程只使用 Codex。另一台 Windows 禁止 SSH、允許的其他通道尚未確認；「更新」指在 App 看狀態後補充 agent 工作指令。先完成本機＋SSH Linux 原生流程；免 SSH Windows 分為可直連時的 sidecar／transport 適配，以及只允許共享資料夾／FTP／itcp 的非同步 bridge。這些擴充尚未實作，不能視為既有功能；原生 Windows Core 的 --via 在固定版本會拒絕。不要將歷史 Codex／Claude 範例當成使用者另有 Claude 付費方案，也不因換 runtime 自動滿足既有可靠交接規格。

效能尚無同條件實測；GitHub stars/downloads不是活躍使用者數。資料快照位於`.study-evidence/`，可用[重查腳本](collect-comparison-evidence.py)產生新觀察；重跑會取得當時最新資料，不能覆蓋原日期結論後仍宣稱同一份快照。

修改程式碼前另讀 repo 的 `AGENTS.md`、適用的本地規範、公司 Orca 版本的 CLI／內建 skill；保存版本與本研究基準的差異。歷史文件沒有優先於現行主設計的效力。

## 2. Who／What／How

| 角色 | 責任 |
| --- | --- |
| 使用者／公司負責人 | 決定需求、公司跨網與正式環境政策；unknown 且無證據時決定是否重新執行；確認只能由本人提供的 itcp 資料 |
| 公司 Agent／工程師 | 勘查可用環境、核對原生接口、實作最薄適配、執行故障測試、記錄限制與證據；從已授權範圍持續推進，不因一般設計選擇重複請示 |
| 外網主 Orca | 透過本地原生代理與多個已設定 peer 交換訊息，保留原生協作與人工操作 |
| 各端本地接收代理 | 用合法本地身分處理跨網訊息，映射原生 Task／thread，遵守本地 Dispatch／權限；不偽造另一個 runtime 的 worker_done |
| 檔案適配器 | 同一套程式、不同設定；FTP／itcp 發送、資料夾 polling、完整性、穩定 ID／epoch／seq／retry、交接查證及 receipt；不重做工作排程與權限系統 |
| Reviewer | 依實際 source／diff／測試查核設計與實作；使用者先前要求可用時以 Sol xhigh subagent review，未實際執行不得宣稱完成或零意見 |

目標是讓公司隔離網段上的 Orca 在現有傳檔通道協作；設計可交公司實作，並維持輕量。第一階段透過兩端本地代理及專用匯出 inbox 接入原生 orchestration。完整 federation transport 適配另研究，不能預先承諾所有遠端控制功能已可用。

## 3. 使用者已決定的約束

- 外網 → 內網：FTP 傳入，內網 polling 落地資料夾。內網 → 外網：itcp 傳至指定資料夾，外網 Windows 由網路芳鄰 polling。itcp 的命令格式、path、返回碼與完成語意目前未知；在公司先查現場說明，查不到再問使用者。
- 同一套程式由設定檔或環境變數決定角色、peer、收件及送件；兩方向分開設定。一個主節點可協調多節點，人員仍可繼續操作。
- 活動 polling 約 1 秒、idle 約 5 秒，可設定；其他 timeout／batch／idle 門檻是待實測的原型值，不是使用者已定的要求。
- seq 僅檢查及記錄跳號／倒序，照收到順序處理，不等缺號。新訊息與 receipt 各自編號；retry 遞增，原 ID／seq 不變。
- 不另建持久 seq counter；重啟與對端同步，無可靠基準就新區段，不猜舊序號。保留舊 outbox 信封與必要交接證據不等於新增 seq 資料庫。
- 原生 agent、協作、Task、權限、確認、log／GUI 優先沿用；安全方案簡單並遵守公司政策。使用者允許修改程式碼、部署及操作正式環境，但每個實際操作仍遵守現場既有權限與確認機制。
- 無法確定收過或執行過時，由人決定；不能把 unknown、timeout 或沒有紀錄當成未執行。內網結果依 itcp 傳回。
- Linux 可能只能 SSH。優先驗證 Linux `orca serve`＋Windows browser client；不可行時驗證內網 Windows Orca＋SSH。能 SSH 不等於 browser 可直接連線。

## 4. 3.1 已收斂的設計與仍待驗證之處

| 項目 | 目前設計 | 公司需要確認 |
| --- | --- | --- |
| Receipt 確認點 | 只能在可查證的 Orca 持久入列後回成功 receipt；不代表已讀／完成 | 指定 caller 的 send 成功與 requestShow 能否可靠核對及保留 |
| 交接狀態 | incomplete → validated → prepared → enqueued／unknown → receipt_pending；寄件端收到有效確認後為 receipted | 呼叫前可取得／固定原生 request ID；prepared durability；入列回應遺失的查證能力 |
| ACK 所有權 | 業務 inbox 仍由原代理消費；bridge 只消費專用匯出 inbox；整批存成穩定 outbox 才 ACK | 可用的合法地址／Run／Dispatch；peek／all 不消費；原生 row 到 outbox 的重播映射 |
| 序號與去重 | sequence_epoch 區分重啟區段；去重依可信來源、目的與 message_id，不依 epoch／seq | 來源綁定、ID 生命週期及同步基準；原型沒有可靠已分配上限時採新 epoch |
| 固定內容比較 | SHA-256(RFC 8785 canonical JSON(信封去除頂層 retry)) | 使用既有 JCS 實作；改 retry／排版不構成新工作，改固定內容必須 conflict |
| 完整檔案 | 每次獨立 attempt；資料檔＋ready manifest，含長度與完整檔 hash；驗證同一份 bytes | itcp 能傳兩檔並保留名稱；優先原子發布，無 remote rename 時的等效條件必須經測試 |
| 順序與卡住 | 首次完整驗證／納入處理的次序；同輪 ASCII 檔名平手；每 peer 獨立且有限量 | 不依底層列舉、mtime 或 seq 排序；unknown 只暫停受影響 peer 一般訊息，receipt／其他 peer 繼續 |
| 單一執行者 | 每 inbox 指定 host owner＋本機 process lock；不提供跨主機 active-active | 第二實例拒絕；接手前舊 owner 確實結束；不能用 timeout 推論已停止 |
| 保留與人工恢復 | 原型不自動清理未知資料；舊檔先查工作與交接證據 | 原生 prune、最長離線／重送、中間資料夾清理及備份回放時間；人工完成／取消的查證介面 |
| 最小持久資料 | 優先 Orca 原有資料；不足時最小檔案 spool／manifest，不直接修改 Orca DB | 本地原子發布／flush 的可恢復性、容量與權限；不是新增工作 DB 或產品 log 系統 |

上述是待實作的規格，不是原生 API 或公司環境已具備的事實。遇到可用性不足，記錄 blocked／unknown，提出具體替代方案，不把降級包裝成已滿足原需求。

## 5. 已查核的原生證據

先前研究記錄 Orca 1.4.244，固定 commit 為 `b8ec5c8d170bcb9988e65de547a3a4e98b2885a9`；本次補強讀取的是 GitHub 該版本來源，沒有重新操作本機或公司主機。

| 來源 | 對本案的重要事實 |
| --- | --- |
| [messaging-and-gates.md](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/skill-guides/orchestration/references/messaging-and-gates.md) | send 成功是 durable enqueue；coordinator 的並行 check 共用 FIFO batch；peek／all 為唯讀；整批處理後才 ACK |
| [mutation-request-show.ts](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/src/main/runtime/rpc/methods/orchestration/runs/mutation-request-show.ts) | requestShow 依 caller fingerprint 與 request ID 查原生持久收據；不能任意換 caller 解讀結果 |
| [orchestration-mutation-request.ts](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/src/shared/orchestration-mutation-request.ts) | completed／pending／absent 有不同含義；absent 可能是未到達、未記錄或已清理，不能證明沒發生副作用 |
| [send-methods.ts](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/src/main/runtime/rpc/methods/orchestration/messaging/send-methods.ts) 與 [send-point-to-point.ts](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/src/main/runtime/rpc/methods/orchestration/messaging/send-point-to-point.ts) | 有 replay／receipt 路徑，但 worker_done 有特別的原子提交路徑；不能外推為所有普通訊息都已證實可安全 crash replay |
| [federation-relay.ts](https://github.com/stablyai/orca/blob/b8ec5c8d170bcb9988e65de547a3a4e98b2885a9/src/main/runtime/rpc/methods/orchestration/federation/federation-relay.ts) | federation 原本就有 sequence／ACK，import 檢查 caller／attachment 並拒絕缺號；不是本案 log-only seq |

尚未找到可直接配置 FTP／itcp 的公開 transport，以及外部 adapter 寫入 Orca log／GUI 的公開標準 API；這是有限查核結果，不是完整原始碼的不存在證明。公司版本需重新確認。

## 6. 待辦事項、優先序與產出

| 優先序 | 工作 | 完成後必須交付 |
| --- | --- | --- |
| P0 | 唯讀勘查 Orca 版本、OS、帳號、模型／agent、FTP／SMB／itcp、Linux SSH 與公司政策 | 去識別化環境清單；實際說明／回傳行為；每個 TBD 的證據或明確缺項 |
| P0 | 驗證本地代理、專用匯出 inbox、合法 caller、send／requestShow／replay 與 retention | 主設計 §2.2 的實際接口表；每個 request 在呼叫前如何固定、重啟後如何查證；不能支援的功能 |
| P0 | 查明普通訊息入列與 mutation receipt 的中斷空窗 | C03–C06 的實測；completed、pending、absent 各自處理；禁止盲目新建 request 的測試 |
| P0 | 驗證 FTP／itcp 的兩檔完整發布、原子 rename 或等效校驗、單一 owner | C01、O03、T05／T07／T12 的證據；itcp 參數仍不得猜 |
| P1 | 建立最小檔案適配原型與穩定 outbox 映射 | 同程式兩端設定、immutable attempt、polling、receipt、unknown、人工作業；不新增 orchestration 系統 |
| P1 | 驗證四組核心故障：收件／入列／receipt 中斷、人工並讀、雙實例、人工結案後舊檔 | 依驗收文件 C／O 案例逐項記錄預期、實際、證據、是否允許自動重試 |
| P1 | 跑全部 26 案例，涵蓋多 peer、timeout、排序、epoch、資料遺失與保留 | passed／failed／blocked／not_run 矩陣；實際入列及副作用次數，不只觀察 UI |
| P1 | Linux serve＋browser 及 Windows SSH 備案 | 可連線路徑、配對／UI 功能、公司允許的 forwarding 與失聯恢復結果 |
| P2 | 研究完整 federation 適配、ask／reply、log／GUI、原生清理政策與相容版本 | 維持原生連續 sequence／caller／Dispatch 的具體方案，或不能支援的限制；不得直接停用原生檢查 |
| P2 | 更新主設計與 review | 以公司 commit／實測證據修正草案；可用時依使用者要求進行獨立 subagent review，留下 findings 與處理紀錄 |

修改後遵守 repo 的檢查要求，包括可用環境下的 `pnpm check:changed --maxWorkers=2`；需要 UI 測試時遵守 AGENTS.md 的背景啟動與測試規範。本次僅變更研究 Markdown，沒有執行上述 repo 檢查、公司故障測試或 Mermaid 實際渲染，不可沿用為 passed。

## 7. 不能漏掉的研究問題與停止條件

**原生交接：**request ID 能否在第一次 mutation 前指定或取得？caller／runtime 重啟後是否穩定？相同 request、相同參數的 replay 會不會只回原結果？原始命令仍執行時能否安全查詢？一般 status 的入列與 receipt 是否有可恢復的原子性？每個問題要對選用方法實測，不能只看 worker_done 路徑。

**專用 inbox：**地址實際如何建立、誰消費、誰 ACK？整批部分保存後中斷是否重播同 row 並沿用原 ID？人工／GUI 是否有其他途徑把 row 標已讀？原生 Run／Dispatch 結束或 caller 改變後如何查舊結果？不能用新的 inbox 或 caller 掩蓋舊 unknown。

**傳輸與資源：**itcp 是否只在特定 OS／帳號可執行、是否保留檔名、一次可否傳兩檔、成功返回是否只是排入傳輸？SMB 快取、讀檔 deadline、process 終止與 disk-full 如何處理？只剩 read-only 權限時可否完成隔離？單一壞檔／失聯 peer 是否造成飢餓？未驗證時不降級用 size 穩定當完整性。

**保留與恢復：**中間系統多久清檔、最長關機多久、原生 mutation receipt／message 何時 prune、備份是否會回退？去重資料遺失時是否可偵測並進入恢復模式？工作被重建成新 ID、人工先完成／取消或恢復舊備份時，要避免把舊命令當新工作。期限沒有證據前，不自動清理 unresolved 資料。

**多節點與部署：**每個 peer 的可信來源及 route 是否能區分？主端轉交消息仍由本地代理處理；不得自動無限轉寄。Linux／Windows 對 spool、鎖、路徑及 timeout 的差異需實測；兩台機器不能以同一資料夾自行推論已形成高可用叢集。

**人工接手：**unknown 要顯示原 message／request／工作關聯及已查證據。人員可選等待、確認已完成、取消或有意識地重做；只有最後一種才建立新的業務工作。`absent`、新 epoch、timeout 或新 request ID 都不能自動授權重新執行。

## 8. 現況與交接完成定義

已完成：原生架構研究、3.1 主設計及 Mermaid 原始碼、review 對照、26 個驗收案例、公司 Agent 的閱讀順序與待辦。歷史可靠性文件已標示以現行主設計為準。

未完成：公司環境勘查、adapter 程式、原生 API 相容性實測、FTP／itcp／SMB 真實傳輸、故障測試、Linux 網頁方案驗證、repo 檢查與新一輪獨立 subagent review。沒有宣稱 reviewer 已零意見。

後續回報必須分開「文件已完成」「原型可用」「公司實測通過」；所有 blocked 項目寫清缺少什麼證據。涉及改變使用者選定的 seq 語意、無法恢復的正式工作或公司政策時，帶具體證據請使用者決定；其他已授權工作繼續進行。
