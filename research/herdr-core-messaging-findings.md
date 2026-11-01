# herdr-core 訊息、等待與失敗處理查核

本地checkout補查：使用者已下載 `C:/Users/swche/orca/projects/orca_study/herdr-core`，HEAD為 `27fea26efe498dce7e1555948fa75c3994fb8a9c`，查核時工作樹乾淨。與下方固定基準 `7a54c2975225a859b7e7d67302df5efc249fb9d0` 相比，僅新增一個測試清理commit，變更檔案為 `crates/herdr-core/src/runtime/tests.rs`；未變更本報告分析的runtime/API/通訊實作，因此以下結論不因這項差異而改變。此補查未執行測試或產品。

查核範圍固定為官方 repository `herdrdev/herdr-core` 的 commit `7a54c2975225a859b7e7d67302df5efc249fb9d0`。原始碼與文件以 `gh api repos/herdrdev/herdr-core/contents/<path>?ref=<commit>` 取得，以下連結全部鎖定該 commit。這是靜態原始碼與既有測試查核，沒有啟動真實 Codex／Claude Code，也沒有執行測試。

## 結論

Codex 與 Claude Code 的互通方式是：其中一個 agent 執行 `hc send <terminal> <text>`，經 herdr-core 的通用 API 把文字送進另一個 agent 的 terminal 輸入。實際動作是 paste、短暫等待、submit，通常為 Enter。接收者透過自己的互動式 CLI 處理文字。這條路徑的核心原始碼沒有 Codex 對 Claude 的專用模型協定；使用的是同一個 `terminal.send` handler 與 PTY 輸入機制。`hc send` 不能解讀成可獨立取件、確認收件、重播內容的 agent inbox API。[API handler][api-send]、[送入 terminal 的實作][input-send]、[holder 寫入 PTY][holder-pty]

```text
Codex／Claude Code 執行 hc CLI
  → 本機 core 的 JSON-RPC terminal.send
  → 目標 terminal 的輸入序列化 queue
  → core-to-holder INPUT frame
  → holder 的 PTY writer
  → 另一個互動式 agent CLI 的輸入

若目標是 machine/t7：
  本機 core → framed JSON-RPC／SSH 的 stdin/stdout → 遠端 core
  → 遠端 holder → 遠端 agent PTY
```

長篇結果由 child 寫檔，再用 `hc send parent "摘要與檔案路徑"` 回報。正常 `done` 的成果文字需要 child 主動回報；core 自動產生的注意通知針對 blocked、error 與 program exit。[使用手冊][manual-report]、[明確驗證 done 不自動 note 的測試][test-notes]

## 1. 官方文件的角色

後續操作補查：[Codex 多機指南](herdr-codex-multimachine-guide.md)、[連線與狀態筆記](herdr-core-connection-status-notes.md)。其中新增原生 Windows 呼叫端拒絕 `--via` 的 source 證據，以及新版 Codex／Claude 原生 OSC 7501 的發行證據。使用者實際方案只用 Codex；template 本身不會安裝或啟用 agent 狀態支援。

- `skills/herdr-core/SKILL.md` 只有短版入口，要求使用前讀 `hc --skill`。完整 manual 放在 `crates/herdr-core/src/SKILL.md`，官方 `AGENTS.md` 明確區分這兩者。[短版 skill][skill]、[官方規則][agents-manual]
- `docs/commands.md` 將 `send` 定義為 paste + Enter，`--wait` 等待該 send 開始的 turn，timeout 預設取 config，否則 180 秒。[send 命令][commands-send]
- `schema/README.md` 定義 JSON-RPC、plain/framed connection、event stream；它把 terminal 的 status 定義為 program 報告的 OSC 7501 資料，core 不從畫面猜測。[transport 規格][schema-connect]、[status 規格][schema-status]
- 完整 manual 要求 interactive agents，並要求 Codex 使用 `--no-daemon`，否則它執行的 commands 會離開 hc。[互動式模式][manual-launch]、[Codex 限制][manual-codex]

## 2. Stack 與 wire protocol

| 層次 | 固定 commit 的行為 | 證據 |
|---|---|---|
| CLI → 本機 core | Unix socket；Windows named pipe。CLI plain call 寫一行 JSON-RPC 2.0，等待一行 response。 | [schema][schema-connect]、[client::call][client-call] |
| plain mode | 每行一則 JSON-RPC message。`id` 配對 response。 | [schema][schema-connect] |
| framed mode | 成功 `hello {framed:true}` 的 response 之後切換。header 是 `[channel u32 LE][kind u8][len u32 LE][payload]`，payload 最大 16 MiB。channel 0 是 JSON-RPC；其他 channel 承載 streams。 | [schema][schema-frames] |
| stream 控制 | DATA、CREDIT、CLOSE、RESIZE、FOCUS、FACTS；attach 需要 framed。初始 credit 256 KiB，viewer 落後超過 4 MiB 用 repaint 取代 backlog。這是 viewer stream 的流量控制，不能當成 agent 訊息 ACK。 | [schema][schema-streams] |
| 跨機器 | `hc connect` 在 stdin/stdout 上橋接同一協定。預設 SSH 執行遠端 `herdr-core connect`；本機 core 維持一條 framed line。 | [schema][schema-connect]、[遠端 line][remote-line]、[SSH 啟動][machines-pipe] |
| SSH 與 PTY | SSH bridge 使用 pipes，設定 BatchMode、ConnectTimeout 與 keepalive。文件要求 stdout 保持純 byte protocol，custom connection 不得要求 remote PTY。agent 本身仍由目的地 holder 在 PTY 中啟動。 | [SSH 原始碼][machines-pipe]、[操作文件][machines-errors]、[PTY spawn][holder-pty] |
| core → holder | 另一個內部 binary framing：`[kind u8][terminal u32 LE][len u32 LE][payload]`；control 是 JSON，terminal bytes 是 raw。INPUT 的 kind 為 3。不要與外部 channel-first framing 混為一談。 | [holder protocol][holder-proto] |

JSON-RPC response 的 `id` 只對應呼叫。遠端 `Line.pending` 用 `id` 找到正在等待的 response；本機 CLI 每個 plain call 都使用 `id:1`。不能由 JSON-RPC 這個名稱推導出訊息去重或交易保證。[遠端 pending map][remote-calls]、[本機 call][client-call]

## 3. hc send 的文字與 queue

`SendParams` 有 `terminal`、`text`、`force`、`if`、`wait`、`timeout`、`caller`，沒有 message id、idempotency key 或 ack token。回傳的 `status` 是貼入當時的狀態，`turn` 是貼入當時的 counter，`started` 是短時間內有沒有觀察到 working／turn 推進；它不等於 LLM 已讀取、理解或完成該文字。[API types][send-types]、[send implementation][input-send]

每個 terminal 有一個 async mutex queue，讓 send、keys、interrupt 的輸入序列不交錯。送入前等待人停止打字，預設 3 秒；送入過程的人類按鍵暫存，完成後補回。若 agent 要求 bracketed paste，core 使用該格式；預設 paste 後 200 ms 再 Enter，template 可覆寫 submit key 與 gap。[輸入 gate][input-gate]、[送入 queue][input-queue]、[paste 與 submit][input-send]

agent-to-agent 文字可包上 `<hc from="t7 review">…</hc>`；首個任務可以加 `reach="hc send t3 when done or stuck"` 提醒回報地址。只有被識別為曾回報狀態的 agent 才符合一般 tagging 條件，shell／dialog 文字可保持原樣；`notes=false` 也會關掉自動 tag。[tagged][notes-tagged]

若目標原本處於 `working`，`terminal_send` 額外記一個 `messages[target]=sender`，讓 parent 正在執行的 wait 以 `reason:message` 返回。**該 map 只存寄件者標記，不存本文**；本文已送進接收 agent 的輸入，可能要等它下一次能處理時才出現。manual 明確要求收到這種 wait result 後處理下一則輸入，不要以 `hc read` 尋找「訊息本文」。[API 的 message marker][api-send]、[wait consumption][wait-body]、[manual][manual-wait]

## 4. child attention／done notes 的投遞

正常成果與異常通知是兩條行為：

| 情況 | 如何讓 parent 知道 |
|---|---|
| child 完成一個 turn、仍為 live agent，status=`done` | child 明確 `hc send parent "結果"`；`--children any` 也可回傳 unseen turn news，但不會替 child 寫成果摘要。 |
| child blocked／error | core 產生 `<hc>t7 … is blocked … See: hc read t7</hc>` 或 error note。 |
| child process exit，含 exit 0 | core 產生 exit note；一般程式可附最後 20 個非空白行，每行最多 300 characters。 |

以上由 `unseen` 的條件 `news > max(seen,noted)` 且 `(stuck || !live)` 決定；既有測試明確驗證 done 不自動 note，以及同一 piece of news 不重複 note。[note 判定與格式][notes-format]、[unseen filter][notes-unseen]、[測試][test-notes]

parent 必須 live、曾報 OSC status，且目前不為 blocked；working parent 也能收文字。core 在輸入前重新建立 note batch，避免已看過的舊 news 又被投遞。實際投遞仍使用 `type_in`、paste、200 ms、Enter；parent 忙或狀態變動時會留待重試，沒有另外的 model-side inbox。[可收件條件][notes-can]、[投遞 loop 與 type_note][notes-delivery]

parent 正在 wait 某 child 時，`waiting[(caller,child)]` 會抑制相同 child 的自動 note；wait 已返回的結果記為 seen。child 主動向自己的 parent send 時設定 `told_parent`，其後正常 turn end 會記為 seen，避免同一回報又成為 unseen news。[waiting guard][waiting-guard]、[send bookkeeping][api-send]、[news bookkeeping][notes-news]；[對應測試][test-told]

## 5. parent-child wait 與 turn 配對

turn 是 terminal 的觀察計數器：root status 每次從 working 離開就加一，包括 done、idle、blocked、clear、exit；不是每則訊息的唯一 ID。[counter][status-turn]、[terminal 欄位][terminal-record]

`hc send --wait` 保留 send 當時的 turn，再以 `after_turn=sent.turn` 等待。若 child 在 wait 正式開始前已完成，`current.turn > sent.turn` 會立即返回，避免漏掉很快完成的 turn；若仍停在上一回合的 idle，不會把舊 idle 當成本次完成。[API handler][api-send]、[wait 的起始判斷][wait-body]

後續獨立執行的裸 `hc wait <t>` 會查 `(caller,target)` 的 `last_send`，沿用同一個 after_turn。timeout 不刪除它；完成後才刪除，且若期間有較新的 send 已覆寫值，舊 wait 不會刪掉新值。CLI 的 caller 取 `HC_TERMINAL_ID`，沒有時取呼叫程序的 parent PID。[last_send lifecycle][waiting-turn]、[caller][cli-caller]

這是「同一 caller 最近一次 send 對應的 terminal turn」配對，不能當成並行多則訊息的逐筆 correlation。map 每個 `(caller,target)` 只有一個值，turn 又以 program status 計數；例如 target 已 working 時再 send，文字仍可能加入同一 turn。[State][runtime-maps]、[API handler][api-send]、[counter][status-turn]

| wait 模式 | 返回條件與界線 |
|---|---|
| 單一 terminal | stopped working、blocked/error、exit/lost，或 timeout。純程式未報 status 時，通常等待 exit。 |
| `--output X` | 只比對 wait 開始後的 output；blocked/error/exit 也會結束。 |
| `--children all` | 當下沒有 working child；live 但尚未回報 status 的 child 算仍在啟動。結果也列 finished children。 |
| `--children any` | parent 尚未見過的 news，含 wait 之前就產生的 news；若無 news，繼續等下一次 child 變化。idle children 仍可被等待。 |
| parent 收到 message | wait 可提前返回 `reason:message`，child 可能還在工作，之後需繼續 wait。 |
| 跨機器 children | local 與曾啟動工作之遠端 machines 一起等；`any` 取最先 news，`all` 合併結果。無法連線的 machine 會被略過，因此返回不等於所有可能遠端工作已成功。 |

證據：[wait 實作][wait-body]、[children 等待][waiting-children]、[跨機器 merge][waiting-everywhere]、[命令文件][commands-wait]

## 6. timeout、錯誤與安全重試

| 情境 | 實際處理 |
|---|---|
| wait timeout | `ended:false, reason:timeout`，預設 180 秒；program 留在執行中。再次 wait，不必重新 launch／send。 |
| send 未觀察到 working | 預設觀察窗口 5 秒；`started:false`，若帶 `--wait` 則回 `not_started`。這只表示尚未觀察到開始，manual 要求先 read 再決定。 |
| booting agent | send 額外等待 output settle，最多 5 秒；失敗明說 nothing was typed。manual 建議首個 task 放進 run，並檢查 `first_message.sent`。 |
| blocked dialog | send 預設以 `kind:blocked` 拒絕，`--force` 可覆寫；`--if idle/working` 在輸入前比對，不符為 `status_mismatch`、nothing was typed。 |
| program 已結束 | `finished`；kept terminal 正在等待新 shell 時為 `unavailable`，待 `restarted` 再試。 |
| registry flush 超時 | 10 秒後回 `unavailable`，訊息明說 operation may already have completed，要求先檢查 terminal／disk。 |
| 遠端 RPC line 在呼叫中斷 | pending 呼叫立即失敗為 `unavailable`，明說 it may have happened there；一般 send 不會自動重送本文。 |

證據：[wait][wait-body]、[send/settle][input-send]、[啟動 manual][manual-launch]、[recovery 規格][schema-recovery]、[registry flush][runtime-save]、[遠端 call][remote-calls]、[forward mode 分流][remote-forward]

官方 manual 特別要求失敗 send 先讀取 target，因為內容可能已抵達；不要直接盲目重送。[manual][manual-launch]

錯誤走 JSON-RPC error，含 code、message，以及 `data.kind`／`data.hint`。CLI 對應穩定 exit codes，例如 not_found=3、unavailable=5、blocked=9、status_mismatch=10、finished=11。這個 envelope 能讓呼叫端判斷下一步，但不提供工作 rollback。[RpcError][rpc-error]

## 7. 斷線、去重與重啟保留範圍

**能確認的是局部的重連、記帳與持久化；不能確認一般 agent 訊息具備 exactly-once。** 原因是 send 無 idempotency key、文字直接輸入 PTY，且 delivery 與記帳跨越多個非交易步驟。[SendParams][send-types]、[type_in][input-queue]、[Link::input][runtime-link]、[server dispatch][server-dispatch]

| 項目 | 能確認 | 不應延伸的保證 |
|---|---|---|
| remote connection | core 自動重連，初始 backoff 250 ms，失敗加倍到預設 30 秒；成功後重新建立 events snapshot。 | 重新連線不代表自動重送一般 send。 |
| waited remote `send`／`wait`／`run` | 若是 lost-line，原本 deadline 內等待重連，接著再呼叫 `terminal.wait`。run 另用 `hc.run` label 找回原 terminal，避免重開原程式。 | send 的本文不會在這個恢復 loop 再送一次；若原 send 未完成，恢復邏輯不能保證原任務確實開始。 |
| remote child 自動 notes | 連線離線時放入 `Peer.outbox`，原子寫 `peers.json`；peer 重連後排出。既有測試涵蓋離線 note 經遠端 core restart 仍送到。 | outbox 是自動 notes 的離線保存，不能套用成一般 `hc send` 的持久 inbox。 |
| 正在線上的 remote note | JSON-RPC notification 沒有 id；接收端把本文存進 `afar_notes` 後排 Job，再用 terminal 輸入送 parent。 | 沒有端到端 note receipt ACK；送出端排送前就更新 noted，重連時 outbox 也在排入 line 後清除。不能保證任意中斷點都不漏／不重複。 |
| note 去重 | registry 的 news、seen、noted、told_parent 抑制已 seen／noted 的通知；單次正常流程有對應測試。 | 這是 child news 去重，不是對任意 message text／request id 的去重。 |
| core restart | `terminals.json` 保存 terminal record，含 turn 與上述 news counters；`peers.json` 保留離線 notes。holder 持有 PTY 與 process，可讓 core restart 不終止它們。 | `last_send`、`waiting`、`messages`、`afar_notes` 是 runtime State；startup 只載入 reg/docs/machines/peers，其餘 Default，因此這些記憶體配對與待投文字不會直接持久化。 |
| crash 期間 turn | core 從 holder output tail 重建狀態；非 exact restore 時最多補計一個可能在 crash 期間結束的 turn。 | 不能宣稱 downtime 中的每個 turn 都有完整 replay。 |
| event subscriber | seq 遞增；落後得到 missed + fresh snapshot；seq 隨 core process 重啟，reconnect 要重新取 snapshot。 | event stream 不是所有 missed changes／訊息的永久日誌。 |

證據：[重連][remote-reconnect]、[events 與 line loss][remote-hold]、[waited operation 恢復][remote-forward]、[peer outbox][remote-outbox]、[遠端 notes 接收][remote-notes-in]、[noted 更新][notes-afar]、[note 去重][notes-unseen]、[runtime 初始化][runtime-start]、[State maps][runtime-maps]、[record serialization][terminal-record]、[crash 重建][runtime-adopt]、[event 規格][schema-events]、[離線重啟測試][test-offline]

取消也有界線：遠端 call 放棄時會送 `$/cancelRequest`；server 的該 handler 只追蹤、abort `machine.exec` tasks。不能把這個機制概括成任意 send／wait 的取消或 rollback。[Asked::drop][remote-calls]、[server cancel handler][server-cancel]

尚未查證本機在 core crash 前已排定、但尚未輸入 parent 的 note jobs，是否會在 startup 全數重新排程。已確認 counters 可持久化，不能據此宣稱所有待投 note 都能 replay。也未驗證每個 crash timing、OS shutdown 或 agent CLI 內部輸入 queue 的耐久性。

`hc keep` 是失去 program 後補一個 shell，原 task 不會重跑；它處理 terminal 恢復，不提供 agent 任務 replay。[recovery 規格][schema-recovery]

## 8. 建議用於比較報告的精確用語

> herdr-core 用通用 JSON-RPC 控制 terminal，agent 的文字往來經 PTY paste／submit。它以 OSC 7501 status、terminal turn 與 parent-child news 記帳協助等待及通知；child 的成果通常用 `hc send` 主動回報。跨機器連線可自動重連，等待可續接，離線自動 notes 有持久化 outbox；一般文字 send 不具可證明的 exactly-once 或持久 inbox 保證。

[skill]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/skills/herdr-core/SKILL.md#L6-L15
[agents-manual]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/AGENTS.md#L17-L20
[manual-launch]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/SKILL.md#L24-L51
[manual-report]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/SKILL.md#L82-L98
[manual-wait]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/SKILL.md#L64-L80
[manual-codex]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/SKILL.md#L201-L204
[commands-send]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/docs/commands.md#L518-L535
[commands-wait]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/docs/commands.md#L626-L655
[schema-connect]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L21-L43
[schema-frames]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L42-L59
[schema-streams]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L61-L81
[schema-events]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L141-L147
[schema-recovery]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L118-L139
[schema-status]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/schema/README.md#L184-L189
[client-call]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/client.rs#L230-L244
[api-send]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api.rs#L432-L474
[send-types]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api/types.rs#L427-L465
[input-gate]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/input.rs#L10-L85
[input-queue]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/input.rs#L102-L152
[input-send]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/input.rs#L154-L243
[holder-proto]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/holder_proto.rs#L1-L32
[holder-pty]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/holder.rs#L338-L365
[runtime-link]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/runtime.rs#L129-L138
[notes-format]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L38-L109
[notes-can]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L54-L58
[notes-tagged]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L139-L163
[notes-unseen]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L165-L176
[notes-news]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L111-L135
[notes-afar]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L189-L205
[notes-delivery]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/notes.rs#L235-L305
[wait-body]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/wait.rs#L108-L187
[waiting-turn]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api/waiting.rs#L14-L39
[waiting-guard]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api/waiting.rs#L42-L92
[waiting-everywhere]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api/waiting.rs#L131-L190
[waiting-children]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/api/waiting.rs#L193-L287
[cli-caller]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/cli.rs#L711-L714
[status-turn]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/status.rs#L70-L122
[terminal-record]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/terminals.rs#L57-L97
[runtime-maps]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/runtime.rs#L46-L100
[runtime-start]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/runtime.rs#L163-L195
[runtime-save]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/runtime.rs#L220-L239
[runtime-adopt]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/runtime.rs#L429-L477
[remote-line]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L1-L4
[remote-calls]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L32-L141
[remote-reconnect]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L185-L273
[remote-hold]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L321-L426
[remote-notes-in]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L550-L585
[remote-outbox]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L589-L681
[remote-forward]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/remote.rs#L933-L1047
[machines-pipe]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/machines.rs#L212-L232
[machines-errors]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/docs/machines.md#L102-L112
[server-dispatch]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/server.rs#L392-L428
[server-cancel]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/server.rs#L300-L374
[rpc-error]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/src/rpc.rs#L14-L69
[test-notes]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/tests/m6.rs#L86-L111
[test-told]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/tests/m6.rs#L257-L273
[test-offline]: https://github.com/herdrdev/herdr-core/blob/7a54c2975225a859b7e7d67302df5efc249fb9d0/crates/herdr-core/tests/remote.rs#L247-L257
