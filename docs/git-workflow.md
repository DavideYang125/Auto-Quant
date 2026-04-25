# Git Fork 工作流指南

## 场景说明

当你参与别人的开源项目时：
- 原项目：`TraderAlice/Auto-Quant`（上游 upstream）
- 你的fork：`你的用户名/Auto-Quant`（自己的仓库 myrepo）
- 你不能直接推送到原项目，只能推送到自己的fork

## 初始配置

### 步骤1: 在GitHub上Fork原项目

1. 访问 https://github.com/TraderAlice/Auto-Quant
2. 点击右上角 **Fork** 按钮
3. 等待完成，你就有了自己的副本

### 步骤2: 配置本地Git Remote

```bash
# 1. 添加你的fork作为remote
git remote add myrepo git@github.com:你的用户名/Auto-Quant.git

# 2. 把原来的origin重命名为upstream（上游）
git remote rename origin upstream

# 3. 验证配置
git remote -v
```

预期输出：
```
upstream  git@github.com:TraderAlice/Auto-Quant.git (fetch)
upstream  git@github.com:TraderAlice/Auto-Quant.git (push)
myrepo    git@github.com:你的用户名/Auto-Quant.git (fetch)
myrepo    git@github.com:你的用户名/Auto-Quant.git (push)
```

## 日常使用

### 推送你的修改

```bash
# 推送到你自己的仓库
git push myrepo 分支名

# 示例：推送autoresearch/apr25分支
git push myrepo autoresearch/apr25
```

### 同步上游更新

```bash
# 方式1: 获取并合并（推荐）
git fetch upstream
git merge upstream/main

# 方式2: 使用rebase（保持更干净的历史）
git fetch upstream
git rebase upstream/main

# 如果有冲突，解决后：
# merge方式：git commit
# rebase方式：git rebase --continue
```

### 提交Pull Request

如果你想贡献代码回原项目：

1. 推送到你的fork
2. 访问 `https://github.com/TraderAlice/Auto-Quant`
3. 点击 **Compare & pull request**
4. 填写PR描述并提交

## 常用命令对照

| 操作 | 命令 |
|------|------|
| 查看remote | `git remote -v` |
| 添加remote | `git remote add 名称 URL` |
| 删除remote | `git remote remove 名称` |
| 重命名remote | `git remote rename 旧名 新名` |
| 获取上游更新 | `git fetch upstream` |
| 查看上游差异 | `git diff upstream/main` |
| 同步上游 | `git merge upstream/main` |

## Remote命名约定

| Remote名称 | 用途 | 权限 |
|------------|------|------|
| upstream | 原项目（上游） | 只读 |
| origin | 你克隆的仓库（可写）| 读写 |
| myrepo | 你fork的仓库 | 读写 |

## 工作流程图

```
┌─────────────────────────────────────────────────────┐
│                    原项目 (upstream)                 │
│              TraderAlice/Auto-Quant                  │
│                    ↑ 只读，同步                      │
├─────────────────────────────────────────────────────┤
│                    你的fork (myrepo)                 │
│                  你的用户名/Auto-Quant                │
│                    ↑ 可写，推送                      │
├─────────────────────────────────────────────────────┤
│                    本地仓库                          │
│              E:/demo/learn/aitrade/Auto-Quant        │
│                    ↑ 开发工作                        │
└─────────────────────────────────────────────────────┘
```

## 本项目当前状态

执行配置前：
```bash
$ git remote -v
origin  git@github.com:TraderAlice/Auto-Quant.git (fetch)
origin  git@github.com:TraderAlice/Auto-Quant.git (push)
```

执行配置后（示例，假设你的用户名是yourname）：
```bash
$ git remote -v
upstream  git@github.com:TraderAlice/Auto-Quant.git (fetch)
upstream  git@github.com:TraderAlice/Auto-Quant.git (push)
myrepo    git@github.com:yourname/Auto-Quant.git (fetch)
myrepo    git@github.com:yourname/Auto-Quant.git (push)
```

## 注意事项

1. **永远不要直接push到upstream**（除非你是项目维护者）
2. **定期同步upstream**以获取最新更新
3. **在功能分支上开发**，不要直接在main上工作
4. **fork后记得去GitHub仓库设置** → 可以更新分支列表等
