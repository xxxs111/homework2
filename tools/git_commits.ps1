# 把项目按模块拆成多次提交，生成一份可读的提交历史。
# 用法（在作业根目录 homework/ 下执行）：
#     powershell -ExecutionPolicy Bypass -File .\tools\git_commits.ps1
#
# 说明：如果你本地是边开发边提交的，请按自己的真实时间线提交，不要用这个脚本覆盖历史。
#       这个脚本适合「代码已经写好、需要整理一份模块化提交记录」的情况。

$ErrorActionPreference = "Stop"

# 找 git：优先 PATH，找不到就去 Git for Windows 的默认安装位置（本机就是这种情况）
$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) {
    foreach ($candidate in @("$env:ProgramFiles\Git\cmd\git.exe",
                             "${env:ProgramFiles(x86)}\Git\cmd\git.exe",
                             "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe")) {
        if (Test-Path $candidate) { $git = $candidate; break }
    }
}
if (-not $git) {
    Write-Host "没有找到 git，请先安装 Git：https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}
Write-Host "使用 git：$git" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    & $git init
    & $git branch -M main
    Write-Host "已初始化仓库" -ForegroundColor Green
}

# 没有配置身份时给一个仓库级的中性署名，避免提交失败；想署自己的名字可以改这两行
if (-not (& $git config --local user.name)) {
    & $git config --local user.name "arrow-arrows"
    & $git config --local user.email "arrow-arrows@users.noreply.github.com"
    Write-Host "已写入仓库级署名 arrow-arrows（不署名到个人）" -ForegroundColor DarkGray
}

function Commit-Group {
    param([string]$Message, [string[]]$Paths)
    foreach ($path in $Paths) {
        if (Test-Path $path) { & $git add $path }
    }
    $staged = & $git diff --cached --name-only
    if (-not $staged) {
        Write-Host "跳过（没有内容）：$Message" -ForegroundColor DarkGray
        return
    }
    & $git commit -m $Message | Out-Null
    Write-Host "已提交：$Message" -ForegroundColor Green
}

Commit-Group "chore: 添加 .gitignore，排除存档与缓存" @(".gitignore")
Commit-Group "feat: 完成棋盘与箭头数据结构、四方向路径检测" @(
    "arrow_arrows/__init__.py", "arrow_arrows/__main__.py", "arrow_arrows/main.py",
    "arrow_arrows/core/__init__.py", "arrow_arrows/core/model.py")
Commit-Group "feat: 实现可解关卡生成（逆向走廊构造法）与求解器" @(
    "arrow_arrows/core/generator.py", "arrow_arrows/core/solver.py")
Commit-Group "feat: 加入配色、字体与图形绘制（霓虹箭头外观）" @(
    "arrow_arrows/ui/__init__.py", "arrow_arrows/ui/theme.py", "arrow_arrows/ui/shapes.py")
Commit-Group "feat: 完成开始/游戏/结算界面、音效与进度存档" @(
    "arrow_arrows/ui/widgets.py", "arrow_arrows/ui/scenes.py",
    "arrow_arrows/ui/audio.py", "arrow_arrows/ui/storage.py")
Commit-Group "feat: 主循环、状态机与飞出/碰撞动画" @(
    "arrow_arrows/ui/app.py", "arrow_arrows/ui/board_view.py")
Commit-Group "test: 补充规则、界面集成与作业测试表 T01-T06 用例" @("arrow_arrows/tests")
Commit-Group "chore: 添加无头截图与逐关试玩验证脚本" @("arrow_arrows/tools")
Commit-Group "docs: 完善 README、实验报告与博客" @(
    "README.md", "实验报告.md", "博客.md", "提交到GitHub.md", "tools")

Write-Host ""
Write-Host "提交历史：" -ForegroundColor Cyan
git log --oneline
Write-Host ""
Write-Host "接下来关联远程仓库并推送：" -ForegroundColor Cyan
Write-Host "  git remote add origin https://github.com/<你的用户名>/<仓库名>.git"
Write-Host "  git push -u origin main"
