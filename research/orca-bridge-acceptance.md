# Orca 檔案橋接驗收與 review 對照

版本：3.1 草案｜2026-10-30  
依據：[主設計書](orca-cross-network-mail-design.md)。本文件是待執行的驗收規格，不是測試通過報告。公司環境、程式實作、故障注入與 Mermaid 實際渲染均尚未驗證。

## 1. Review 對照

| Review 項目 | 3.1 的處理 | 實作前的通過條件 |
| --- | --- | --- |
| P1：receipt 與 Orca 交接空窗 | 主設計 §6：receipt 僅確認已可查證的 Orca 持久入列；列出交接狀態、持久證據及 unknown 恢復流程 | 相同 caller、request ID 與參數可在中斷後查證；pending／absent 不會被當成未執行 |
| P1：人工與 bridge 競爭 inbox | §6.3：專用匯出 inbox、唯一消費者、整批保存後才 ACK；人工以 peek／all 監看 | 無人或第二個 process 消費同一 batch；原業務 inbox 可繼續操作 |
| P1：federation 接點未定 | §2.2：第一階段用本地接收代理；列出功能、API、地址與限制 | 公司版本驗證合法身分、地址與 RPC；不把外層 seq 直接送 federationImport |
| 序號區段 | §5：sequence_epoch；重送保留 epoch、ID、seq；新區段不影響去重 | 重啟及舊區段延遲檔不造成重新執行；無獨立持久 seq counter |
| 完整檔案 | §7：每次傳輸使用不可覆寫的資料檔及 ready manifest；校驗長度與 SHA-256 | FTP／itcp 能送兩檔；接收端以驗證過的同一份 bytes 交付，半檔不通過 |
| 收到順序 | §4：首次完整驗證並納入處理的順序；同輪固定檔名排序；不依 seq／mtime 排序 | 1、3、2 的跨輪到達順序維持；同一輪可重現，工作完成順序另由 Task 相依性決定 |
| 卡住與多節點 | §4、§7：逾時、每輪上限、每對端獨立佇列及單一 owner | 一個失聯對端不阻塞其他對端；舊 process 未退出時不啟動同通道替代 sender |
| 舊檔與人工接手 | §8：保留條件、unknown 查證、完成／取消後重播與資料遺失模式 | 沒有紀錄不等於新工作；無法證明安全時不自動重做 |
| 歷史文件優先權 | 歷史稿僅供參考，現行方案以主設計及本清單為準 | 歷史稿不再宣稱優先於主設計 §6 |

「文件已補強」不代表上述原生能力或公司通道已通過驗收。遇到不能確認的原生 API、caller 身分或 receipt 保留期限，必須記為 blocked／unknown，不能以新建 request 代替查證。

## 2. 測試前置條件與紀錄

先在隔離測試 workspace 執行可觀察、無正式環境副作用的工作。記錄 Orca 版本／commit、兩端 OS、adapter commit、caller 身分參照、Run／Dispatch、路由設定、polling／timeout／retry 值及 FTP／itcp 的實際說明。認證資料不得寫入 public repo。

每筆測試紀錄包含：案例 ID、時間、注入位置、來源及目的節點、message_id、sequence_epoch、seq、retry、固定內容 digest、每次傳輸檔名、原生 request ID／訊息 ID、查證介面與結果、實際副作用次數、預期／實際狀態、是否允許自動重試及結論。使用 Orca 原有 log／公開查詢，必要時保留測試證據；不要另建一套產品 log 系統。

結果只使用 passed、failed、blocked、not_run。以下案例目前全部為 **not_run**。

## 3. 收件、入列與 receipt 的故障邊界

| ID | 操作／中斷點 | 預期狀態及不變條件 | 查證來源 | 自動重試界線 |
| --- | --- | --- | --- | --- |
| C01 | 資料檔寫一半時殺掉 sender；另測 ready manifest 截斷、先到或延遲 | incomplete；不交付、不回成功 receipt | ready 與資料檔的格式、長度、hash；本地 Orca 不應有新訊息 | 可重新讀取／重傳原訊息；不得直接入列半檔 |
| C02 | 完整接收並保存後、prepared 交接紀錄建立前中斷 | validated；重啟能找到完整原檔；沒有任何原生呼叫已發出 | 本地 spool、狀態紀錄、呼叫邊界注入證據 | 能證明未呼叫時可進行首次交付；證據不足轉 unknown |
| C03 | prepared 紀錄已持久化、原生呼叫前後各中斷一次 | prepared／handoff_unknown；保留相同 request 身分與參數 | prepared 紀錄、同 caller 的 requestShow、原生 mailbox | 不建立新 request；只有已驗證的同請求 replay 才可自動執行 |
| C04 | Orca 訊息已入列、成功回應被丟棄 | 不再插入第二封；查證成功後為 enqueued | requestShow completed 的 method／receipt／訊息 ID，必要時原生唯讀 mailbox 查證 | 僅可重放已完成請求或重送 receipt；入列恢復測試未過則人工處理 |
| C05 | Orca 狀態為 pending；分別測原 process 活著、已退出與 runtime 重啟 | 保持 unknown／查證中；不假設未執行 | requestShow、原 process 狀態、原生訊息／Task | 原 process 活著先查詢；退出也須已證明該方法 pending replay 安全才可重放 |
| C06 | requestShow absent：分別以換 caller、清理 receipt、還原舊狀態重現 | unknown；不得因 absent 建立新工作 | caller 綁定、receipt 保留策略、原生訊息與 Task 紀錄 | 僅重試唯讀查證；重新派工需人工決定 |
| C07 | enqueued 已確認、receipt 尚未建立或發送前中斷 | 原訊息只入列一次；重啟依原證據生成／恢復 receipt | 原生入列證據、receipt spool 及穩定關聯 | 可恢復 receipt；不得重做工作 |
| C08 | receipt 發送中斷、itcp 超時、sender 收到 receipt 後尚未持久確認就關機 | 接收端維持 enqueued；sender 可能重傳同一 message | 雙端 spool、receipt 關聯、原生訊息數量 | 可重傳原訊息／receipt；不得建立新 ID 逃過去重 |
| C09 | 偽造來源、錯誤 in_reply_to／digest／方向的 receipt，及重複 receipt | 不清除不相關 outbox；合法重複 receipt 無額外副作用 | 可信路由映射、待送固定內容、receipt | receipt 不再回 receipt；未知或衝突送人工檢查 |

## 4. Inbox 所有權、並行與人工操作

| ID | 操作 | 預期狀態及不變條件 | 查證來源 | 自動重試界線 |
| --- | --- | --- | --- | --- |
| O01 | bridge 消費專用匯出 inbox；人工同時 peek／all；另在隔離環境重現兩個 consuming check | 正式配置只有一個 ACK owner；監看不消費。重現實驗應證明共用 batch 的風險，不能把第二個 consumer 當安全配置 | delivery_id、所有 batch row、原生已讀狀態、outbox 對照 | 監看可重試；不得用重送補救無法查證的誤 ACK |
| O02 | 一個 batch 含多筆，保存到第 N 筆就中斷；另測全部保存後 ACK 回應丟失 | 未完整保存不 ACK；batch 重播時已保存的 row 沿用原 message_id，不產生新 outbox | delivery_id、原生 row ID 與 outbox 一對一映射 | 可重讀 batch、確認全部保存後 ACK；只對缺漏 row 建立首次 outbox |
| O03 | 同一主機同一 inbox 啟動兩個 bridge；另測兩台主機共用同一 drop path | 第二個本機實例拒絕取得 owner；跨主機只允許一台配置為 owner，未提供 active-active | OS process lock、部署路由表、sender／入列計數 | 只有確認舊 owner 結束後可接手；不能憑網路逾時搶占 |
| O04 | 人工先完成或取消 Task，再重播舊訊息；另測 message 去重紀錄已清理 | 已確認完成／取消不重新啟動；缺證據為 unknown；人工已處理但從未入列時不得偽造 durable-enqueue receipt | 原生 Task／Dispatch、人工處理紀錄、舊 request／訊息綁定 | 可查證／回報既有狀態；不能因新 epoch 或沒有 dedup row 自動執行 |
| O05 | 關機後原生專用 Run／Dispatch 或 caller 已變更 | 舊綁定不自動改指新工作；unknown 或待重新映射 | prepared 紀錄、原生 caller／Run／Dispatch 查詢 | 新映射須先查清舊交付；禁止換身分後拿 absent 當安全重送依據 |

## 5. 傳輸、順序、保留與跨平台

| ID | 操作 | 預期狀態及不變條件 | 查證來源 | 自動重試界線 |
| --- | --- | --- | --- | --- |
| T01 | 一般訊息及回覆雙向往返；外網關機後再開機 | FTP 與 itcp／網芳方向正確；未收到可驗證 receipt 前保留 outbox；完成另外回報 | 兩端固定信封、原生訊息、receipt | 未超出可證實的去重／保留範圍時可同 ID 傳輸重試 |
| T02 | 三輪分別收到 seq 1、3、2；同輪多檔；檔案 mtime 故意亂序 | 按完整接收次序交付；同輪用固定檔名順序；seq 異常僅記錄 | ready 驗證／admission 次序、原生入列順序 | 不等待缺號，不按 seq 重排 |
| T03 | 單端／雙端重啟、新 epoch、舊 epoch 延遲檔及舊檔 retry | 新訊息使用新區段；舊 retry 保留原 epoch／ID／seq；dedup 不依 epoch | 信封、重啟 log、原生持久證據 | 不以區段變更重新執行；無可靠基準不猜舊 counter |
| T04 | 同 ID 改 retry、改 JSON 排版／key 順序；再改 body／目的地／seq | retry／排版不構成新工作；固定內容變更為 conflict | RFC 8785 canonical 固定內容 digest 與原始檔 hash | conflict 不自動重試入列 |
| T05 | 網芳 read 卡住、itcp 不退出、單一對端失聯；另一對端正常 | timeout 只表示未知；獨立對端繼續；同 lane 未退出的 sender 不另啟動；receipt 發送不堵收件掃描 | timer、process、各 peer 的進度和佇列 | 可按設定重試獨立通道；無法停止舊 process 則阻擋該 lane |
| T06 | active／idle 切換、大量候選檔及錯誤檔、同一輪超過 batch 上限 | 約 1／5 秒可設定；無重疊掃描；公平掃描不餓死較後檔案／對端；錯誤節流 | polling 時間、掃描輪次、每輪數量、錯誤顯示 | 正常重試；不每秒無限制重建工作 |
| T07 | spool 磁碟滿、權限錯誤、manifest 狀態落盤失敗及 Orca 未啟動 | 不回 receipt、不 ACK 未保存 batch、不發出沒有 prepared 證據的新 mutation | 檔案寫入結果、原生查詢、batch 狀態 | 修復後先查證；未呼叫且證據完整才首次交付 |
| T08 | 原生 receipt 被 prune、中間資料夾清理、receiver spool 遺失或還原舊備份 | 恢復模式；目前可見但無紀錄的舊檔視為 unknown；不得全部當新工作 | 備份／保留設定、雙端 outbox、原生 Task／訊息 | 僅查證；未建立安全 replay horizon 前不自動清理 dedup 證據 |
| T09 | Linux 只能 SSH；分別測允許及不允許 forwarding；SSH 中斷 | 驗證 serve＋browser 的實際功能；不可行時 Windows Orca＋SSH；斷線不等於工作已停止 | 公司版本、連線政策、原生 session／Task | 先查原工作；不因 SSH timeout 另派相同工作 |
| T10 | 一個主節點對多節點；交換錯誤 to／來源；回報假的 worker_done | 各 peer 的 ID／epoch／receipt 隔離；拒絕錯路由及遠端偽造生命週期 | 路由 allowlist、原生權限／Dispatch、各 peer 狀態 | 可修復路由後重送原訊息；權限拒絕不由 bridge 繞過 |
| T11 | 原生 federationImport 收到缺號 relay；外層信封收到 seq 缺號 | 原生測試維持原生拒收；bridge 外層只 log；兩者不互相冒充 | 固定版原始碼、公司版本行為、原生 RPC 結果 | 不改掉原生連續性檢查；完整 federation 適配另案研究 |
| T12 | 不支援版本、缺必要欄位、超出大小上限、路徑穿越／symlink、同名 attempt 不同 bytes | quarantine／明確錯誤；不進 Orca、不回成功 receipt；後續合法檔可被掃到 | 信封 validator、路徑解析、檔案 digest、原生訊息數量 | 修正後建立可追溯的新 attempt；不可覆寫已發布 attempt |

## 6. 公司 Agent 的驗收出口

原型先完成 C01–C09、O01–O05，再跑 T01–T12。任何無法證實的狀態維持 unknown；允許以人工查證結案，但須記錄不能自動恢復的限制。只有文件更新或 mock 成功，不能標記 FTP、itcp、SMB 或公司 Orca 版本 passed。

Review 收斂條件是：每個發現都有設計位置、可觀察結果與測試；實作入口／request replay／檔案保留的未知事項有明確 owner 及阻擋條件。這次僅完成規格層面的補強，未執行新一輪獨立 subagent review，亦不宣稱 reviewer 已零意見。
