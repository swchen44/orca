# Herdr 案例：第一代 Workspace 與第二代 Space

整理日期：2026-11-03。本文以已下載的原始碼為準，從單一 repo 逐步說明到 Android 多 repo build。命令與路徑皆為示例，尚未執行；研究版本列於文末。另見 [Orca 案例](orca-project-workspace.md)及 [Orca／Herdr 比較](ocra-herdr-project-worksapce-comparsion.md)。

## 先認識兩代

**以「整理一組終端機和 agents」來看，第一代 Workspace 可以對應第二代 Space；兩者的架構、設定與部分功能則不同。**

| | 第一代 | 第二代 |
| --- | --- | --- |
| 原始碼 | `herdr` | `herdr-app` ＋ `herdr-core` |
| 操作畫面 | 終端機中的 TUI | GPUI 桌面視窗 |
| 程序由誰維持 | Herdr session server | 獨立的 herdr-core |
| 工作容器 | Workspace → Tab／Pane | Space → Tab → Pane |
| 常用命令 | `herdr workspace ...` | `herdr-app do space.new ...` |
| 執行程序／agent | 在 workspace 的終端機中執行 | 在 Space 終端機執行，或由 `hc` 管理 |
| Git worktree | 內建 CLI／UI | app 的 worktree mod |

「Herdr 2」是 app 原始碼使用的名稱，不代表 release 版本一定是 `2.x`。下文每個案例都分別列出兩代用法；命令不要混用。[架構依據][H2] · [app 說明][H3]

**共通原則：開 Workspace／Space 不會複製程式碼；建立 Git worktree 才會產生該 repo 的另一份工作目錄。** 多個終端機指向同一資料夾，仍會修改相同檔案。

## 案例 1：開啟一個既有 Git repo

需求：研究 `D:\git\clinic_bookmarklet`，使用 Codex 或 Claude。

**第一代**

```powershell
herdr workspace create --cwd 'D:\git\clinic_bookmarklet' --label clinic-study --focus
```

**第二代**

```powershell
herdr-app do space.new --name clinic-study --folder 'D:\git\clinic_bookmarklet'
```

在新終端機確認目錄，再執行公司已設定好的 `codex` 或 `claude`。

| 相同觀念 | 差異 |
| --- | --- |
| 都是把終端機開在現有 checkout；修改會直接寫入原目錄。 | 第一代叫 Workspace，第二代叫 Space；畫面與指令不同。 |
| 都不會因為建立工作容器而 clone、搬移 repo 或新增 branch。 | 第一代重跑 `herdr` 可能只是接回既有 session；第二代 New space 按鈕也不保證詢問 folder。精準開目錄可用上述命令。 |

來源：[第一代建立流程][H9] · [第二代建立流程][H5]

## 案例 2：同一個 repo，讓兩個 agent 分別嘗試

需求：Codex 和 Claude 各修一次 bug，比較結果。

**第一代**

在 repo 的側邊欄選單選 **New worktree**；或用 CLI 明確指定起點和路徑：

```powershell
herdr worktree create --cwd 'D:\git\clinic_bookmarklet' --branch fix-a --base master --path 'D:\worktrees\clinic-a'
herdr worktree create --cwd 'D:\git\clinic_bookmarklet' --branch fix-b --base master --path 'D:\worktrees\clinic-b'
```

`master` 僅為此例起點，使用前確認 repo 的實際 branch／commit，並使用尚未占用的路徑和 branch。

**第二代**

在 repo Space 的選單或 `+` 選單選 **New worktree**，分別輸入 `fix-a`、`fix-b`。內建 mod 會建立 Git checkout，再開成 Space。

```text
原始 repo：D:\git\clinic_bookmarklet

第一代自訂路徑                 第二代內建預設路徑（假設 home 為此使用者）
D:\worktrees\                 C:\Users\swche\.herdr\worktrees\clinic_bookmarklet\
├── clinic-a\ → Codex          ├── fix-a\ → Codex
└── clinic-b\ → Claude         └── fix-b\ → Claude
```

| 相同觀念 | 差異 |
| --- | --- |
| 每個 worktree 有自己的工作目錄；可分別 review、commit，再選擇或整合修改。 | 第一代 CLI 可指定 `--path`、`--base`，並有 worktree directory 設定。 |
| 一個 worktree 只屬於一個 Git repo；不是安全沙箱。 | 第二代研究版本的 mod 固定 root 為 `~/.herdr/worktrees`，新 branch 從來源 checkout 的 HEAD 建立；已有 branch 則嘗試直接 checkout。 |

第二代 Space 選單主要取第一個 terminal 的 cwd，`+` 選單使用焦點 pane 的 cwd。若 panes 位於不同目錄，先確認來源 checkout。

來源：[第一代 Git 命令][H8] · [第二代 worktree mod][H6] · [選單來源][H6a]

## 案例 3：自行指定絕對／相對路徑

需求：worktree 必須放在團隊約定的位置。

**第一代**

絕對路徑可使用案例 2 的 `--path`。若要跨工具共用自訂 checkout，也可使用下方一般 Git 做法，再以 `workspace create` 開啟。

**第二代**

研究版本的內建 mod 沒有 root 或 base ref 設定。可先用 Git 建立，再以 `space.new` 開啟。

以下先用 Git 建立一個相對路徑的 worktree，**兩代都能使用**：

```powershell
git -C 'D:\git\clinic_bookmarklet' worktree add -b example-b '../clinic-b' master
```

`git -C` 先切到 repo，因此 `../clinic-b` 的結果是 `D:\git\clinic-b`。要使用絕對路徑，可將該參數換成 `D:\worktrees\clinic-b`；不要重複建立已存在的 branch／路徑。

接著依使用的代別選一個命令：

```powershell
# 第一代
herdr workspace create --cwd 'D:\git\clinic-b' --label clinic-b --focus

# 第二代
herdr-app do space.new --folder 'D:\git\clinic-b'
```

| 相同觀念 | 差異 |
| --- | --- |
| checkout 由 Git 管理，開啟工作容器只是將終端機放進該目錄。 | 第一代有自己的 worktree 路徑設定；第二代 mod 的固定 root 不會讀取它。 |
| 上例相對路徑以 Git 的工作目錄解析。 | 不要把這個 Git 行為誤認成兩代都有「repo 相對 root 設定」。 |

Git 的連結靠 checkout 的 `.git` 指標與共用 Git 管理資料，整個目錄不必是 symlink／junction。objects 和一般 refs 共用；工作目錄、HEAD、index 分開。可用 `git worktree list` 核對。[Git worktree 文件][G1]

## 案例 4：研究父資料夾，底下有多個 repo

需求：`D:\git\yazi_work` 是普通資料夾，想讓 agent 比較裡面的程式碼。

```text
D:\git\yazi_work\
├── yazi_intranet\       # Git repo
└── other-repo\          # 未來可能加入，名稱僅示意
```

**第一代**

```powershell
herdr workspace create --cwd 'D:\git\yazi_work' --label yazi-study --focus
```

**第二代**

```powershell
herdr-app do space.new --name yazi-study --folder 'D:\git\yazi_work'
```

| 相同觀念 | 差異 |
| --- | --- |
| 普通資料夾也能作為工作起點，不必先變成 Git repo。 | 第一代 Git discovery 從 cwd 向父目錄找 Git repo；第二代 mod 也從來源 folder 查 Git。 |
| agent 可跨子目錄閱讀，但父資料夾不會因此變成一個 Git repo。 | 第二代側邊欄的 worktree 分組根據 common-dir 等資訊，不是掃描任意父資料夾並匯入所有子 repo。 |

要隔離修改 `yazi_intranet`，將兩代命令中的路徑改成 `D:\git\yazi_work\yazi_intranet`，再替它建立 worktree。不要從非 Git 父目錄期待一次建立全部子 repo 的 worktree。

來源：[第一代 Git discovery][H10] · [第二代 Space][H5] · [第二代 Git 分組][H7]

## 案例 5：前後端分開的請假系統

需求：新增主管審核功能，前端和 API 在不同 repo。

```text
D:\company\leave-system\
├── leave-web\           # Git repo A
├── leave-api\           # Git repo B
└── notes\               # 普通筆記
```

| 步驟 | 第一代 | 第二代 |
| --- | --- | --- |
| 1. 整體研究 | 在父目錄開 `leave-study` Workspace。 | 在父目錄開 `leave-study` Space。 |
| 2. 隔離修改 | 為 web、API 各建立 worktree Workspace。 | 為 web、API 各建立 worktree Space。 |
| 3. 分工 | web agent 和 API agent 先協調介面，再各自修改。 | 相同。 |
| 4. 整合測試 | 將各 repo 已 review 的 commit 帶入實際跑測試的 checkout。 | 相同。 |

**相同觀念：** 兩個 repo 的 branch、commit 和合併各自處理；外部 worktree 的修改不會自動寫進原父目錄。

**差異：** 開啟容器與建立 worktree 的命令／UI 不同，跨 repo 的協調責任相同。這是利用一般 Git 與終端機組成的流程，兩代都沒有在本研究中確認會自動建立整套跨 repo feature。

來源：[第一代建立與 Git 流程][H8] · [第二代建立與 Git 流程][H6]

## 案例 6：Android 一套 source tree，研究並 build image

需求：公司使用 Repo manifest 管理數十個 Git projects，最後由一個 build command 產生 image。

```text
/work/android-main/
├── .repo/                         # Repo 管理資料
├── frameworks/base/               # Git project
├── packages/apps/Settings/        # Git project
├── device/company/product/        # 示意 Git project
└── out/                           # 輸出位置依公司設定
```

這是 Repo 的 manifest XML，與 app 的 `AndroidManifest.xml` 不同。以下假設完整 source tree 已依公司流程準備好，且**兩代都在本機 Linux 使用**。[Android Repo 文件][A1]

**第一代**

```sh
herdr workspace create --cwd /work/android-main --label android-integration --focus
```

**第二代**

```sh
herdr-app do space.new --name android-integration --folder /work/android-main
```

兩代接下來的操作相同：

1. 在工作終端機確認 `pwd` 和 `repo status`。
2. 執行 agent，研究或修改需要的 Git projects。
3. 在 source root 執行公司的 build command。標準 AOSP 流程為 `source build/envsetup.sh`、`lunch <target>`、`m`；公司流程可能不同。
4. 分別 review、提交修改過的 repo，記錄 image 與測試結果。

| 相同觀念 | 差異 |
| --- | --- |
| root 工作容器可放 Claude、Codex、build 等終端機；會直接修改這棵 tree。 | 第一代使用 TUI 和 session server；第二代使用桌面 app 和獨立 core。 |
| source root 通常不是單一 Git repo，不能一次 New worktree 就隔離整棵 Android tree。 | 在無圖形桌面的 Linux host，第一代可用 TUI；第二代 app 需桌面及相容 Vulkan，core 則可單獨使用。 |

第一代 Workspace 和第二代 Space 在此用途上可直接對應。再開一個容器指向相同 root，仍會共用 source 與 build output。

來源：[第一代建立流程][H9] · [第二代建立流程][H5] · [Linux app 條件][H11] · [AOSP build][A2]

## 案例 7：Android 多 agent 分工，再整合成 image

需求：三個 agent 分別新增系統 API、Settings 頁面及產品預設值。

```text
完整整合 tree：/work/android-main/
├── frameworks/base/               ← 接收系統 API commit
├── packages/apps/Settings/        ← 接收 UI commit
└── device/company/product/        ← 接收產品設定 commit

外部隔離 checkout：
├── base-feature/                  ← agent A
├── settings-feature/              ← agent B
└── product-feature/               ← agent C
```

| 步驟 | 第一代 | 第二代 |
| --- | --- | --- |
| 1. 開整合環境 | 以案例 6 建立 root Workspace。 | 以案例 6 建立 root Space。 |
| 2. 確認版本 | 查每個 project 的 commit、branch 和未提交修改。 | 相同。 |
| 3. 建立隔離 checkout | 對各 Git project 建 worktree；CLI 可指定 base／path。 | 對各 project 使用 mod；自訂起點／路徑時先用 Git 建立，再開 Space。 |
| 4. 分派工作 | 三個 worktree Workspace，各跑一個 agent。 | 三個 worktree Space，各跑一個 agent。 |
| 5. 整合 | 各自 review、commit，再依公司 Git／Gerrit 流程帶回整合 tree。 | 相同。 |
| 6. Build | 在 `/work/android-main` 執行公司 build command，產生 image。 | 相同。 |

**相同觀念：** 完整 build 不會自動採用外部 worktree 的檔案。要將修改帶入真正 build 的 checkout，再檢查、build。記錄 manifest revisions、commit、target 和測試結果；`repo manifest -r` 不包含未提交檔案或所有外部 build 輸入。

**差異與限制：** 第一代 CLI 的 path／base 彈性較直接；第二代研究版 mod 固定 root、由來源 HEAD 建新 branch。Repo 的 common-dir 可能在 `.repo/projects/...git`，兩代都應先選一個 project 驗證相容性。第二代還會用 common-dir 推導名稱和分組，不能保證呈現方式與普通 `.git` checkout 相同。

若要兩組任務**平行 build 兩份完整 image**，兩代都建議使用兩套完整 Repo client 與獨立輸出目錄，再分別開 Workspace／Space。這需要公司 Repo／build 流程，不是一個涵蓋所有 Git projects 的 worktree。

來源：[第一代 worktree][H8] · [第二代 mod][H6] · [Git worktree][G1] · [Android Repo][A1]

## 案例 8：Build 很久，想關閉畫面再回來

| 動作 | 第一代 | 第二代 |
| --- | --- | --- |
| 離開畫面，背景繼續跑 | detach client，session server 維持程序。 | 關 app 視窗，core 維持程序。 |
| 回來看進度 | 接回原 session。 | 重新開 app，連回 core。 |
| server／core crash 或重開機 | 原程序已中斷；可恢復布局、新 shell，符合條件的 agent 可用 native session resume。 | 研究版 kept terminal 回到最後目錄的新 shell，不能套用第一代的 agent resume 保證。 |
| 關閉 pane／tab | 是結束／移除工作終端機的操作，不是單純 detach。 | 會結束其中的終端機；與關視窗不同。 |

**相同觀念：** 關閉觀看畫面與停止程序是兩件事。detach 不等於重開機後原 build 還活著。

**差異：** 程序分別由 session server 或 core 持有，agent 對話的恢復條件也不同。長時間 Android build 應確認自己做的是 detach／關視窗，而非關閉 build pane。

來源：[第一代生命週期][H12] · [第二代生命週期][H11]

## 使用者怎麼看：優點與取捨

以下保留具名評測與回報，並標示適用代別。它們不是兩代同條件測試，不能用來判定哪代一定較快或較穩。

| 觀點 | 適用代別、來源 | 與案例的關係 |
| --- | --- | --- |
| 能沿用既有終端機、鍵盤／滑鼠操作，detach 後再接回。 | 第一代；David Mytton，[Console](https://console.dev/tools/herdr)，2026-06-11。 | 案例 8 的便利；該文對 handoff 的實驗性提醒僅代表當時版本。 |
| agent 狀態與通知有助找到等待處理的工作，但仍要理解設定。 | 第一代；Nicolas Deville，[使用筆記](https://notes.nicolasdeville.com/apps/herdr/)，談 2026-08～09 版本。 | 案例 2、7 的多 agent 管理。生產力提升屬個人體驗。 |
| bare repo 的 UI 分組不一定符合日常工作的 checkout 層級。 | 第一代需求；scottames，[#553](https://github.com/herdrdev/herdr/discussions/553)，2026-06-10。 | 案例 2、7：分組外觀和 Git 連結不同；第二代也需核對 common-dir 判斷。[H7] |
| 希望 worktree 放 repo 內或 sibling 位置，方便其他工具共用。 | 第一代需求；sdemura 等，[#3310](https://github.com/herdrdev/herdr/discussions/3310)，2026-08-27 起。 | 案例 3：路徑彈性是實際需求；第二代 snapshot 的 root 是 mod 常數。[H6] |
| 安裝 mod 後切換 layout，mod 就看不到了。 | 桌面 app；bonanyan，[#5760](https://github.com/herdrdev/herdr/discussions/5760)，2026-11-02；未列 OS／版本。 | 第二代 layout 決定要放哪些 mod；可自訂也需要理解配置。未重現該第三方 mod 個案。[H13] |
| 外部 Ghostty 的捲動設定不會控制 app，閱讀 agent 輸出時覺得容易捲過頭。 | 第二代；fidelisakilan，[#5762](https://github.com/herdrdev/herdr/discussions/5762)，2026-11-02；app 0.1.12／hc 0.1.17／macOS。 | 桌面版有自己的 terminal 捲動程式；不可推論 Linux 或最新版有相同體感。[H14] |

使用者回報支持的是**工作習慣與設定成本的取捨**：第一代可沿用終端機；第二代有桌面 layout 和 JavaScript mods，但需管理自己的畫面與操作設定。這不是整體優劣排名。

第二代狀態由程序的 OSC 7501 回報，不能保證任意 CLI 都有 working／blocked 狀態。[H2] 同樣地，任何一代的普通工作容器都不提供跨 repo 原子整合、完整 Android build tree 隔離或模型服務。

## 範圍與研究版本

本文核對原始碼與隨附文件，未安裝或啟動實機測試，也未驗證公司 API gateway、Android manifest 或 build 環境。公司若只核准 Electron，仍需另外核准 Herdr 的原生執行檔。

| 原始碼 | 固定 commit |
| --- | --- |
| 第一代 `herdr` | `ee5bfb5041bb3e4a49d591c72308aae3c81ecdde` |
| 第二代 `herdr-app` | `1581a587919dddd6f1efd5f78eb542c4b2b02cb5` |
| 第二代 `herdr-core` | `27fea26efe498dce7e1555948fa75c3994fb8a9c` |

遠端版本已前進，本文描述的是這些 snapshot。功能結論以 source 為準；評測及 feature request 只代表當時觀點。

## 原始碼與官方來源

- [第一代原始碼][H1]、[workspace 建立][H9]、[Git discovery][H10]
- [第一代 worktree][H8]、[session 生命週期與 resume][H12]
- [第二代 app 架構／手冊][H3]、[命令][H4]、[Space 建立][H5]
- [第二代 worktree mod][H6]、[選單 cwd][H6a]、[側邊欄 Git 分組][H7]
- [第二代 core 職責][H2]、[Linux 條件與程序生命週期][H11]
- [第二代 layout／mod][H13]、[兩代捲動實作][H14]
- [Git worktree][G1]、[Android Repo][A1]、[AOSP build][A2]

[H1]: https://github.com/herdrdev/herdr/tree/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde
[H2]: https://github.com/herdrdev/herdr-core/blob/27fea26efe498dce7e1555948fa75c3994fb8a9c/AGENTS.md
[H3]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/SKILL.md
[H4]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/commands.rs
[H5]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/window.rs#L2309
[H6]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/worktree/main.js
[H6a]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/new-menu/main.js#L70
[H7]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/defaults/mods/spaces/main.js
[H8]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/worktree.rs
[H9]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/app/creation.rs
[H10]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/src/workspace/git/discovery.rs
[H11]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/README.md
[H12]: https://github.com/herdrdev/herdr/blob/ee5bfb5041bb3e4a49d591c72308aae3c81ecdde/docs/next/website/src/content/docs/session-state.mdx
[H13]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/layout.rs
[H14]: https://github.com/herdrdev/herdr-app/blob/1581a587919dddd6f1efd5f78eb542c4b2b02cb5/src/terminal.rs#L788
[G1]: https://git-scm.com/docs/git-worktree
[A1]: https://source.android.com/docs/setup/reference/repo
[A2]: https://source.android.com/docs/setup/start
