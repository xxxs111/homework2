# 提交到 GitHub

> **当前状态：本地仓库、远程地址都已经配好了**。
> 分支 `main`，10 次按模块划分的提交，工作区干净，已确认没有敏感信息；
> `origin` 已指向 `https://github.com/xxxs111/homework2.git`。
> **只剩最后一步：在你自己的终端里执行一次 `git push`（需要你的 GitHub 账号授权）。**

> 为什么最后这一步必须由你来做：推送要用你的 GitHub 账号，凭据只能由你本人授权；
> 而且当前这台机器的命令行连不上外网（`git ls-remote` 报 `Could not connect to github.com:443`），
> 所以推送只能在你自己能上网的终端里发起。

---

## 一、最快的方式：双击 `推送.bat`

项目根目录下有一个 `推送.bat`（本机辅助脚本，已加进 `.gitignore`，不会进仓库）：

1. 双击 `推送.bat`；
2. 第一次会弹出浏览器让你**登录 GitHub 授权**（Git 自带的 Credential Manager 负责，凭据只留在你本机，不会进仓库）；
3. 看到 `[成功]` 就完成了，刷新 <https://github.com/xxxs111/homework2> 即可看到代码与 10 条提交记录。

如果弹出的是「还没有配置远程仓库」，说明 remote 被清掉了，按提示粘贴
`https://github.com/xxxs111/homework2.git` 即可。

---

## 二、手动方式（等价命令）

本机的 git **已经安装但没有加进 PATH**（在 `C:\Program Files\Git\cmd\git.exe`），所以要么用完整路径，要么临时加进 PATH：

```powershell
# 方式 A：直接用完整路径
$git = "C:\Program Files\Git\cmd\git.exe"
& $git push -u origin main

# 方式 B：把 git 加进当前会话的 PATH 后再用
$env:Path += ";C:\Program Files\Git\cmd"
git push -u origin main
```

**如果推送被拒绝（`rejected ... non-fast-forward`）**：说明建仓库时勾选了 Add a README。
两种处理方式，任选其一：

```powershell
# 把远程那个 README 合并进来再推（推荐）
& $git pull --rebase origin main
& $git push -u origin main

# 或者：远程只有自动生成的 README，直接用本地内容覆盖
& $git push -u origin main --force
```

远程地址要换的话：

```powershell
& $git remote set-url origin https://github.com/<你的用户名>/<仓库名>.git
```

---

## 三、已经做好的本地仓库

```
分支：main
提交：10 条（按模块划分）
文件：40 个（源码 + 测试 + 工具 + 12 张界面截图 + 4 份文档）
大小：约 0.84 MB
远程：origin -> https://github.com/xxxs111/homework2.git
```

提交历史：

```
docs: 补充本地仓库状态与一键推送说明
docs: 完善 README、实验报告与博客
chore: 添加无头截图与逐关试玩验证脚本
test: 补充规则、界面集成与作业测试表 T01-T06 用例
feat: 主循环、状态机与飞出/碰撞动画
feat: 完成开始/游戏/结算界面、音效与进度存档
feat: 加入配色、字体与图形绘制（霓虹箭头外观）
feat: 实现可解关卡生成（逆向走廊构造法）与求解器
feat: 完成棋盘与箭头数据结构、四方向路径检测
chore: 添加 .gitignore，排除存档与缓存
```

以后想再补一次提交：

```powershell
$git = "C:\Program Files\Git\cmd\git.exe"
& $git add -A
& $git commit -m "fix: 修复 xxx"
& $git push
```

---

## 四、关于提交署名

按你的要求**没有署个人名字**，用的是仓库级的中性署名：

```
user.name  = arrow-arrows
user.email = arrow-arrows@users.noreply.github.com
```

想换成自己的名字 / 邮箱（只影响之后的提交）：

```powershell
& $git config --local user.name  "你的名字"
& $git config --local user.email "你的邮箱"
```

想把已有 9 条提交的作者一起改掉：

```powershell
& $git rebase --root --exec 'git commit --amend --no-edit --reset-author'
```

---

## 五、提交前自查（作业注意事项）

```powershell
$git = "C:\Program Files\Git\cmd\git.exe"

# 1. 确认工作区干净
& $git status --short

# 2. 确认没有把敏感信息提交上去（应无输出）
& $git grep -nE "(api[_-]?key|token|secret|password|cookie)" --

# 3. 确认本地存档没有被跟踪（应无输出）
& $git ls-files | Select-String "progress.json"

# 4. 确认程序能按 README 的说明跑起来
pip install pygame
python arrow_arrows/main.py
python -m unittest discover -s arrow_arrows/tests -t .
```

---

## 六、推荐 commit 信息（作业参考格式对照）

| 作业给的示例 | 本项目实际使用 |
| --- | --- |
| `feat: 完成游戏棋盘和箭头显示` | `feat: 完成棋盘与箭头数据结构、四方向路径检测` |
| `feat: 实现四个方向的路径检测` | 同上（改成行/列位掩码 O(1) 扫描） |
| `feat: 增加碰撞反馈和失误次数` | `feat: 主循环、状态机与飞出/碰撞动画` |
| `feat: 增加关卡切换功能` | `feat: 实现可解关卡生成（逆向走廊构造法）与求解器` |
| `fix: 修复向上检测时的数组越界` | 已由测试 T03「贴边朝外的箭头」覆盖 |
| `docs: 完善README和运行说明` | `docs: 完善 README、实验报告与博客` |

---

## 七、相关脚本

* `推送.bat`：双击即可配置远程并推送（本机辅助脚本，不进仓库）。
* `修复GitHub访问.bat` + `fix_github_hosts.ps1`：一键修复下面第八节的 hosts 问题（不进仓库）。
* `tools/git_commits.ps1`：按模块重新生成这套提交历史（会自动寻找 `git.exe`，并写入中性署名）。
  仅在「需要重新整理历史」时使用；如果你之后按真实时间线提交，不要用它覆盖。

---

## 八、如果 push 报「连不上 github.com」

按本机实际排查的结果：

* `hosts` 文件里有 22 行把 github 相关域名（`github.com`、`api.github.com`、`raw.githubusercontent.com` 等）
  指向了 `127.0.0.1`——多半是某个 GitHub 加速器 / 代理工具写进去的，这会让 **git 和浏览器都连不上 GitHub**；
* 本机到 GitHub 的真实网络**其实是通的**（直连 `20.205.243.166:443` 测试成功），只是被 hosts 挡在了前面；
* 本机装了 Clash Verge，但主程序没有运行，代理端口（7897）没有监听，系统代理也是关闭的。

### 解法 A：修 hosts（推荐，不需要梯子）

1. 双击 `修复GitHub访问.bat`；
2. UAC 弹窗点「是」（改 hosts 需要管理员权限）；
3. 它会先备份 hosts（`hosts.backup-<时间戳>`），再把那 22 行注释掉并刷新 DNS；
4. 然后双击 `推送.bat` 推送即可。想恢复原样就用备份文件覆盖回去。

等价的命令（在**管理员** PowerShell 里执行）：

```powershell
$p = "$env:SystemRoot\System32\drivers\etc\hosts"
Copy-Item $p "$p.backup" -Force
(Get-Content $p) | ForEach-Object {
    if ($_ -match 'github' -and $_ -notmatch '^\s*#') { "#$_" } else { $_ }
} | Set-Content $p -Encoding ASCII
ipconfig /flushdns
```

### 解法 B：走代理（完全不动 hosts）

```powershell
# 1) 打开 Clash Verge，开启「系统代理」（混合端口默认 7897）
# 2) 让 git 也走这个代理
$git = "C:\Program Files\Git\cmd\git.exe"
& $git config --global http.proxy  http://127.0.0.1:7897
& $git config --global https.proxy http://127.0.0.1:7897

# 3) 双击 推送.bat 推送；成功后可选择取消代理设置
& $git config --global --unset http.proxy
& $git config --global --unset https.proxy
```
