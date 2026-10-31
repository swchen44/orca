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

