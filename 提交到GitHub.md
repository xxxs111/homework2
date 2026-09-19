# 提交到 GitHub

> **当前状态：本地仓库已经建好了**（分支 `main`，9 次按模块划分的提交，工作区干净，已确认没有敏感信息）。
> 剩下只有两步：**① 在 GitHub 网页新建空仓库；② 把本地提交推上去（需要你自己的 GitHub 账号授权）**。

---

## 一、最快的方式：双击 `推送.bat`

项目根目录下有一个 `推送.bat`（本机辅助脚本，已加进 `.gitignore`，不会进仓库）：

1. 先到 GitHub 网页新建一个**空仓库**（**不要**勾选 Add a README / .gitignore / license，否则推送会冲突）；
2. 双击 `推送.bat`；
3. 第一次运行时它会让你**粘贴仓库地址**（形如 `https://github.com/用户名/仓库名.git`）；
4. 之后会弹出浏览器让你**登录 GitHub 授权**（Git 自带的 Credential Manager 负责，凭据只留在你本机，不会进仓库）；
5. 看到 `[成功]` 就完成了，刷新仓库页面即可看到代码与 9 条提交记录。

> 为什么最后一步需要你来做：推送要用你的 GitHub 账号，凭据必须由你本人授权；
> 另外当前这台机器的命令行连不上外网（`github.com` 无法建立连接），所以推送只能在你自己的终端里发起。

---

## 二、手动方式（等价命令）

本机的 git **已经安装但没有加进 PATH**（在 `C:\Program Files\Git\cmd\git.exe`），所以要么用完整路径，要么临时加进 PATH：

```powershell
# 方式 A：直接用完整路径
$git = "C:\Program Files\Git\cmd\git.exe"
& $git remote add origin https://github.com/<你的用户名>/<仓库名>.git
& $git push -u origin main

# 方式 B：把 git 加进当前会话的 PATH 后再用
$env:Path += ";C:\Program Files\Git\cmd"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

远程地址填错了就先删掉重来：

```powershell
& $git remote remove origin
& $git remote add origin https://github.com/<你的用户名>/<仓库名>.git
```

---

## 三、已经做好的本地仓库

```
分支：main
提交：9 条（按模块划分）
文件：40 个（源码 + 测试 + 工具 + 12 张界面截图 + 4 份文档）
大小：约 0.84 MB
```

提交历史：

```
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
* `tools/git_commits.ps1`：按模块重新生成这套提交历史（会自动寻找 `git.exe`，并写入中性署名）。
  仅在「需要重新整理历史」时使用；如果你之后按真实时间线提交，不要用它覆盖。
