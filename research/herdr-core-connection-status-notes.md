# Herdr App／Core：連線與 agent 狀態核實筆記

核對日期：2026-11-01。這份筆記供整體操作指南引用，只記錄已查到的實作、官方發布依據與限制；沒有啟動、停止、更新或安裝任何 App／Core，也沒有呼叫付費 agent。

使用者要的「更新」是看完狀態後，補充或修改 agent 的工作指令。另一台 Windows 禁止使用 SSH；兩台 Windows 之間允許哪些其他通道，目前尚未確定。

使用者後續確認只使用 **Codex**，Claude 沒有付費方案。因此主流程與命令一律以 Codex 為準，Claude 資料僅保留在附錄作版本比較。主 agent 唯讀查得本機 `codex --version` 為 `0.166.0`、`--help` 有 `--no-daemon`；本機未找到 hc／App 的已安裝命令，沒有環境實測。每台執行 Codex 的機器仍需有自己的可用登入與模型權限，不能因本地可用就推論遠端可用。

本機三個 checkout 的 HEAD 與 origin 已核對，研究時 `git status --short` 都沒有輸出：

| Repo | 固定 commit |
|---|---|
| `herdr-core` | `27fea26efe498dce7e1555948fa75c3994fb8a9c` |
| `herdr-app` | `1581a587919dddd6f1efd5f78eb542c4b2b02cb5` |
| 舊 `herdr` | `ee5bfb5041bb3e4a49d591c72308aae3c81ecdde` |

已讀各 repo 的 `AGENTS.md`，根目錄沒有 `AGENTS.local.md`。下文的「支援」以這些固定 commit 為準，不能當成三台機器已部署或已跑通的紀錄。

## 核實結論

| 要求 | 現成支援 | 限制／需要自製 |
|---|---|---|
| 本地 Windows App 連本地 Core，顯示 agent 並補充指令 | 本地 named pipe、terminal 操作、OSC 7501 狀態讀取已有實作。[C1][C2][A1] | agent 必須真的回報狀態；App 顯示另有 pane／labels／parent 條件。[C3][A2] |
| 本地 Windows Core 連 SSH Linux Core | 有 `hc machine add user@host --name linux`；遠端 terminal 以 `linux/t7` 定址。[C4] | 本地需要可用的 `ssh` client，Linux 需要可登入的 SSH server 與相容 Core；Windows 用 keys／SSH agent，沒有共享互動密碼登入。[C5] |
| 另一台 Windows 禁止 SSH，只提供 TCP／HTTPS／WSS | Core 沒有現成對應 listener，也沒有 App 的 URL 連線欄位。[C1][C6][A3] | 需自製安全 transport bridge，且本地原生 Windows Core 的 `--via` 被明確禁止，單補遠端 bridge 還不夠。[C5] |
| 另一台 Windows 只提供共享資料夾／FTP／其他檔案通道 | Core 沒有現成檔案佇列連線模式；Windows named pipe 也拒絕 remote clients。[C6] | 可自製狀態快照＋指令佇列 helper，但它是另一套工作流程；原生 App machine／terminal attach 不會因此成立。[C1][C6][A3] |
| Codex 的狀態 | Codex CLI 0.163.0 官方發布紀錄已列出原生 OSC 7501。[V2] | 發布紀錄不能代替實際版本與執行環境驗收；舊版或不回報者需另評估 agent 升級或自製 OSC adapter。[C3][C7] |

## 1. Core 到底聽在哪裡

Core 的 server 透過平台層 `AsyncListener` 接受連線。Unix 用 Unix domain socket，Windows 用 named pipe。公開文件也明確寫本地 Unix socket、named pipe，以及 `hc connect` 的 stdin／stdout 模式。[C1][C2]

`hc connect` 是既有的原始位元組入口：它連到本地 Core，雙向複製 stdin／stdout，保留 plain 或 framed protocol。它可能因為 Core 尚未啟動而自動啟動 Core，因此這次沒有執行它。[C2][C8]

這版不存在可設定 bind address／port 的 TCP listener、HTTP handler 或 WebSocket handler。這項否定結論是依 server 的唯一 listener 路徑、兩個平台實作、CLI 與 API method table 核對，未把測試裡的 `TcpListener` 或下載 release 的 HTTP 當成對外 API。[C1][C6][C9]

API 是 **JSON-RPC 2.0 一行一個訊息**，並非 HTTP JSON-RPC endpoint。`hello` 加 `framed: true` 後切到 binary framed protocol；`terminal.attach` 要這個模式。frame 包含 channel、kind、length 與 binary payload，另有 credit／close／resize 等訊息。因此，只會轉送一筆 HTTP JSON 的代理，無法直接承擔 App 所用的完整 terminal 連線。[C2]

`HC_SOCKET` 是本地 endpoint override，沒有把它填成 `https://…`、`ws://…`、`host:port` 就切換 transport 的語意。Windows 連線走 `CreateFileW` 開 pipe；建立 pipe 時同時使用 `PIPE_REJECT_REMOTE_CLIENTS` 與 async `reject_remote_clients(true)`，所以 `\\other-host\pipe\…`／SMB named pipe 不是現成捷徑。[C6][C10]

## 2. `machine --via` 的真實契約與 Windows 限制

正常 SSH 模式執行的是本地 `ssh`，帶上遠端 shell line。一般遠端 line 最後會啟動目的端的 `herdr-core connect`，以便取得同一套 protocol。[C5]

`--via` 接受的是**本地命令列**。Core 以 `sh -c` 啟動它，把需要在目的地執行的 shell line 當成最後一個參數。官方契約要求：

- 最後一個參數能在目的端執行。
- stdin 與 stdout 雙向完整保留原始位元組。
- 不提示登入、不要求互動、不開 remote PTY；transport 自己完成認證與信任保證。
- 指定 `--name`；命令是一行，不能含控制字元。[C4][C5][C11]

**原生 Windows 本地 Core 不支援 `--via`。** `machines.rs::check_target` 的條件直接包含 `cfg!(windows)`；即使 Windows 裝了 Git Bash 或 `sh.exe`，這個檢查仍會拒絕。API `machine.add` 跟 CLI 使用相同的檢查，改成直接送 JSON-RPC 不能繞過。[C5][C12]

目的端是 Windows 是另一件事。Core 有 Windows 遠端連線的 command fallback，但透過 `--via` 自動安裝 Windows Core 會回 `install_failed`，提示自行安裝。不要把「Unix 可以使用自訂連線」延伸成「任何平台可自動裝到 Windows」。[C5]

### 為什麼不能直接寫 `--via 'nc winbox 1234'`

`nc` 本身不提供 Core listener、遠端 shell 執行、認證或加密。`--via` 還會附加一整段遠端 shell line；一般 `nc host port` 不會把這個參數拿去 Windows 執行。因此即使本地是 Unix，這個字串也不滿足官方契約。[C4][C5]

如果自製固定連線的 bridge client，刻意接收最後一個參數，然後把 stdio 接到已存在的目的端 `hc connect`，有機會滿足「連線」所需的 raw stream。但必須另外設計及驗收參數處理、session 選擇、binary／framed byte stream、斷線與程序生命週期；忽略最後參數的 fixed-endpoint shim 也不能宣稱支援原本的安裝／更新 shell 操作。這是根據契約推導的實作選項，repo 沒有提供此 bridge。[C2][C4][C5]

### 沒有 SSH server 與沒有 SSH client

| 情況 | 影響 |
|---|---|
| 本地 Windows 沒有 SSH server，但有 SSH client | 不阻擋本地 Core 主動連 SSH Linux。Core 使用本地 `ssh` executable，沒有要求本地 `sshd`。[C5] |
| 本地 Windows 沒有 SSH client | 現成 SSH machine 路徑無法啟動 `ssh`；原生 Windows 的 `--via` 也無法替代。[C5] |
| 目的 Windows 沒有／禁止 SSH server | 現成 SSH machine 路徑不能進去；該 Windows 是否有 outbound SSH client 不會自動形成可被 App 管理的反向 machine 連線。[C5][C13] |
| 只禁密碼登入，仍允許 SSH | keys／SSH agent 是現成 Windows 路徑；但本案使用者已表示另一台 Windows 禁止 SSH，所以不作主方案。[C4][C5] |

`HC_SSH` 在原始碼中的註解是測試替身，不應把改這個環境變數當成正式的 Windows 自訂 transport API。[C5]

## 3. 免 SSH：依允許通道分支

### 分支 A：允許 TCP／HTTPS／WSS 之類持續雙向通道

需要另做 bridge。目的 Windows 上的 helper 可以在使用者帳號下，將已驗證及加密的網路連線接到 `hc connect` 或當地 named pipe。由於本地原生 Windows Core 拒絕 `--via`，要進入**原生 App 的 machine／terminal 模型**，還需要本地 Core 的正式自訂 transport 實作，或另一個確實實作相同 protocol 的客戶端／代理。單純把 Windows listener 開出來、放一個 `nc`、或設定 URL 都不完整。[C1][C2][C5][A3]

HTTPS 方案若採 request／response RPC gateway，可做查詢與送出指令，但 terminal attach、持續 events、framed protocol 仍要另設 streaming／WebSocket 等對應。WSS 方案也要實作 message 與 byte stream 的轉接；WSS 本身不理解 hc frame。[C2]

不能把 Linux Core 已有 `--via`，直接推論成「Windows App 透過它自動看到第三台 Windows 的完整 machine spaces」。Core 的 doc mirror 明確排除遠端再監看的第三台 Core 文件，App 的 machine layout 使用這些 doc；多跳 layout 不在現成保證內。若借 Linux 當 transport relay，仍應將它當作自製代理設計並驗收。[C13][A4]

### 分支 B：只允許共享資料夾／FTP／其他檔案交換

可設計目標 Windows 常駐 helper：

1. 在目標機器用當地 hc 讀取 terminal 狀態與輸出，寫狀態快照。
2. 從允許的檔案通道取得新的工作指令，驗證目標 terminal 與訊息 ID，再在當地呼叫 `hc send`。
3. 寫回已接收、已送入 terminal、失敗原因等結果；狀態與指令需有時間戳、序號與斷線／過期呈現。

這是自製的非同步指令佇列，沒有 repo 內現成元件，也不能只複製 `machines.json` 或 terminal state 檔達成。它可配自製 App mod／外部看板；原生 App 側欄、互動 terminal attach、即時 resize 不會自動取得支援。這是依 Core transport／API 與 App machine UI 契約推導的方案範圍。[C1][C2][C6][A3]

既有需求中的 `itcp` 已知是依指定檔案／路徑傳送的傳檔程式，歸在本分支；不能當成 Core 原生需要的持續雙向 byte stream。公司端仍需查明它的實際命令語法、接收路徑、完成標記與檔案發布是否完整，不需再確認它屬於哪一種類型。

### 自製 transport 的信任邊界

Core 沒有另外的 API 密碼、每個 client 的權限隔離或端到端加密。能連 API 的 client 可以用 Core 帳號執行程式、讀寫檔案、操控 terminal；自訂 transport 必須自己補齊身分驗證、存取控制與加密。這是 repo 公開的既有信任契約，不是可省略的 bridge 細節。[C14]

## 4. Codex 如何回報 OSC 7501

Core 的狀態來源只有 agent 輸出的 OSC 7501；沒有螢幕辨識、agent 廠牌偵測或 per-vendor registry。程式沒有回報時，`status` 就沒有值。`defaults/programs.json` 的 Claude／Codex 名稱與圖示，只是 App 的啟動與顯示資料，不代表它能辨識 agent 的工作生命週期。[C3][A5]

| Agent | 已確認的原生支援證據 | 對這份指南的意義 |
|---|---|---|
| Codex CLI | OpenAI 官方 changelog 的 `0.163.0`，2026-10-15，列出 `#52725 Report terminal program status with OSC 7501`。[V2] | 使用已有這項能力的互動版，在 hc／App terminal 內執行；不必用舊 Herdr 的 session hook 代替狀態協定。 |

這裡只證實上述版本發布過原生能力，沒有聲稱每個未來版本、啟動模式、tmux／PTY 鏈都一定回報，也沒有從發布紀錄推導未記載的強制啟用設定。

固定版本 Core manual 明確要求 Codex 含 templates 都使用 `--no-daemon`，否則其命令會在 hc 外執行；範本以 `command: codex --no-daemon` 啟動。這是 Core 的執行脈絡要求，與 agent 是否會發 OSC report 是分開的條件。[C19]

Core 的 Ghostty VT 測試明確驗證：

- 讀取 `working`、`blocked:kind=permission` 與 `clear` 的 OSC 7501 report。
- agent 發 `ESC ] 7501 ; ? ST` 查詢時，Core 會產生支援回應。
- runtime 將 VT 產生的回應寫回程式的 input。[C7][C15]

Windows release 另帶 `conpty\conpty.dll` 與 `conpty\x64\OpenConsole.exe`。程式碼說明 Windows 內建 ConPTY 會丟棄某些 agent 要接收的 input escape sequences；完整 release 會優先用隨附版本，單一裸 exe 則可能退回內建 ConPTY。所以 Windows 驗收需保留完整 bundle，不能只憑 agent 版本推論 query 能往返。[C16]

### 不要套用舊 `herdr integration install`

舊 `herdr` 有另外一套 `HERDR_ENV`／`HERDR_PANE_ID`／`HERDR_SOCKET_PATH` 與 pane API。核對的舊 repo HEAD 中，Claude hook 只處理 `session`、發 `pane.report_agent_session`；Codex PowerShell hook 也只處理 `SessionStart`、執行 `herdr pane report-agent-session`。它們沒有輸出 OSC 7501。[H1][H2]

新 Core 為 child terminal 設定的是 `HC_TERMINAL_ID` 與 `HC_TERMINAL_SOCKET`，API method table 沒有舊 `pane.report_agent_session`、`integration.install` 或一般 `terminal.set_status`。因此，名稱叫 `herdr-agent-state` 的舊資產不能當成 App／Core 已附帶的狀態 integration。[C9][C17][H1][H2]

若 agent 太舊或不支援 7501，可選擇在授權後評估升級 agent，或自製會在**該 hc terminal 的輸出路徑**發送 7501 的 adapter。Core 可以解析 adapter 輸出的合法 report，但 repo 沒有提供 Claude／Codex 舊版 adapter。hook 的 stdout 常由 agent 自己擷取，不能假設 `printf` 到 hook stdout 就會流到 terminal；wrapper 啟動／結束最多只能證明程序生命週期，也不等於每一輪的 working／blocked／done。[C3][C7][C9]

### 最小驗收方式

下列是建議在後續實際部署時使用的命令，這次沒有執行：

```powershell
codex --version
hc machine ls --json
hc ls --json
hc get linux/t7 --json
hc read linux/t7 --lines 80
hc events --terminal linux/t7 --json
```

以真實的 idle → working → done／idle，以及需要人處理時的 blocked，確認 `hc get` 的 `reported`、`status` 與 `records`。`reported: true` 只表示這個 terminal 曾收到報告，不代表目前一定有 root status；`clear` 會清除，program 結束也會重設 status。`records` 是同一 terminal 內的具名 PSP records，與 `hc run` 建立的獨立 child terminal 是兩個層次。[C18]

Core 的 `turn` 在 root 從 working 離開時增加，包含 done、idle、blocked、clear、結束。不要把 turn 增加解讀成整個任務或所有背景工作都成功完成。對不回報狀態的長駐互動程式，`hc wait` 視為仍在工作，直到程序結束；不能拿它當作每輪完成的替代偵測。[C18][C9]

## 5. `hc ls` 與 App agent 側欄的差別

App 的 `agents()` 主清單從 **spaces → tabs → panes** 取 terminal，且該 terminal 必須已有 status；所以 `hc ls` 中存在某個 root terminal，不表示它會出現在 App 側欄。[A6]

外部用 hc 建立的 root terminal，要讓 App 顯示，有兩條現成路徑：

- 由 App 的 `space.new`／`tab.new`／terminal 指令建立；App 會管理 labels。[A1][A2]
- 用 `herdr.space=<id>` 選 space，選擇性加 `herdr.tab=<id>`；或在同機器的 space 中執行 `terminal.keep` 收納既有 live terminal。[A1][A2][A7]

labels 使用目標機器自己的 local ID。App 顯示遠端 ID 的 `linux/` 前綴要先去掉再寫成遠端 labels；`herdr.tab` 未提供時 App 可建立 tab。App reconciliation 還要求該 machine 的 layout document 可用。[A2][A8]

例子中的 ID 必須從真實 App 查得，不能照抄：

```powershell
herdr-app ls
hc run --bg --on linux --label herdr.space=sp1 --label herdr.tab=tb1 -- codex --no-daemon
```

或先在 App 選到 Linux machine 的 space，再收納那台的 terminal：

```powershell
herdr-app do terminal.keep --terminal linux/t7
herdr-app ls
```

`terminal.keep` 要求 terminal 與當前 space 在同一台 machine，否則回 `A terminal's pane must stay on its own machine.`；若回 `pending: true`，需要再用 `ls` 確認遠端異動真的成功。[A7]

### hc child terminal

由 App 內 agent 的 terminal 呼叫 `hc run`，Core 可記錄 `parent`，也支援跨機 parent；App 的 agents mod 會從 `terminals()` 找 `parent` 對得上的 live children，掛在已出現的 root agent 下。這些 child 不一定要有自己的 App labels。[C17][C13][A9]

遠端 child 可讀自己的 terminal 記錄取得實際 `parent`，再用 `hc send <parent> <摘要>` 沿既有 core 連線回傳。反向 callback 只允許 `send`／`get`／`read`／`wait`，且目的 terminal 必須是啟動這台 machine 工作的 parent；不需要本地 Windows 開 inbound SSH server，也不代表遠端取得任意本地 terminal 的控制權。[C13]

但側欄樹是從 `agents()` 的 root 開始。如果 parent root 本身沒有進 App pane，或 root 沒有 7501 status 而不在 `agents()`，不能保證 child 會單獨冒出來。child 的 status 可提高該 root 列的排序急迫度；child 的 done 會當 idle，因為它向 parent 回報。App 也刻意不對 sub-agent 單獨發完成／blocked 通知。[A6][A9][A10]

### 補充或修改 agent 指令

用完整 terminal address 讀取與送出即可；這是在既有互動 terminal 貼入文字並按 Enter，不是更新 Core／App 程式：

```powershell
hc get linux/t7 --json
hc read linux/t7 --lines 80
hc send linux/t7 "補充：先只修登入流程，保留 API，完成後列出改動與驗證結果。"
```

`hc send` 回報觀察到的狀態；它不是通用工作排程器。正在執行時如何接收 steering／queued input 仍由 agent 處理。blocked 會拒絕普通 send，不應用 `--force` 略過使用者的權限決策。連線中斷期間，attach 的輸入不會被 Core 排隊；不確定上一則是否送達時先讀取，不要盲目重送。[C9][C13][C19]

## 附錄：Claude 的版本比較

Anthropic 官方 Claude Code `v2.1.295` 發布紀錄，2026-10-08，列出新增 Program Status Protocol／OSC 7501。[V1] 主 agent 唯讀查得本機 Claude 是 `2.1.208`，比這項支援的發布版本早；使用者沒有 Claude 付費方案，因此不啟動、不升級、不把 Claude 放入本次工作流程。

## 固定來源索引

### herdr-core @ 27fea26

- [C1：server 啟動與唯一 listener 路徑](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/server.rs#L1-L78)
- [C2：protocol、plain／framed、attach 與 events 契約](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/schema/README.md#L22-L119)
- [C3：狀態只由程式提供](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/README.md#L99-L110)
- [C4：SSH 與自訂連線的公開操作契約](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/docs/machines.md#L8-L61)
- [C5：Reach、via、Windows 拒絕、SSH、dial／install 實作](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/machines.rs)
- [C6：Windows named pipe、拒絕遠端 client](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/platform/windows.rs#L149-L355)
- [C7：7501 report 與 support probe 測試](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/ghostty-vt/src/tests.rs#L156-L172)
- [C8：connect 雙向複製原始位元組](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/cli.rs#L807-L829)
- [C9：完整 API method table 與 send／wait 契約](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api.rs#L55-L157)
- [C10：HC_SOCKET 的 endpoint 選擇](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/paths.rs#L20-L40)
- [C11：MachineAddParams 的 via 參數契約](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api/types.rs#L693-L732)
- [C12：machine.add 實作](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api.rs#L599-L631)
- [C13：遠端 mirror、peer、routing 與中斷期間輸入](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/remote.rs)
- [C14：本地 API 權限與 remote trust](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/docs/security.md#L1-L61)
- [C15：VT 回應回寫至程式](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/runtime.rs#L428-L456)
- [C16：Windows bundled ConPTY 選擇及 fallback](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/platform/windows.rs#L704-L741)
- [C17：parent 與 HC_TERMINAL_ID／HC_TERMINAL_SOCKET](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api/run.rs#L110-L225)
- [C18：status、records、clear、turn 與 exit reset](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/status.rs#L1-L145)
- [C19：代理人的 read／send／ready／blocked 操作守則](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/SKILL.md)

### herdr-app @ 1581a58

- [A1：App CLI、remote space、labels 的操作手冊](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/SKILL.md#L1-L77)
- [A2：labels、machine local ID 與 child terminal 契約](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/AGENTS.md#L135-L159)
- [A3：machine-add UI 呼叫 SSH machine.add](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/machine-add/main.js#L83-L108)
- [A4：machine documents 與 layout mirror](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/mirror.rs)
- [A5：App program names／run／icons](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/programs.json#L1-L10)
- [A6：由 App panes 產生 agents 清單](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L1605-L1658)
- [A7：terminal.keep 同 machine 檢查與非同步 labels 修改](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2424-L2485)
- [A8：reconcile labels 與 machine document available 條件](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2015-L2044)
- [A9：agents mod 的 parent tree、排序、child done 規則](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/agents/main.js#L39-L248)
- [A10：App 的 seen／done／idle 與 sub-agent alert 規則](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/model.rs#L437-L518)

### 舊 herdr @ ee5bfb5

- [H1：Claude hook 使用舊環境與 pane.report_agent_session](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/integration/assets/claude/herdr-agent-state.sh#L1-L106)
- [H2：Codex hook 使用 herdr pane report-agent-session](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/integration/assets/codex/herdr-agent-state.ps1#L1-L55)

### Agent 官方版本依據

- [V1：Anthropic 官方 Claude Code v2.1.295 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.295)，已實際讀取發布內容。這是版本發布依據，沒有啟動 Claude。
- [V2：OpenAI 官方 changelog，Codex CLI 0.163.0／2026-10-15／PR #52725](https://learn.chatgpt.com/docs/changelog?date=2026-10-15)，已實際讀取官方頁面。這是版本發布依據，沒有啟動 Codex。

[C1]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/server.rs#L1-L78
[C2]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/schema/README.md#L22-L119
[C3]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/README.md#L99-L110
[C4]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/docs/machines.md#L8-L61
[C5]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/machines.rs
[C6]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/platform/windows.rs#L149-L355
[C7]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/ghostty-vt/src/tests.rs#L156-L172
[C8]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/cli.rs#L807-L829
[C9]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api.rs#L55-L157
[C10]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/paths.rs#L20-L40
[C11]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api/types.rs#L693-L732
[C12]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api.rs#L599-L631
[C13]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/remote.rs
[C14]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/docs/security.md#L1-L61
[C15]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/runtime.rs#L428-L456
[C16]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/platform/windows.rs#L704-L741
[C17]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api/run.rs#L110-L225
[C18]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/status.rs#L1-L145
[C19]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/SKILL.md
[A1]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/SKILL.md#L1-L77
[A2]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/AGENTS.md#L135-L159
[A3]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/machine-add/main.js#L83-L108
[A4]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/mirror.rs
[A5]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/programs.json#L1-L10
[A6]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L1605-L1658
[A7]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2424-L2485
[A8]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2015-L2044
[A9]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/agents/main.js#L39-L248
[A10]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/model.rs#L437-L518
[H1]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/integration/assets/claude/herdr-agent-state.sh#L1-L106
[H2]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/integration/assets/codex/herdr-agent-state.ps1#L1-L55
[V1]: https://github.com/anthropics/claude-code/releases/tag/v2.1.295
[V2]: https://learn.chatgpt.com/docs/changelog?date=2026-10-15
