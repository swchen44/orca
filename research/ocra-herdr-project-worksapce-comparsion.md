# Orca 與 Herdr：Project、Workspace、Space 及 Android 案例比較

整理日期：2026-11-03。依需求保留檔名中的 `ocra`、`worksapce`、`comparsion` 拼法，內容產品名稱使用 Orca／Herdr。

先讀：[Orca 案例](orca-project-workspace.md) · [Herdr 由淺入深案例](herdr-project-workspace.md)。本文件是 source review，不是效能測試或已在公司環境驗證的相容性保證。

## 版本與證據範圍

| 對象 | 本文核對版本 | 說明 |
| --- | --- | --- |
| Orca | 使用者 fork `swchen44/orca`，`f16217b827f3594ebd279b837c3cfd7cf66f5c36` 的相關原碼 | 延續既有 Orca 文件與 session 的版本。 |
| Herdr 1 | `herdrdev/herdr`，`ee5bfb5041bb3e4a49d591c72308aae3c81ecdde` | 已下載的第一代 TUI/server。 |
| Herdr 2 app | `herdrdev/herdr-app`，`1581a587919dddd6f1efd5f78eb542c4b2b02cb5` | 已下載的 GPUI 桌面 app，主要比較對象。 |
| Herdr 2 core | `herdrdev/herdr-core`，`27fea26efe498dce7e1555948fa75c3994fb8a9c` | app 使用的 terminal runtime，並非另一套 Project 管理器。 |

Herdr app/core 遠端已比本機 snapshot 前進；本文不將網站最新版能力直接套入這些 commits。表格中的「未實作／未查到」限於列出的原始碼與所研究路徑，不代表將來版本不會提供。

## 概念與操作比較表

| 比較項目 | Orca | Herdr 2 app + core | 事實依據 |
| --- | --- | --- | --- |
| 程式架構 | Electron app，啟動／管理 coding agents | Rust GPUI app 顯示畫面，core 管理 PTY 與程序 | [O4]、[H1] |
| Project 的意義 | repository／資料夾註冊與相關設定；多 repo 可歸 Project Group | 目前 UI 主要是 Space；不能假設有完全相同的 Orca Project 設定層 | [O1]、[H2] |
| 工作容器 | Git worktree Workspace，或資料夾形式的 workspace | Space → Tabs → Panes；Space 可以指向任意既有 folder | [O2]、[H2] |
| 普通資料夾 | Folder Workspace／folder project 流程，可提供不綁單一 Git repo 的工作範圍 | `space.new --folder <path>` 建立終端機和 Space | [O2]、[H2] |
| 開工作容器會自動隔離程式碼？ | 要看是 Git worktree 還是 Folder Workspace | 普通 Space 不隔離；New worktree 才呼叫 Git 建 checkout | [O2]、[H3] |
| 多 repo 組織 | Project Group 與 group Folder Workspace 流程 | 預設 spaces mod 的 nesting 是同一 repo 的 Git worktree 分組；未在該 mod 找到 Orca 式父資料夾批次匯入流程 | [O1]、[H4] |
| New worktree 的範圍 | 一個 Git repo | 一個 Git repo | [O1]、[H3] |
| 預設 worktree 位置 | client／host path，加 repo override，配合 nestWorkspaces | shipped mod 固定 `~/.herdr/worktrees/<repo>/<branch-slug>`，home 屬 Space 所在機器 | [O1]、[O3]、[H3] |
| 絕對／相對路徑 | 一般本機相對 root 以 repo path 解析；絕對 root 直接使用。WSL／SSH 另有規則 | shipped mod 無 root 設定。可手動 `git worktree add` 指定路徑，再 `space.new` 開啟 | [O1]、[H3] |
| 巢狀 worktree 目錄 | 可開關 repo 名稱子目錄 | shipped mod 固定加 repo 名稱 | [O1]、[H3] |
| 選擇起始版本 | 建立流程可選 branch／commit；確切選項依介面版本 | mod 新 branch 固定由來源 HEAD 建立，既有 branch 則 checkout；自訂 base 可用 Git | [O1]、[H3] |
| 開已存在的 worktree | 可辨識，另有 external worktree 來源顯示設定 | Open worktree 讀 `git worktree list --porcelain`，開 Space 或跳至已開 Space | [O1]、[H3] |
| 命名與自動分組 | workspace 名稱、Git branch 與側邊欄組織是不同狀態 | 明示 name 影響名稱；spaces mod 分組依 common-dir、linked 與 main Space 存在，不以 name 作 gate | [O1]、[H4] |
| 刪除 worktree | 官方文件說明可能連 branch 一起刪除，也有保留分支處理，操作前讀當版確認內容 | mod 執行 `git worktree remove`，這個路徑沒有刪 branch；含 dirty/submodule 檢查與 force 流程 | [O5]、[H3] |
| 企業核准 Electron | 桌面模式需要相容的 Electron runtime | 需核准 Herdr app/core 的原生執行檔；Electron 不提供這些程式 | [O4]、[H1] |
| Agent 的 API token | 由 agent 的憑證、endpoint、環境與政策決定 | 同樣由 agent 決定；Space、core 不提供雲端模型 | 兩者都啟動外部 agent；公司 gateway 尚未實測 |

## 同一批資料夾，操作怎麼對應？

| 案例 | Orca 的用法 | Herdr 2 的用法 |
| --- | --- | --- |
| `D:\git\clinic_bookmarklet` 是 Git repo | Add Repo 加入；選原 checkout 或在 Project 下新增 Git Workspace | `herdr-app do space.new --name clinic-study --folder 'D:\git\clinic_bookmarklet'`；需要隔離時再 New worktree |
| `D:\git\yazi_work` 普通父資料夾，底下多 repo | 直接加入子 repo；需要時匯入 Project Group，再建 group Folder Workspace | 父資料夾開研究 Space；各子 repo 分別開 Space 及 worktree；普通 parent Space 不會自動註冊全部子 repo |
| 同一 repo 讓 Codex／Claude 各試一種方案 | 建兩個 Git Workspace | 建兩個 worktree Space |
| 前端和後端分開的請假系統 | group Folder Workspace 做整體研究，各 Project worktree 分工 | parent Space 做整體研究，各 Git repo 的 worktree Space 分工 |
| 想沿用 `C:\Users\swche\orca\workspaces` | 依既有 Workspace Directory 設定 | Herdr 的 root 獨立；若要自訂目錄，用 Git 建 checkout 後再開 Space，勿假設自動讀 Orca 設定 |

具體命令、絕對／相對路徑 tree 及建立行為，見 [Herdr 案例第 3～7 節](herdr-project-workspace.md)。所有實體範例目錄仍需使用者自行選定；本研究沒有操作任何既有工作環境。

## Android：最容易混淆的地方

兩者都可以在完整 Android source root 執行 agent 和公司 build command；兩者的一般 Git worktree 都只處理單一 Git repo。**在另一個目錄開普通工作容器，不會讓 Android manifest 的全部 projects 同時產生隔離 checkout。**

| Android 情境 | Orca | Herdr 2 | 實際需另行負責的部分 |
| --- | --- | --- | --- |
| 一套 source tree 研究並 build | Folder Workspace 位於 `/work/android-main` | Space 的 folder 設 `/work/android-main` | `repo init/sync`、Linux build 環境、target、公司 build script |
| 對 frameworks/base 隔離修改 | 該 Project 建 worktree | 該 repo New worktree 或 Git 命令建立再開 Space | 選對 baseline、review、commit |
| Settings、framework、device 分工 | 三個 Git worktrees，加整合 Folder Workspace | 三個 worktree Spaces，加整合 Space | 介面協調、各 repo 的 commit 依賴與整合 |
| 把修改帶進 image | 整合到實際 build tree 再 build | 同樣先整合到實際 build tree | build 不會自動採用外部 worktree 的檔案 |
| 兩組功能平行產生 image | 兩套 Repo client／source tree + 個別 Folder Workspace | 兩套 Repo client／source tree + 個別 Space | source、OUT_DIR、其他產物與資源隔離 |
| 在 `.repo` root 選 New worktree | 必須選實際 Git 子 project；資料夾操作不等於 Git worktree | mod 的 Git 檢查會因 root 不是 Git repo 而無法建立 | Android 的 manifest 並非 Git super-repo 的自動隔離機制 |

以上 Android 使用方式是依程式能力和 Git／Repo 機制推導的案例，不是已驗證的公司環境操作結果。[H3][O2][A1][G1]

特別是 Repo 的 common-dir 可能位於 `.repo/projects/...git`；Herdr mod 由 common-dir 推導 repo 名稱及 main 路徑，實際目錄名稱／分組未必與普通 `.git` checkout 一致。因此應先對單一 Android project 驗證，不能宣稱可直接批次建立完整可 build tree。[H3][H4]

## Herdr 1 的差異不能省略

第一代 `herdr` 可使用 `herdr workspace create --cwd ... --label ... --focus`；worktree CLI 支援 `--base` 和 `--path`，config 也有 `[worktrees] directory`。第二代 shipped JS mod 的固定路徑限制不能反過來套用到第一代。第一代 Git discovery 只查 cwd 與父目錄，也不會把 Android 子 repos 全部當作一個 repo。[H5]

重新從別的資料夾執行第一代 `herdr`，可能只是 attach 既有 default session；要新增特定目錄 workspace 應使用明確命令。第二代的 app `space.new`、core `HC_SESSION` 和第一代 session 也不是可互換的名詞。[H5][H6]

## 使用者討論與 source 對齊

| 討論線索 | 可以學到什麼 | 本文採用的事實 |
| --- | --- | --- |
| [Herdr #3310：相對 worktree 路徑](https://github.com/herdrdev/herdr/discussions/3310) | 使用者希望路徑跟隨 repo | 功能請求不能證明 app snapshot 已實作；目前 app root 常數見 [H3] |
| [Herdr #553：bare repo 與 sibling worktree 分組](https://github.com/herdrdev/herdr/discussions/553) | 目錄配置與 UI grouping 可能不同 | app grouping 使用 common-dir／linked 判斷，見 [H4]；不能把貼文期望當作已實作 |

本機 source snapshot 與已發布版本可能不同；文件遇到差異時，先確認實際執行檔屬於哪一代、哪個 commit 或 release。

## 選擇方式

若同仁主要需要 Project／多 repo 群組、工作樹路徑設定，以及 Git 工作區流程，先閱讀 Orca 範例。若主要需要維持終端機程序、Space／Tab／Pane、遠端機器及可修改的 mods，先閱讀 Herdr 第二代範例。這是根據本次功能範圍的使用建議，不是效能或穩定性排名。

## 固定版本來源

- [O1] [Orca worktree 路徑計算](https://github.com/swchen44/orca/blob/f16217b827f3594ebd279b837c3cfd7cf66f5c36/src/main/ipc/worktree-logic.ts)，[group/worktrees 文件](https://github.com/swchen44/orca/blob/f16217b827f3594ebd279b837c3cfd7cf66f5c36/docs/site/content/docs/model/worktrees.mdx)。
- [O2] [Orca folder workspace model](https://github.com/swchen44/orca/blob/f16217b827f3594ebd279b837c3cfd7cf66f5c36/src/main/ipc/worktrees/folder-workspace-model.ts)，`mergeFolderWorkspace` 使用 repo.path、空 branch/head。
- [O3] [Orca WorkspaceDirectorySetting](https://github.com/swchen44/orca/blob/f16217b827f3594ebd279b837c3cfd7cf66f5c36/src/renderer/src/components/settings/WorkspaceDirectorySetting.tsx)。
- [O4] [Orca package.json](https://github.com/swchen44/orca/blob/f16217b827f3594ebd279b837c3cfd7cf66f5c36/package.json)。
- [O5] [Orca Worktrees 官方文件](https://www.onorca.dev/docs/model/worktrees)；此連結會隨官方更新，刪除行為以實際版本為準。
- [H1] [Herdr app AGENTS](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/AGENTS.md)，[core AGENTS](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/AGENTS.md)。
- [H2] [app commands](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/commands.rs)，[new_space](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2309)。
- [H3] [app worktree mod](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/worktree/main.js)。
- [H4] [app spaces mod](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/spaces/main.js#L204)。
- [H5] [Herdr 1 worktree command builder](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/worktree.rs)，[workspace 建立](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/app/api/workspaces.rs)，[startup](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/server/headless/bootstrap.rs)。
- [H6] [core paths／session](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/paths.rs)。
- [A1] [Android Repo 官方文件](https://source.android.com/docs/setup/reference/repo)。
- [G1] [Git worktree 官方文件](https://git-scm.com/docs/git-worktree)。
