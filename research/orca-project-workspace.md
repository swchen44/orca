# Orca 的 Project、Workspace 與 Folder Workspace

查核日期：2026-11-01。本文的 Orca 指 [stablyai/orca](https://github.com/stablyai/orca) 的 AI 開發工具；同名的 orca-desktop.com 是另一個產品，其 workspace 文件不適用於此。

## 概念

| 名稱 | 用途與範圍 |
| --- | --- |
| Project | Orca 註冊的工作來源。Git repo 可作為 project；匯入含多個 repo 的父資料夾時，也可把選定的 repo 分別匯入，或在側邊欄歸成 project group。Project group 是組織方式，底下仍是各自獨立的 repo。 |
| Workspace | 在 Orca 中開啟任務、終端機與 agent 的工作空間。一般 Git repo 的新 workspace 流程會建立真實的 Git worktree：有自己的目錄、分支與終端機，從選定的 ref 開始。 |
| Folder Workspace | Project group 的父資料夾層級工作空間，以其中一個 source project 綁定 issue 或 PR 等任務來源。它和各 repo 的 worktree 並列顯示，但本身不等於每個 repo 都有新的 Git worktree。 |

依據：[Orca Worktrees 官方文件](https://www.onorca.dev/docs/model/worktrees)、[首次使用流程](https://www.onorca.dev/docs/first-session)。Folder workspace 的命名 session 與 Git worktree 目錄也可分開理解；[維護者對 folder project 的說明](https://github.com/stablyai/orca/issues/12593)指出 folder project 的 workspace 會重用同一資料夾。

## 請假系統：單一 repo

前端、後端和資料庫 migration 放在同一個 `leave-system` repo：

```text
leave-system/                 # 一個 Git repo / Orca project
├── frontend/
├── backend/
└── migrations/
```

在這個 project 建立 `leave-approval` workspace 時，一般 Git worktree 流程會為整個 repo 建立另一份工作目錄與分支。前後端的改動因此一起出現在同一個 repo 的 diff；原本的 checkout 與新 worktree 是不同的工作目錄。[來源：Worktrees](https://www.onorca.dev/docs/model/worktrees)

### 多個任務與 agents

一個 project 可以有多個 workspace；下圖是 Orca 的概念組織，不代表磁碟上的實際資料夾層級：

```text
Project：leave-system
├── Workspace：修正請假天數     → branch：fix-leave-days     → Codex
├── Workspace：新增主管審核頁面 → branch：feature-approval  → Claude Code
└── Workspace：改善查詢速度     → branch：improve-query     → Codex
```

每項任務在各自的 worktree 中修改，完成後分別 review、commit 和合併。同一個問題也可建立 `fix-login-codex` 與 `fix-login-claude` 兩個 workspace，讓兩個 agent 分別嘗試，再比較各自的 diff。

Worktree 隔離的是工作目錄，並非作業系統的安全沙箱；agent 仍受其執行帳號的權限約束。

## 請假系統：多個 repo

前端、後端分別有自己的 Git 歷史和生命週期，父資料夾只用於集中管理：

```text
leave-system/                 # 一般資料夾；此例本身不是 Git repo
├── leave-web/                # Git repo / project
├── leave-api/                # Git repo / project
└── leave-infra/              # Git repo / project
```

將 `leave-system` 匯入並建立 project group 後，可在群組標題按 `+` 建立 Folder Workspace，例如 `leave-approval`，並選 `leave-api` 作為任務來源。這個選擇用於綁定任務來源，不代表 `leave-web`、`leave-api` 和 `leave-infra` 都建立了對應分支或 worktree。[來源：Worktrees 的 multi-repo 說明](https://www.onorca.dev/docs/model/worktrees)

**Folder Workspace 不會自動替各 repo 建立隔離 worktree。** 官方 repo 的[實際使用回報](https://github.com/stablyai/orca/issues/6357)記錄了 folder workspace 在原父資料夾執行、直接修改各 repo 原 checkout 的情況；這是個案證據，不能推論所有版本的其他細節。若跨 repo 任務需要隔離，應分別在要修改的每個 Git project 建立 worktree，並確認各自的路徑與分支。每個 repo 的 commit 與後續合併也各自處理。

## 磁碟上可能長什麼樣

以下只是示意，實際 Orca 管理目錄與名稱依設定而異：

```text
projects/
└── leave-system/             # Folder Workspace 指向的既有父資料夾
    ├── leave-web/            # 原 checkout
    ├── leave-api/            # 原 checkout
    └── leave-infra/          # 原 checkout

orca-managed-workspaces/       # 示意：各 repo 的獨立 worktree
├── leave-web/leave-approval/ # web 自己的分支與工作目錄
└── leave-api/leave-approval/ # API 自己的分支與工作目錄
```

建立 Folder Workspace 本身不會產生上圖下半部；這些獨立 worktree 必須另外建立。即使 workspace 名稱相同，它們仍是不同 repo 的不同工作目錄。建立前後可在各 repo 執行 `git worktree list` 核對實際狀態。[來源：Orca Worktrees](https://www.onorca.dev/docs/model/worktrees)、[Git worktree 官方文件](https://git-scm.com/docs/git-worktree)。

## 截圖中的 Workspace 設定

以下說明一般 Windows 本機 Git repository；WSL、SSH 與遠端主機的路徑規則可能不同。畫面文字與功能會依 Orca 版本變動。[來源：工作區設定介面](https://github.com/swchen44/orca/blob/main/src/renderer/src/components/settings/GeneralWorkspaceSettingsSection.tsx)、[路徑計算程式](https://github.com/swchen44/orca/blob/main/src/main/ipc/worktree-logic.ts)

### 工作區目錄：絕對路徑

這是**新建 Git worktree 的根目錄**，不是 Project 原始 repository 所在目錄，也不是決定 Folder Workspace 父資料夾的位置。截圖的值是：

```text
C:\Users\swche\orca\workspaces
```

假設 Project 的原始 checkout 是 `C:\company\leave-system`，新增 workspace 名為 `fix-login`，而截圖的「巢狀工作區」已開啟，結果示意如下：

```text
C:\
├── company\
│   └── leave-system\                   # Project 的原始 checkout
└── Users\swche\orca\workspaces\       # 設定的絕對路徑
    └── leave-system\                    # 巢狀工作區：repository 名稱
        └── fix-login\                   # 新 Git worktree
```

其他 Project 若沿用相同設定，也會使用這個根目錄；例如 `C:\company\payroll` 的 `fix-login` 可放在 `C:\Users\swche\orca\workspaces\payroll\fix-login`。這兩個 `fix-login` 因為分屬不同的 repository 子目錄而區分開。

### 工作區目錄：相對路徑

例如輸入 `.orca/worktrees`。相對路徑是**相對於各 Project 的 repository 路徑**，不是相對於 Orca 安裝目錄或使用者家目錄。假設巢狀工作區仍然開啟：

```text
C:\company\
├── leave-system\                             # Project A 原始 checkout
│   └── .orca\worktrees\leave-system\fix-login\  # Project A 的 worktree
└── payroll\                                  # Project B 原始 checkout
    └── .orca\worktrees\payroll\fix-login\       # Project B 的 worktree
```

若關閉巢狀工作區，以上路徑就不會有額外的 `leave-system` 或 `payroll` 子目錄，例如 `C:\company\leave-system\.orca\worktrees\fix-login`。注意此設定會把 worktree 放進原 checkout 目錄內；如不希望原 repo 的 Git 狀態列出它，應在原 repo 的 ignore 規則中處理該目錄，並依團隊需求評估是否適合。

以上是假設 Project 未設定自己的 worktree 路徑覆寫、名稱未衝突時的例子；實際名稱可能被調整。[來源：worktree 路徑與 Project 覆寫](https://github.com/swchen44/orca/blob/main/src/main/ipc/worktree-logic.ts)

### 套用於與巢狀工作區

- **套用於：用戶端預設值**：設定目前用戶端的預設路徑；有多個 host 時，可選特定 host 設定覆寫。遠端 host 的實際路徑規則可能不同。[來源：WorkspaceDirectorySetting](https://github.com/swchen44/orca/blob/main/src/renderer/src/components/settings/WorkspaceDirectorySetting.tsx)
- **巢狀工作區開啟**：根目錄下先加 repository 名稱，再加 workspace 名稱，即 `<根目錄>\<repo名稱>\<workspace名稱>`。
- **巢狀工作區關閉**：使用 `<根目錄>\<workspace名稱>`。這裡的「巢狀」是磁碟目錄配置，與 Orca 側邊欄的父子 workspace 關係不同。

這些路徑設定主要影響後續建立的 worktree；不要假設變更設定會自動搬移既有工作目錄。

### 來源與工作樹根目錄

此區決定**在 Orca 之外建立的 worktree，預設是否顯示在側邊欄**，不決定 Orca 新建 worktree 的存放位置，也不會因隱藏而刪除檔案。[來源：Orca Worktrees](https://www.onorca.dev/docs/model/worktrees)

| 畫面項目 | 用途與例子 |
| --- | --- |
| Claude Code | 控制符合 `.claude/worktrees/*` 來源的外部 worktree 顯示；例如 Claude Code 建立的工作樹。 |
| GSD | 控制符合 `.gsd-workspaces/*` 來源的外部 worktree 顯示。 |
| 其他位置 | 控制未歸入其他來源的外部 worktree。 |
| 工作樹根目錄 | 新增自訂**絕對路徑**，例如 `D:\team-worktrees`，讓 Orca 將該處已辨識的外部 worktree 分類為此來源。新加入的自訂來源預設隱藏，可再切換顯示。 |

例如，某 repository 已透過 Git 建立外部 worktree `D:\team-worktrees\leave-fix`：把 `D:\team-worktrees` 加入自訂來源並選「顯示」，可讓符合條件的工作樹依此來源顯示；這個操作不會建立新的 Git worktree。單一 Project 的 Non-Orca worktrees 對話框也能覆寫來源顯示設定，或逐一顯示隱藏的工作樹。

## Project 有哪些設定？

有。**Settings → Repository** 提供以 repository 為範圍的設定，例如 base ref、建立工作樹時的 hooks／命令、Worktree Shared Paths、圖示，以及 commit／PR 等 source-control AI 設定；實際欄位依版本而異。[來源：Settings Reference](https://www.onorca.dev/docs/settings)

程式也支援 repository 專屬的 `worktreeBasePath`：設定後會優先於一般 workspace directory。此覆寫用於該 repository 的新 worktree，不會把 Project 原始 checkout 移走。[來源：路徑程式](https://github.com/swchen44/orca/blob/main/src/main/ipc/worktree-logic.ts)

例如 `leave-system` 的 base ref 可設為 `origin/main`，建立 worktree 後執行團隊核准的 setup 命令；而 `payroll` 可有自己的設定。Project 已加入哪個資料夾，和 workspace 新 worktree 的存放位置是兩個不同概念。

## Folder Workspace 有哪些設定？

有可設定的**建立選項與工作區資料**，但不要將上方 Git worktree 的「工作區目錄」視為 Folder Workspace 的父資料夾設定：

1. 匯入包含多個 repo 的父資料夾並建立 Project Group。
2. 在群組標題選 `+`，建立 Folder Workspace，填入名稱、選擇 source project，並可選擇關聯 issue 或 PR。
3. Folder Workspace 以群組的既有父資料夾為工作範圍；選擇 source project 是決定任務來源，不會自動替各 repo 建立 branch 或 worktree。

例如：Project Group 指向 `C:\company\leave-system`，底下有 `leave-web` 和 `leave-api`；建立 `主管審核` Folder Workspace 並選 `leave-api` 為 source project，agent 可以從父資料夾處理跨 repo 任務，但在各 repo 的原 checkout 寫入時會影響那些原目錄。若需要隔離，需分別建立 repo worktree，並確認 agent 實際工作路徑。[來源：Orca Multi-repo project groups & folder workspaces](https://www.onorca.dev/docs/model/worktrees)

除了名稱、任務連結等 workspace 資料，Orca 也有適用於一般 workspace 的介面及 agent 設定；目前未查到一個與截圖相對應、可單獨指定所有 Folder Workspace 新建磁碟根目錄的設定頁。

## 實際例子：這台電腦的 `C:\Users\swche\orca`

以下是 2026-11-01 的本機檢查結果，目錄和分支之後可能變動。這是一個實際的 Git worktree 例子，**不是** Folder Workspace 的例子：

```text
C:\Users\swche\orca\
├── projects\
│   ├── codex-chatgpt-web-study\   # 另一個 Git repository
│   └── orca_study\                # 原始 checkout，目前 branch：master
│       └── .git\                  # Git 共用資料與 worktree 登記
└── workspaces\
    ├── .orca-preparing\
    └── orca_study\                # 依 repository 名稱分類的資料夾
        └── 2orca\                 # orca_study 的 linked worktree
            └── .git               # 指向 Git 管理資料的文字檔
```

`git worktree list` 在 `orca_study` 查到兩筆：

| 工作目錄 | 角色 | 檢查時的 branch |
| --- | --- | --- |
| `C:\Users\swche\orca\projects\orca_study` | 主 checkout | `master` |
| `C:\Users\swche\orca\workspaces\orca_study\2orca` | linked worktree | `sw/research-orca-network-bridge` |

兩者檢查時都指向同一個 commit `13bf0be`，但 branch 不同，之後可以各自前進。`projects\orca_study` 是本機 repository，與本文件所在的 GitHub `swchen44/orca` repository 不應當成同一個 repository。

### 它們用什麼 link 連在一起？

這個例子中，`2orca` 與其父資料夾經檢查是一般目錄，沒有顯示為 Windows symlink 或 junction。Git 的連結是透過**普通文字檔中的路徑，以及主 repository 的管理資料**實現，不是把整個 `2orca` 目錄做成檔案系統捷徑：

```text
workspaces\orca_study\2orca\.git          # 文字檔
    │
    └─ gitdir: C:/Users/swche/orca/projects/orca_study/.git/worktrees/
               12260-d3149bc4-0bfe-4360-950a-1aa37e94db77
                                      │
                                      ├─ gitdir → 2orca/.git
                                      ├─ commondir → ../..  # 主 checkout 的 .git
                                      ├─ HEAD → 該 worktree 目前的 branch
                                      └─ index → 該 worktree 的暫存狀態
```

上圖為了易讀將第一個路徑換行；實際 `.git` 文字檔的 `gitdir:` 指標是一行。管理目錄名稱由 Git 產生，不應假設其他電腦或重新建立後會相同。兩個 worktree 的 Git objects 與一般 branch refs 由同一 repository 共用，但各自有工作目錄、`HEAD` 與 index；修改一邊的檔案，不會自動修改另一邊的工作目錄。[來源：Git worktree 文件](https://git-scm.com/docs/git-worktree)

可以用唯讀指令確認：

```powershell
git -C C:\Users\swche\orca\projects\orca_study worktree list
Get-Content C:\Users\swche\orca\workspaces\orca_study\2orca\.git
git -C C:\Users\swche\orca\workspaces\orca_study\2orca rev-parse --absolute-git-dir
git -C C:\Users\swche\orca\workspaces\orca_study\2orca rev-parse --git-common-dir
```

避免手動移動或刪除這些 `.git` 管理檔案；若要移動或移除 worktree，使用 Orca 或 Git 的 worktree 命令，以維持登記關係。

