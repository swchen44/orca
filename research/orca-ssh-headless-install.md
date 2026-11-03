# Orca：Windows 經 SSH 連內網 Headless Linux

整理日期：2026-11-04。依 upstream `stablyai/orca` commit `11baf7a82e6a5a636dd7216342653b4e6c6639e4` 分析。這比前面的 Orca workspace 文件研究版本新；舊版 relay 流程不應直接套用。本文未部署到公司主機，也未測試 mirror 或認證。

## 1. Linux 會裝什麼？

SSH 首次部署的主體是 **managed orcad server bundle + 固定版本 Node 執行檔**，不需要 Linux 圖形桌面，也不是在遠端執行一般 `npm install orca` 或 `pip install`。

| 元件 | 作用 | 從哪裡取得 |
| --- | --- | --- |
| `orcad.js`、`orcad-server.js`、CLI、各 worker | 遠端工作區、RPC、檔案／session 等功能 | Windows Orca 隨附的 target template，在本機組裝、校驗後上傳。 |
| `daemon-entry.js`、node-pty 及目標平台的 `pty.node` | 背景 PTY／agent 程序 | 同一 bundle，使用預建原生模組。 |
| `@parcel/watcher` JS／native、ripgrep `rg` | 檔案監看與搜尋 | 同一 bundle。 |
| 其他資源 | mobile web、hook／computer sidecar 等；browser native 是否包含取決於 bundle | 依 artifact manifest 部署；不代表所有可選功能已配置可用。 |
| 固定 Node runtime | 執行 server 和相關程式 | 先在 Windows 取得並上傳，失敗才嘗試由 POSIX host 下載。 |

原碼依據：[artifact manifest][S1]、[bundle 本機組裝][S2]、[遠端安裝][S3]。

此 commit 的 Node pin 是 **24.22.1**。例如 Linux x64 glibc 使用 `node-v24.22.1-linux-x64.tar.gz`；其他 CPU/libc 使用其他檔案。runtime 安裝會從 archive 提取 Node 執行檔並驗證版本／SHA-256，不是把主機既有 npm 裡的任意 Node 當成相同 runtime。[Node pin][S4]、[runtime 安裝][S5]

一般登入 home 放置示意：

```text
~/.orca-remote/
├── orcad-<version+hash>/
│   ├── orcad.js
│   ├── orcad-server.js
│   ├── daemon-entry.js
│   ├── node_modules/...
│   └── ripgrep/linux-x64/rg
└── runtimes/
    └── node-<sha256>/bin/node

~/.orca/                          # 狀態資料，與部署檔分開
```

Shared home／machine-specific 配置會另選 machine home，以上不是所有主機的固定絕對路徑。[版本目錄][S6]、[home 決策][S7]

安裝利用 SFTP 上傳；SFTP 不可用或路徑不可見時可改走 SSH exec stdin 傳輸。POSIX launch 以帳號權限用 `nohup` 等背景啟動，記錄 PID、readiness、log；這條流程不等於自動建立 systemd service。[傳輸][S8]、[啟動][S9]

Git、Android `repo`、公司 build tools、Codex／Claude 和 API 憑證仍需在 Linux 可用；不應把 server bundle 的部署成功當成公司開發環境也已配置。

## 2. Linux 不能連外，但 npm／pip mirror 可用

原碼的 runtime 取得順序：

1. 檢查 Linux 是否已有可校驗的 managed runtime。
2. 缺少時，Windows 先檢查本機 archive cache／下載來源。
3. Windows 取得成功，經 SSH 上傳給 Linux，Linux 解壓、驗 hash、執行 self-test。
4. Windows 取得失敗，POSIX host 才以 curl／wget 嘗試下載。host 的 mirror 值來自 Windows Orca 的設定，接著可嘗試固定上游來源。[下載與上傳流程][S10]

因此，**Linux 無法連外不一定阻擋部署**。Windows 若能取得正確 bytes，Linux 只需接收上傳並執行。

但 npm registry mirror 和 pip index 不是 Node distribution mirror：此流程不靠 npm／pip 下載 Node。官方來源的 archive mirror URL 形狀為：

```text
<Node.js download mirror>/v24.22.1/node-v24.22.1-linux-x64.tar.gz
```

設定位置：**Windows Orca → Settings → Advanced → Network → Node.js download mirror**。也可由 Windows Orca 程序環境讀 `NODEJS_ORG_MIRROR` 或 `NVM_NODEJS_ORG_MIRROR`。不是只設定 Linux 的 npm registry 就會生效。特定 unofficial target 不套用官方 distribution mirror；實際依 CPU/libc pin 選擇。[mirror 規則][S11]

若兩端都不能下載，錯誤訊息提供離線 archive cache 路徑。預設 cache root 在 Windows Orca userData 的 `orcad-artifacts` 下，archive 在 `node/archives/<filename>`；依錯誤提供的確切位置放入核准的原始 archive，下一次會校驗 hash。這不是任意修改或重新打包 archive 都能通過。[cache／離線提示][S12]

Linux 還需相容 CPU/libc、可寫且可執行的部署位置，以及解壓／校驗需要的工具。僅有 npm 或 pip 可執行，不能保證符合條件。Node runtime 和 `rg`、`.node` 等仍是 binary，需符合公司執行政策。

## 3. 已有 daemon，為什麼還要 SSH？

**daemon 負責執行工作；SSH 負責遠端進入、部署、管理和運送資料。** managed server 預設只 bind `127.0.0.1`，Windows 無法直接從網路連到這個 Linux loopback endpoint。[bind 設定][S13]

```text
Windows Orca
  │ 本機 loopback endpoint
  │
  └── SSH 加密通道 ───────────────────→ Linux sshd
       通常是 TCP forwarding                   │
       或 SSH exec stdio bridge                ↓
                                    Linux 127.0.0.1:<server-port>
                                               │
                                               └── managed orcad → PTY daemon → agents/build
```

SSH 的職責包括：帳號登入／驗證、執行部署及啟停指令、上傳檔案、建立 Orca server 通訊通道，以及需要時轉送開發服務埠。server 的 RPC 仍有自己的配對／身份驗證；SSH 不是把 Orca server 改成無認證服務。

此 commit 的 tunnel 先嘗試 TCP forwarding；無法建立有效轉送時，若可用則改用 **SSH exec 的 stdio bridge**，再由 host 內的 bridge 連 loopback server。因此 `AllowTcpForwarding` 並非此版本的絕對必要條件，但 SSH exec／通道仍須能工作，不能保證任何封鎖政策都能通過。[tunnel 選擇][S14]、[stdio bridge][S15]

這也修正先前說明中「拒絕 forwarding 就一定無法連」的過度簡化。daemon 可維持程序，不代表 Windows 已有到它的網路路徑；SSH 中斷時，Windows 需重建通道才能重新操作。真正 crash／重開機不代表原 build 自動復活。

## 4. 另一台 Windows 要不要 SSH server？

| 操作方式 | 目標 Windows 需要什麼？ | 需要 sshd？ |
| --- | --- | --- |
| Windows A 的 Orca → Settings → SSH → Windows B | B 有可登入的 SSH server；Orca 部署 Windows target 的 managed server/runtime | **需要**。這是 SSH target 模式。 |
| A → 直接配對 B 的 Remote Orca Server | B 自行安裝 Orca，開桌面 server 或 `orca serve`，並允許 A 連到 Orca endpoint | **不需要**，除非另選 SSH 當承載通道。 |

Windows target 並非只靠推測：source 定義 win32 x64／arm64，CI 有真實 Win32-OpenSSH、cmd／PowerShell host 測試。Windows managed bundle 包含 `node.exe`、ConPTY／process-tree 等對應 binary；仍要符合帳號、解壓及程序啟動政策。[平台實作][S16]、[Windows SSH CI][S17]

Windows `orca serve` 的內建 service 安裝器目前未支援，需要長期服務時要另行管理程序；這不影響 Windows 可作為 SSH target。以上「控制」指遠端 repo、terminal 和 agent 等 Orca 工作，不等於 RDP 或整個 Windows 桌面的遠端滑鼠控制。[Windows service 限制][S18]

## 5. Linux 沒有 SSH server，Windows 能自動裝 Orca Server 嗎？

**不能透過上述 SSH 自動部署流程安裝。** 該流程需要先成功登入 SSH，才能上傳 bundle、執行安裝與啟動命令；沒有可用的 sshd，就沒有這條部署通道。Windows 已裝 Orca，不代表能直接把程式裝進任意 Linux 主機。[遠端部署][S3]

有兩種安排：

| 安排 | 第一次如何部署 | 後續連線 |
| --- | --- | --- |
| 啟用 Linux SSH server | 先由管理者或其他既有管道準備 sshd，Windows Orca 才能自動部署 managed server。 | 經 SSH tunnel／stdio bridge。 |
| Linux 自行準備 Orca Server | 經 Linux console、管理平台、核准的檔案交付等既有方式，先安裝可用的 Orca runtime，再啟動 headless server。 | Windows 直接配對 Orca Server；不需要 sshd，但服務 endpoint 必須可達。 |

第二種方式的 headless 啟動範例：

```sh
orca serve --pairing-address <Linux可達的內網IP或主機名>
```

這個命令的前提是 Linux 已有可用的 Orca 安裝；它不會替一台完全未配置的主機遠端安裝。啟動後取得 pairing link，再到 Windows Orca 的 Remote Orca Servers 加入；依實際 listener、網路與防火牆設定確認連線。內網不必為此開放公網存取。[Remote Orca Server 文件][S19]

`orca serve` 會選擇可用的 server runtime，不能保證任何安裝都走純 Node 路徑；該版本存在 native preflight 失敗時退回 Electron、以及有下游 SSH targets 的 profile 選用 Electron 的邏輯。因此 headless Linux 要依核准的安裝方式驗證 runtime，而不是單憑有 Node/npm 就判定 server 已可執行。[serve 選擇原碼][S20]

## 固定版本來源

[S1]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/shared/orcad-artifacts.ts
[S2]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/orcad/orcad-artifact-materializer.ts
[S3]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/orcad-remote-install.ts
[S4]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/shared/node-runtime-pin.ts
[S5]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/orcad-remote-node-runtime.ts
[S6]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/remote-versioned-install.ts
[S7]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/orcad-remote-context.ts
[S8]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/remote-install-transfers.ts
[S9]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/orcad-remote-launch.ts
[S10]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/install/remote-node-runtime-host-download.ts
[S11]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/shared/node-dist-mirror.ts
[S12]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/node-runtime/pinned-runtime-materializer.ts
[S13]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/lifecycle/orcad-managed-runtime-context.ts
[S14]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/lifecycle/orcad-managed-tunnel-transport.ts
[S15]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/managed-server/lifecycle/orcad-stdio-bridge-script.ts
[S16]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/ssh/ssh-remote-platform.ts
[S17]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/.github/workflows/ssh-windows-hosts.yml
[S18]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/cli/handlers/serve-service.ts
[S19]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/docs/site/content/docs/remote-servers.mdx
[S20]: https://github.com/stablyai/orca/blob/11baf7a82e6a5a636dd7216342653b4e6c6639e4/src/main/orcad/orcad-local-serve-selection.ts
