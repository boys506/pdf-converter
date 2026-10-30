# 推送到 GitHub · 三步走

> 说明：`.gitignore` 已排除 `.venv`（133MB）、`dist`（85MB）、`build` 和临时文件，
> 仓库实际只有几百 KB，很干净。exe 通过 Releases 发布，不占仓库体积。

---

## 第 0 步：先确认这台电脑有没有 git

在 `D:\dshwork\转pdf` 地址栏输入 `cmd` 回车，敲：

```bat
git --version
```

**如果显示 `git version 2.x.x`** → 正常，继续第 1 步。

**如果显示 `'git' 不是内部或外部命令`** → 说明 git 没装或没进 PATH，三种解决办法：

| 办法 | 说明 |
| --- | --- |
| **用 `push_github.bat`（推荐）** | 脚本会自动在常见位置找 git（含本机自带的便携版），不用配环境变量 |
| 临时把 git 加进当前窗口的 PATH | 粘贴下面这行，之后 `git` 就能用了，关掉窗口失效 |
| 安装 Git for Windows | https://git-scm.com/download/win ，装完重开 cmd |

本机自带的 git 在 `D:\workbuddy\WorkBuddyAI\resources\vendor\PortableGit\cmd\`，
临时启用：

```bat
set "PATH=D:\workbuddy\WorkBuddyAI\resources\vendor\PortableGit\cmd;%PATH%"
git --version
```

> 注意：`set PATH` 只在当前 cmd 窗口有效，换窗口要重新执行。
> 想一劳永逸就装 Git for Windows，或者右键「此电脑 → 属性 → 高级系统设置 →
> 环境变量」把上面的 `cmd` 目录加进 Path。

---

## 第 1 步：在 GitHub 上建一个空仓库

1. 打开 https://github.com/new
2. **Repository name** 填 `pdf-converter`（想用别的名字也行，后面命令里改）
3. **Public / Private** 按需要选
4. ⚠️ 下面的 `Add a README file`、`Add .gitignore`、`Choose a license` **全部不要勾**
5. 点 `Create repository`

---

## 第 2 步：本地提交并推送

打开项目文件夹 `D:\dshwork\转pdf`，在地址栏输入 `cmd` 回车（或右键 → 在终端中打开），
依次执行（把 `<你的用户名>` 换成你的 GitHub 用户名）：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"

git init -b main
git add -A
git commit -m "feat: PDF 转换工坊 - 多格式批量转 PDF 桌面工具"

git remote add origin https://github.com/<你的用户名>/pdf-converter.git
git push -u origin main
```

推送时会要求登录：

- **用户名**：你的 GitHub 用户名
- **密码**：**不能用账号密码**，必须用 Personal Access Token

### 怎么拿 Token

1. GitHub 右上角头像 → `Settings`
2. 左侧最下方 → `Developer settings`
3. `Personal access tokens` → `Tokens (classic)` → `Generate new token (classic)`
4. Note 随便填，Expiration 选 30 天或 90 天，勾选 **`repo`** 这一项
5. 生成后复制那串 `ghp_...`，**粘贴到密码位置**（只显示一次，记得先存下来）

> 嫌每次输麻烦：`git config --global credential.helper manager`，
> Windows 会弹窗登录并记住凭据。
>
> 或者改用 SSH：`git remote set-url origin git@github.com:<你的用户名>/pdf-converter.git`，
> 需先在本机配置 SSH key 并加到 GitHub。

### 更省事：用一键脚本

上面的命令可以全部交给仓库里的 `push_github.bat`，它已经帮你写好 `.gitignore`、
建好 main 分支、配好 remote（已实测通过）：

```bat
push_github.bat <你的GitHub用户名> pdf-converter "你的名字" "你的邮箱@example.com"
```

后两个参数是提交作者，只对当前仓库生效，不会污染全局配置。
不带参数运行会显示用法。推送时同样需要输入 Token 作为密码。

---

## 第 3 步：把 exe 传到 Releases（推荐）

`dist/` 不进仓库，所以程序要通过 Release 附件分发：

1. 打开仓库页 → 右侧 `Releases` → `Create a new release`
2. **Choose a tag** 输入 `v1.0.0` → 点 `Create new tag`
3. Release title 填 `v1.0.0 首个版本`
4. 描述里写点功能说明（可以直接抄 README）
5. 把 `D:\dshwork\转pdf\dist\PDF转换工坊.zip`（30MB）拖到 **Attach binaries** 区域
6. 点 `Publish release`

README 里的 `[Releases](../../releases)` 链接会自动指向这个页面。

> 注意：单个附件上限 2GB，30MB 完全没问题。

---

## 之后怎么更新

改完代码后：

```bash
git add -A
git commit -m "fix: 修复 xxx"
git push
```

发新版本就再建一个 Release（tag 用 `v1.0.1`）。

---

## 常见问题

**Q：`'git' 不是内部或外部命令，也不是可运行的程序`**
A：git 没装或没加进 PATH。用 `push_github.bat`（会自动找），
或临时执行 `set "PATH=D:\workbuddy\WorkBuddyAI\resources\vendor\PortableGit\cmd;%PATH%"`，
或安装 Git for Windows 后重开窗口。详见第 0 步。

**Q：`git push` 报 `remote: Repository not found`**
A：仓库没建、名字拼错，或者 Token 没勾 `repo` 权限。私有仓库还必须勾 `repo`。

**Q：报 `failed to push some refs` / `rejected`**
A：远程已有提交（建仓库时勾了 README）。先 `git pull --rebase origin main` 再 push，
或者干脆删掉仓库重建一个空的。

**Q：`fatal: not a git repository`**
A：没在项目目录里执行。先 `cd /d D:\dshwork\转pdf`。

**Q：`.venv` 会不会被传上去？**
A：不会，`.gitignore` 里已排除。可以用 `git status --short` 确认列表里没有 `.venv/`、`dist/`。

**Q：想连 exe 一起放仓库里？**
A：不建议（85MB，每次改动都产生新副本）。如果坚持，把 `.gitignore` 里的 `dist/` 删掉再提交，
但 GitHub 对超过 50MB 的文件会警告，100MB 直接拒绝。

**Q：想加开源许可证？**
A：GitHub 仓库页 → `Add file` → `Create new file`，文件名输入 `LICENSE`，
会提示选择模板（MIT 最常用）。
