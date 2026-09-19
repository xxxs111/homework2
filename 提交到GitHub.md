# 提交到 GitHub 的步骤

> 本机当前**没有安装 Git**（`git --version` 提示找不到命令），所以仓库初始化与提交需要你先装好 Git。
> 装好后按下面的步骤操作即可；`tools/git_commits.ps1` 会把项目按模块拆成 9 次有意义的提交。

## 一、安装 Git（Windows）

1. 下载安装包：<https://git-scm.com/download/win>
2. 一路默认安装即可（安装完需重开一个终端，让 `git` 进入 PATH）。
3. 配置身份（提交记录里会显示）：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

## 二、初始化仓库并分模块提交

在作业根目录（`homework/`，也就是本文件所在目录）打开 PowerShell，执行：

```powershell
# 方式一：一键按模块提交（推荐，脚本见 tools/git_commits.ps1）
powershell -ExecutionPolicy Bypass -File .\tools\git_commits.ps1
```

或者手动执行下面九条（与脚本内容一致，可按自己的真实开发节奏调整）：

```bash
git init
git branch -M main

git add .gitignore
git commit -m "chore: 添加 .gitignore，排除存档与缓存"

git add arrow_arrows/__init__.py arrow_arrows/__main__.py arrow_arrows/main.py arrow_arrows/core/__init__.py arrow_arrows/core/model.py
git commit -m "feat: 完成棋盘与箭头数据结构、四方向路径检测"

git add arrow_arrows/core/generator.py arrow_arrows/core/solver.py
git commit -m "feat: 实现可解关卡生成（逆向走廊构造法）与求解器"

git add arrow_arrows/ui/__init__.py arrow_arrows/ui/theme.py arrow_arrows/ui/shapes.py
git commit -m "feat: 加入配色、字体与图形绘制（多格长箭头外观）"

git add arrow_arrows/ui/widgets.py arrow_arrows/ui/scenes.py arrow_arrows/ui/audio.py arrow_arrows/ui/storage.py
git commit -m "feat: 完成开始/游戏/结算界面、音效与进度存档"

git add arrow_arrows/ui/app.py arrow_arrows/ui/board_view.py
git commit -m "feat: 主循环、状态机与飞出/碰撞动画"

git add arrow_arrows/tests
git commit -m "test: 补充规则、界面集成与作业测试表 T01-T06 用例"

git add arrow_arrows/tools
git commit -m "chore: 添加无头截图与逐关试玩验证脚本"

git add README.md 实验报告.md 博客.md 提交到GitHub.md tools
git commit -m "docs: 完善 README、实验报告与博客"
```

查看提交历史：`git log --oneline --graph`

## 三、推到 GitHub

1. 在 GitHub 网页上新建仓库（**不要**勾选 Add README / .gitignore，避免冲突），拿到仓库地址。
2. 关联并推送：

```bash
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

3. 之后每次修改：

```bash
git add -A
git commit -m "fix: 修复 xxx"
git push
```

## 四、提交前自查（作业注意事项）

```bash
# 1. 确认没有把敏感信息提交上去（应无任何输出）
git grep -nE "(api[_-]?key|token|secret|password|cookie)" -- . ":!*.md"

# 2. 确认本地存档没有被跟踪（应无输出）
git ls-files | findstr progress.json

# 3. 确认程序能按 README 的说明跑起来
pip install pygame
python arrow_arrows/main.py
python -m unittest discover -s arrow_arrows/tests -t .
```

## 五、推荐 commit 信息（作业参考格式）

| 参考示例 | 本项目实际使用 |
| --- | --- |
| `feat: 完成游戏棋盘和箭头显示` | `feat: 完成棋盘与箭头数据结构、四方向路径检测` |
| `feat: 实现四个方向的路径检测` | 同上（位掩码 O(1) 扫描） |
| `feat: 增加碰撞反馈和失误次数` | `feat: 主循环、状态机与飞出/碰撞动画` |
| `feat: 增加关卡切换功能` | `feat: 实现可解关卡生成（逆向走廊构造法）与求解器` |
| `fix: 修复向上检测时的数组越界` | 边界朝外箭头的越界问题已由测试 T03 覆盖 |
| `docs: 完善README和运行说明` | `docs: 完善 README、实验报告与博客` |
