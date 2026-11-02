# Herdr 的 Project、Workspace、Space 與 Git worktree：由淺入深案例

整理日期：2026-11-03。對照同目錄的 [Orca 案例](orca-project-workspace.md)。本文依已下載原始碼分析，未啟動、安裝或變更使用者的 Herdr，也未在 Android build host 實測。所有新增目錄、branch 與 UI 畫面樹均為教學示意。

## 1. 先分清楚三個 repository

| 本機目錄 | 研究版本 | 角色 |
| --- | --- | --- |
| `herdr/` | `ee5bfb5041bb3e4a49d591c72308aae3c81ecdde` | 第一代 Herdr：Rust 的 terminal TUI／server，使用 workspace 等概念。 |
| `herdr-core/` | `27fea26efe498dce7e1555948fa75c3994fb8a9c` | 第二代的 terminal runtime；`hc` 管理程序、PTY、訊息與遠端機器。 |
| `herdr-app/` | `1581a587919dddd6f1efd5f78eb542c4b2b02cb5` | 第二代 GPUI 桌面 app；用 Space、Tab、Pane 安排 core 中的終端機，worktree 由 shipped mod 提供。 |

這三個目錄不是同一個版本的三個隨意拆分模組。不要把第一代 `herdr workspace ...` 命令、第二代 `herdr-app do ...` 命令及 `hc` 混用。以下操作案例主要使用 **第二代 app + core**；第一代差異見後文。研究版本是本機 snapshot，並非宣稱最新遠端功能。[H1][H2][H3]

### 閱讀前先選擇使用的代別

原始碼 `herdr-app/AGENTS.md` 明確使用「Herdr 2 desktop app」；本文的第一代／第二代指這兩套產品架構，不等同於 release 的 SemVer 必然是 `1.x`／`2.x`。僅憑下載版本號或桌面顯示的 Herdr 名稱，不能確定正在使用哪套。[H3]

| 你使用的執行指令 | 對應架構 | 本文案例位置 |
| --- | --- | --- |
| `herdr workspace ...`、`herdr worktree ...` | 第一代 `herdr` | 第 10 節：第一代對應案例與限制 |
| `herdr-app do space.new ...` | 第二代桌面 `herdr-app` | **第 3～9 節全部是第二代案例** |
| `hc ...`／`herdr-core ...` | 第二代的 terminal runtime | 與 app 配合；core 本身不提供 app 的 Space UI／worktree mod |

第二代案例由第 3 節直接開 repo，一路到第 9 節 Android 多 agent 整合 build。第一代指令另列第 10 節，不應拿來當成第二代 `herdr-app` 的指令。

## 2. 概念與對照

| 概念 | 第二代 Herdr 的意思 | 是否自動建立 Git 分支或隔離目錄？ |
| --- | --- | --- |
| Project | 日常可以指一個程式碼專案；在目前 app 不應假設它等同 Orca 的獨立 Project 註冊／設定單位。 | 不會因為名稱叫 project 就隔離。 |
| Space | 一台機器上的工作容器，含 tabs 和 panes；可以指向 Git repo，也可以是普通資料夾。 | `space.new` 啟動終端機並記錄畫面狀態，本身不執行 `git worktree add`。 |
| Tab／Pane | Space 中的分頁／分割畫面，可顯示終端機或 mod。 | 多開 pane 不會複製程式碼。 |
| Git worktree Space | worktree mod 執行 Git 建立 checkout，再對該目錄 `space.new`。 | 這時才有該 repo 的獨立工作目錄。 |
| core terminal | `hc` 管理的程序及 PTY；app 是它的 viewer。 | `hc run --cwd ...` 只指定程序的起始目錄。 |

原始碼依據：`commands.rs` 的命令參數、`window.rs::new_space`、worktree mod 的 `create`；core 的職責見其 AGENTS 與 API。[H2][H4][H5][H6]

**名稱相近不代表隔離方式相同。** 對同一資料夾開兩個 Space，兩個 agent 修改的是同一份檔案；對同一 repo 建立兩個 Git worktree，才會有兩份工作目錄。Git worktree 仍不是安全沙箱。


### 2.1 都在本機 Linux：Workspace 可以對應 Space 嗎？

**若指「整理一個資料夾的終端機和 agents」，第一代 Workspace 可以對應第二代 Space。** 這是工作用途的對應，不是設定檔、儲存資料或命令的直接相容關係。

```text
第一代 herdr                         第二代 herdr-app
Workspace：android-study            Space：android-study
├── Claude 終端機                     ├── Claude 終端機
├── Codex 終端機                      ├── Codex 終端機
└── build 終端機                      └── build 終端機
    cwd：/work/android-main               cwd：/work/android-main
```

兩者都能執行相同的公司 CLI 和 build command；普通 Workspace／Space 都不會複製 Android tree。若兩個 agents 指向同一個 source tree，它們會修改相同檔案。這項限制不因使用 Linux 或第二代而改變。[H5][H9][G1]

| 本機 Linux 使用者會看到的差異 | 第一代 | 第二代 |
| --- | --- | --- |
| 畫面所在位置 | 既有終端機裡的 TUI | GPUI 桌面視窗；core 可單獨無桌面使用 |
| 程序的持有者 | Herdr session server | 獨立的 herdr-core；app 是 viewer |
| 開啟研究目錄 | `herdr workspace create --cwd /work/android-main --label android-study --focus` | `herdr-app do space.new --name android-study --folder /work/android-main` |
| worktree 自訂 | CLI 有 path、base 和 worktree directory 設定 | 研究版本 shipped mod 固定 root，新 branch 從來源 HEAD 建立；自訂可先用 Git 建立 |
| 介面擴充 | 第一代自己的設定與 plugin／API 流程 | layout 和 JavaScript mods；不是沿用第一代 plugin 套件的保證 |
| 關閉畫面後程序繼續 | 第一代本來就有背景 server | app 視窗關閉後由 core 維持；不是第二代才新增的概念 |
| 重開機後 agent 對話 | 第一代有符合條件的 integration native session resume；不等於原程序存活 | 研究版本 kept terminal 回到原目錄的新 shell，不能套用第一代的 agent resume 保證 |
| 無桌面 Linux host | TUI 可在終端機使用 | app 需要圖形桌面與相容 Vulkan；只有 core 可無桌面執行 |

原碼與隨附文件依據：[H1][H2][H3][H8][H9][H11][H12]。關閉畫面、關閉 pane、停止 server/core 和重開機是不同動作；不能把「detach 後程序還活著」理解成重開機仍保有同一個程序。第二代 README 明載關閉 pane/tab 會結束其中終端機；core crash 或 reboot 後可恢復的 panes 是新 shell，不是原程序。[H11]

另外，第二代 core 依程序回報的 OSC 7501 狀態運作，不保證任意 CLI 都自動被辨識為 working／blocked；app 的 sidebar 顯示能力要配合 agent 的狀態回報。[H2][H11]

因此，Android 本機案例的工作安排可以相同：一個 root 工作容器、數個 agent 和一個 build terminal。選用哪代仍需確認你的 worktree、terminal 操作、擴充套件及復原需求，不應將第二代視為第一代所有功能的完全替代。本文沒有實測兩代效能或穩定性。

## 3. 第二代案例一：直接開既有 Git repo

需求：`D:\git\clinic_bookmarklet` 已是 Git repo，想讀程式或讓 agent 修改。

1. 開啟 Herdr app。預設 New space 直接送出 `space.new`，未指定 folder 時會繼承同機器焦點終端機的 cwd；不要假設按鈕會提供資料夾選擇器。
2. 要精準開啟指定資料夾，在已安裝的第二代 app 使用下列命令。
3. 在開啟的終端機確認工作目錄，再啟動公司已能使用的 `codex` 或 `claude`。

```powershell
herdr-app do space.new --name clinic-study --folder 'D:\git\clinic_bookmarklet'
herdr-app ls
```

`space.new`、`--name`、`--folder` 的形狀由程式確認；`ls` 用來核對已建立的 Space。上述不是第一代 Herdr 命令。[H3][H4][H5]

```text
D:\git\clinic_bookmarklet\           # 原本的 Git checkout

Herdr app
└── Space：clinic-study
    └── Tab → 終端機 cwd 指向上面的資料夾
```

只開 Space 不會搬移 repo、不會 clone，也不會自動新增 branch。直接修改會改到原 checkout。給 Space 固定名稱有利於辨識；未命名時則依當前 folder／Git 資訊產生名稱。側邊欄的 worktree 分組依 Git common-dir 與是否存在 main checkout Space 判斷；目前實作沒有以「是否命名」作為分組條件。[H5][H7]

## 4. 第二代案例二：同一 repo 的兩個獨立任務

需求：Codex 修正書籤，Claude 試另一種寫法，互相比較。

1. 確認選單使用的來源 checkout 與 HEAD：Space 選單以該 Space 第一個終端機的 live cwd 為主；`+` 選單另傳入焦點 pane 的 cwd，若不同 panes 在不同目錄，兩者可能不同。
2. 在 Space 選單或 `+` 選單使用 **New worktree**，輸入 branch，例如 `fix/bookmarklet-a`。
3. 再建立 `fix/bookmarklet-b`，分別啟動 agent。
4. 完成後分別 review、commit，再依團隊流程選擇或合併修改。

目前 shipped worktree mod 的規則是：

- 固定 root 為該 Space 所在機器的 `~/.herdr/worktrees`。
- 根據 repo 名稱建立子目錄，branch 中的 `/` 等字元轉為 `-`。
- 新 branch 從「來源 checkout 的 HEAD」建立；同名 branch 已存在時使用既有 branch，Git 本身可能因 branch 已被其他 worktree 使用而拒絕。
- 建立成功後對 checkout 執行 `space.new`，預設保持未命名，名稱可跟隨 folder；是否分組則由 spaces mod 的 Git 判斷決定。[H6][H7]

```text
D:\git\clinic_bookmarklet\                       # 原始 checkout

C:\Users\swche\.herdr\worktrees\                # 假設 app 的 home 為此使用者
└── clinic_bookmarklet\
    ├── fix-bookmarklet-a\                       # branch：fix/bookmarklet-a
    └── fix-bookmarklet-b\                       # branch：fix/bookmarklet-b
```

UI Space 分組示意：

```text
clinic_bookmarklet
├── fix-bookmarklet-a → Codex  # branch：fix/bookmarklet-a
└── fix-bookmarklet-b → Claude # branch：fix/bookmarklet-b
```

原碼的 root 是常數，不應照抄第一代的 `[worktrees] directory` 或 Orca 的 Workspace Directory 設定，宣稱可以改變第二代 shipped mod 的路徑。此版本的 New worktree 也沒有獨立的 base ref 欄位。[H6]

## 5. 第二代案例三：使用絕對或相對路徑

若要自行指定位置與起點，可以使用一般 Git 建立 worktree，再讓 Herdr 開該目錄。以下命令有建立 branch 和資料夾的副作用，請選擇新名稱並確認起點；本文未執行：

```powershell
# 絕對路徑：以本機 master 為範例，實際依該 repo 的 branch
git -C 'D:\git\clinic_bookmarklet' worktree add -b example-a 'D:\worktrees\clinic-a' master
herdr-app do space.new --folder 'D:\worktrees\clinic-a'

# 相對路徑：git -C 先切到 repo，../clinic-b 解析成 D:\git\clinic-b
git -C 'D:\git\clinic_bookmarklet' worktree add -b example-b '../clinic-b' master
herdr-app do space.new --folder 'D:\git\clinic-b'
```

這裡相對路徑的解析由 **Git 命令的工作目錄** 決定，不是第二代 app 的「repo 相對 root 設定」。為了讓操作容易重現，`space.new --folder` 範例都使用絕對路徑。也不要把 terminal 的相對 `cwd` 規則與 worktree root 的規則混為一談。[H4][H6][G1]

Git worktree 透過 checkout 中的 `.git` 指標、common Git directory 和管理資料連結；整個資料夾不需要變成 Windows symlink／junction。objects 和一般 refs 共用，工作目錄、HEAD、index 分開。可執行 `git worktree list` 及 `git rev-parse --git-common-dir` 核對。[G1]

## 6. 第二代案例四：研究父資料夾 `D:\git\yazi_work`

假設目前是普通父資料夾，底下含 `yazi_intranet`，以後可能再放其他 Git repo：

```text
D:\git\yazi_work\                   # 普通資料夾
├── yazi_intranet\                  # Git repo
└── other-repo\                     # 未來範例
```

整體研究可以直接建立父資料夾的 Space：

```powershell
herdr-app do space.new --name yazi-study --folder 'D:\git\yazi_work'
```

在此終端機啟動 agent，可要求它閱讀兩個子 repo，但這個 Space 不會自動形成 Orca 那種匯入多 repo 的 Project Group。預設 spaces mod 依 Space 的 folder／第一個終端機的 live cwd 查詢 Git 資訊；不要把「同一 repo 的 worktree 分組」誤認成「任意父資料夾下所有 repo 分組」。[H5][H7]

如果要對 `yazi_intranet` 建 worktree，另外建立該 repo 的 Space，再使用 New worktree；從非 Git 的父目錄執行 worktree mod，不能把所有子 repo 當成一個 Git repo。

```powershell
herdr-app do space.new --folder 'D:\git\yazi_work\yazi_intranet'
```

兩個普通 Space 即使都叫不同的研究主題，只要指向同一個資料夾，仍會修改同一份檔案。

## 7. 第二代案例五：多 repo 請假系統

```text
D:\company\leave-system\
├── leave-web\                # Git repo A
├── leave-api\                # Git repo B
└── notes\                    # 普通研究筆記
```

1. 建立 `leave-study` Space，folder 指向父資料夾，用於跨 repo 閱讀及筆記。
2. 分別為 web、API 建立以 repo 根目錄為 folder 的 Space。
3. 要隔離修改時，分別建立 `feature/approval-web`、`feature/approval-api` worktree。
4. 協調 API 介面；每個 repo 分別 review、commit 與整合。
5. 若整合測試只讀原父資料夾中的 checkout，先將已 review 的 commit 整合到該 checkout。外部 worktree 的變更不會自動出現在原目錄。

這是依 Space 和 Git worktree 實作推導的使用方式；並非原碼中專用的「跨 repo feature」功能。[H5][H6][G1]

## 8. 第二代案例六：Android 單一 source tree 研究和 build

Android Repo 的 manifest XML 配合 `repo init`、`repo sync` 建立完整 source tree，source root 通常不是單一 Git repo。這裡是 Repo 的 manifest，不是 Android app 的 `AndroidManifest.xml`。[A1]

```text
/work/android-main/
├── .repo/
├── frameworks/base/                   # Git project
├── packages/apps/Settings/            # Git project
├── device/company/product/            # 示意 Git project
└── out/                               # 實際依 build 設定
```

以下使用公司 Linux build host；source tree 已由公司流程準備好。若從 Windows 控制，先在 Herdr 設定 SSH machine，再核對名稱與 folder，不能把 Windows 的 D: 路徑交給 Linux host。

```sh
hc machine ls
# android-build 是例子，使用上一步實際存在的 machine 名稱
herdr-app do space.new --name android-integration --machine android-build --folder /work/android-main
```

在這個 Space 的終端機確認 `pwd` 與 `repo status`，啟動 agent 跨 repo 研究、修改，接著在同一 source root 執行公司 build command。標準 AOSP 流程範例為 `source build/envsetup.sh`、`lunch <公司target>`、`m`，vendor 流程可能不同。[H3][A1][A2]

此 Space 的角色接近 Orca 的 Folder Workspace：都可將終端機放在完整 source root，直接修改這棵 tree。建立第二個 Space 指向同一路徑不會隔離 Android source 或 build output。

## 9. 第二代案例七：Android 多 agent、單 repo worktree、整合 image

需求：新增公司裝置模式，三個 agent 分別改系統 API、Settings 和產品預設值。

```text
Herdr app（示意）
├── Space：android-integration → /work/android-main
├── base 的 worktree Space → 該 repo 的隔離 checkout
├── Settings 的 worktree Space → 該 repo 的隔離 checkout
└── product 的 worktree Space → 該 repo 的隔離 checkout
```

1. 先確認每個 source checkout 的 commit、工作目錄狀態與 Repo 管理流程；先選一個 project 驗證 worktree 相容性。Repo 的 Git common-dir 可能在 `.repo/projects/...git`；目前 mod 從 common-dir 推導 main/name，可能得到 `base.git` 等名稱，而不是 source folder 的 `base`。因此不能承諾自動目錄名稱或 grouping 和普通 `.git` checkout 相同；必要時手動 Git 建 worktree，再以明確路徑開 Space。
2. 為三個 Git project 分別開 Space。原碼的 New worktree 新 branch 從來源 HEAD 建立；要從指定 commit 開始時，使用上文一般 Git 命令，不要自行假設 mod 有選擇 base ref 的 UI。
3. 分別建立 worktree、啟動 agents，先協調跨 repo 介面，再各自 review 和 commit。
4. 回到 `android-integration`，依公司 Git／Gerrit 流程，將三個 repo 的 commit 帶入 `/work/android-main` 對應的 checkout。
5. 確認修改和 branch 後，執行公司 build command，產生 image 並測試。
6. 記錄 manifest revisions、各 repo commit、target、命令與結果；`repo manifest -r` 不包含尚未提交的檔案或所有外部 build 輸入。[A1]

單個 repo worktree 沒有完整 build tree。外部 worktree 的修改，完整 build 不會自動採用；除非公司自行實作並驗證其他 source mapping／build 機制。若要兩組 agents 同時產生兩套 image，使用兩套完整 Repo client 和各自的輸出目錄，分別開 Space。這是兩套完整 tree，並非一個涵蓋全部 projects 的 Git worktree。[G1][A1]

## 10. 第一代對應案例，以及使用者討論的查證

第一代使用 workspace／tab／pane 和 `herdr worktree ...`；原碼中有 `[worktrees] directory` 設定及 worktree 建立／開啟／移除流程。不要把它的設定直接套用到第二代。第一代也不是「建立 workspace 就自動 clone repo」；建立工作容器與建立 Git checkout 是不同操作。[H1][H8]

若你實際執行的是第一代 `herdr`，可將同一組案例改為：

```powershell
herdr workspace create --cwd 'D:\git\clinic_bookmarklet' --label clinic-study --focus
herdr workspace create --cwd 'D:\git\yazi_work' --label yazi-study --focus

# 對單一 Git repo，在指定絕對路徑及 base 建立 worktree
herdr worktree create --cwd 'D:\git\clinic_bookmarklet' --branch example-a --base master --path 'D:\worktrees\clinic-a'
```

第一代 UI 的 New workspace 只詢問名稱；cwd 依 `new_cwd` 與來源 workspace 繼承。從另一個目錄再次執行 `herdr` 會 attach 既有 session，只有空 session 才用 startup cwd 建立第一個 workspace，因此不要把重新執行 `herdr` 當成新增指定資料夾的方法。[H9]

Android 第一代範例是在 Linux build host 執行 `herdr workspace create --cwd /work/android-main --label android-integration --focus`；root workspace 可執行 agent 與完整 build，但 Git discovery 從 cwd 向父目錄尋找 Git repo，不會自動掃描所有 Android 子 projects。單一 Git 子 repo 的 worktree 仍需分別建立，整合方式同前節。[H10]

兩個討論可作為查證起點：

- [#3310：希望 worktree root 支援 repo 相對路徑](https://github.com/herdrdev/herdr/discussions/3310)。這是第一代功能請求；不能只靠貼文推定第二代已提供此設定。第二代研究版本 root 是 mod 中的常數。[H6]
- [#553：bare repo 加 sibling worktrees 的分組問題](https://github.com/herdrdev/herdr/discussions/553)。這是在討論 UI 分組與 checkout 的差異；不能把期望的 UI 當成所有版本已實作。第二代的 grouping 要看 `spaces/main.js` 的 Git common-dir、linked 與 main checkout Space 是否存在。[H7]

討論作為需求和陷阱線索；本文的功能結論採用固定 commit 的實作，不把使用者需求、其他分支 prototype 或最新網站宣傳當成已下載版本的功能。


### 10.1 網路使用者怎麼看：優點、成本與原碼對照

查閱日期：2026-11-03。以下是具名作者的使用筆記、評測及 GitHub 討論，**不是使用者滿意度調查，也沒有找到可作為結論的兩代同條件 Linux benchmark**。不同時間、平台與版本的經驗分別列出；不把 macOS 個案推論成 Linux 必然重現。

| 來源、日期與代別 | 使用者／作者看重或遇到的事 | 優點或成本如何理解 | 與原碼對齊及限制 |
| --- | --- | --- | --- |
| David Mytton，[Console 評測](https://console.dev/tools/herdr)，2026-06-11，第一代 TUI | 肯定既有終端機、鍵盤與滑鼠操作，以及 detach／reattach 工作方式；提醒 live server handoff 當時仍屬實驗性 | 若已熟悉終端機，第一代能保留既有工作習慣；handoff 與 detach 要分開看 | 第一代有 session server 與 client 分工，可支持 detach 的功能敘述；「好用」是評測者判斷，不是第二代較差的證據。handoff 的評價只代表當時，不能作為所有版本的狀態。[H1][H12] |
| Nicolas Deville，[個人使用筆記](https://notes.nicolasdeville.com/apps/herdr/)，頁面討論 2026-08～09 的第一代版本 | 以終端機中的 agent 狀態、通知與 session 整理理解產品價值，也特別整理通知和設定的學習成本 | 多 agent 的收益主要是看出誰需要你，不能只以開多少 panes 衡量；新使用者仍需理解通知與設定 | 此文以 workspace、prefix keys 和第一代版本為背景；不能當成第二代 Space 或 core 的實測。功能依原碼可以查到，生產力提升仍是個人體驗。[H1][H9] |
| scottames，[GitHub #553](https://github.com/herdrdev/herdr/discussions/553)，2026-06-10，第一代 | 喜歡 worktree 分組，但希望 bare repo 的 main checkout 成為可見 parent，避免多一層沒有實際工作的 container row | 自動分組有用，但 repo 磁碟結構不一定符合使用者想看的 UI 結構 | 需求不表示已實作；第二代實際 grouping 使用 common-dir、linked 與 main Space 判斷，應另外核對，不能只換 workspace 名稱就推定問題解決。[H7] |
| sdemura 等，[GitHub #3310](https://github.com/herdrdev/herdr/discussions/3310)，2026-08-27 起，第一代需求 | 希望 worktree 與 repo 靠近，方便和 Claude/Codex 共用同一組 checkout；也有人偏好 sibling 路徑 | 集中管理與 repo-local layout 各有需求；路徑彈性會影響團隊流程 | 對第二代研究 snapshot 而言，root 在 mod 是常數；可手動 Git 建 checkout 再開 Space。貼文中的其他 agent config 繼承主張未在本研究驗證。[H6] |
| bonanyan，[GitHub #5760](https://github.com/herdrdev/herdr/discussions/5760)，2026-11-02，談 layouts/mods 的桌面 app；貼文未列版本及 OS | 安裝 herdr-pets 後，切換 layout 就看不到它 | 第二代可自訂介面是彈性，也需要理解「安裝 mod」與「layout 是否放置它」是不同事情 | app layout 是 block/container tree，可包含 mod；切換後是否顯示取決於布局。這支持其架構原因，但未重現該第三方 mod 個案，也不把它判為 core runtime 故障。[H13] |
| fidelisakilan，[GitHub #5762](https://github.com/herdrdev/herdr/discussions/5762)，2026-11-02，app 0.1.12／hc 0.1.17／macOS 27.0.1 | 原本在 Ghostty 設定好的捲動速度不適用 app，回看 Claude 輸出會捲過頭，希望有 app 專用調整 | 原生 app 有自己的 terminal UI；原終端機的細節設定不一定繼承，可能增加調整成本 | 第一代 source 有 `ui.mouse_scroll_lines`，第二代 snapshot 在自己的 `terminal.rs` 處理 scroll，settings 未提供等同欄位。貼文版本比本機 snapshot 新；不能據此宣稱最新版或 Linux 一定缺少設定／有相同體感。[H14] |

這些資料支持的差別，是工作習慣、介面控制與路徑／擴充設定的取捨；它們不能證明第一代或第二代整體更快、更穩或更適合所有人。第二代官方 README 提到圖形桌面與 Vulkan 需求、core 的程序持續性及 mods 管理，但這些是供應方說明，不能充作獨立使用者好評。[H11]

對目前 Android Linux 案例，可先用同一套 source root、相同 agent 命令與相同 build command 比較日常操作：哪個畫面容易找到等待中的 agent、捲動與快捷鍵是否順手、實際 worktree 路徑是否符合團隊需求。尚未進行這種對照測試，因此本文不給效能或穩定性排名。

## 11. 企業內網與本案例界線

Herdr 第一代與第二代 app/core 都有原生 Rust 實作，不使用 Orca 的 Electron 執行方式；公司核准 Electron 並不代表 Herdr 原生執行檔已核准。API token 是否可用由已安裝的 agent CLI 與公司 endpoint 設定決定；Space／worktree 不提供模型服務。本文未驗證公司安裝、登入、計費、長時間 build 或真實 agent 費用。[H1][H2][H3]

## 來源索引

- [H1] [Herdr 1 snapshot](https://github.com/herdrdev/herdr/tree/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde)，`Cargo.toml`、`src/main.rs`。
- [H2] [core AGENTS：職責與限制](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/AGENTS.md)，[API types](https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/crates/herdr-core/src/api/types.rs)。
- [H3] [app AGENTS](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/AGENTS.md)，[app 操作手冊](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/SKILL.md)。
- [H4] [app commands.rs](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/commands.rs#L32)，`space.new`、`tab.new`、`terminal.open`。
- [H5] [app window.rs::new_space](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2309)。
- [H6] [app shipped worktree mod](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/worktree/main.js)，root 在 L16，`repoOf` 在 L99 左右，建立在 L182，移除在 L209。
- [H6a] [app + menu](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/new-menu/main.js#L70)，[Space menu](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/menu/main.js#L59)，兩者來源 cwd 的傳入方式不同。
- [H7] [app shipped spaces mod](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/spaces/main.js)，Git common-dir 辨識與 group 排序。
- [H8] [Herdr 1 worktree.rs](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/worktree.rs)，[config model](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/config/model.rs)。
- [H9] [Herdr 1 workspace schema](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/api/schema/workspaces.rs)，[creation](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/app/creation.rs)，[startup cwd](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/server/headless/bootstrap.rs#L107)。
- [H10] [Herdr 1 Git discovery](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/workspace/git/discovery.rs)，[worktree UI](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/client/shell/worktrees.rs)。
- [G1] [Git worktree 官方文件](https://git-scm.com/docs/git-worktree)。
- [A1] [Android Repo 官方指令文件](https://source.android.com/docs/setup/reference/repo)。
- [A2] [AOSP build 流程](https://source.android.com/docs/setup/start)。

- [H11] [第二代 README：Linux 安裝條件、畫面與程序生命週期](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/README.md)。
- [H12] [第一代 session-state 文件](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/docs/next/website/src/content/docs/session-state.mdx)。
- [H13] [第二代 layout tree 與 mod block](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/layout.rs)，mod content 與 `visible_blocks` 等實作。
- [H14] [第一代 mouse_scroll_lines 設定](https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/config/model.rs#L961)，[第二代 terminal 捲動](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/terminal.rs#L788)，[第二代 settings](https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/settings.rs)。
