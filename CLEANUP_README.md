# 项目清理指南

## 概述

本指南帮助你清理项目中不再需要的测试代码、临时文件和缓存文件。

## 清理内容

### 1. 测试代码
- `backend/tests/` - Python 后端测试目录
- `frontend/src/__tests__/` - Vue 前端测试目录
- `frontend/vitest.config.ts` - 测试配置文件
- `check_console.py` - 控制台检查脚本
- `check_full.py` - 完整检查脚本
- `SchedulePage.vue` - 空的测试文件

### 2. 临时文件
- `backend/.pytest_cache/` - pytest 缓存
- `backend/uvicorn.log` - 服务器日志
- `backend/uvicorn_err.log` - 错误日志
- `.superpowers/` - 临时数据目录

### 3. 缓存文件
- 所有 `__pycache__/` 目录 - Python 字节码缓存

## 清理方法

### 方法一：使用批处理脚本（推荐）

1. 双击运行 `cleanup.bat`
2. 等待脚本执行完成
3. 按任意键关闭窗口

### 方法二：使用 Python 脚本

```bash
python cleanup_project.py
```

### 方法三：手动清理

#### 删除测试目录
```bash
# Windows
rmdir /s /q backend\tests
rmdir /s /q frontend\src\__tests__

# Linux/macOS
rm -rf backend/tests
rm -rf frontend/src/__tests__
```

#### 删除测试文件
```bash
# Windows
del check_console.py
del check_full.py
del SchedulePage.vue
del frontend\vitest.config.ts

# Linux/macOS
rm check_console.py check_full.py SchedulePage.vue frontend/vitest.config.ts
```

#### 删除日志文件
```bash
# Windows
del backend\uvicorn.log
del backend\uvicorn_err.log

# Linux/macOS
rm backend/uvicorn.log backend/uvicorn_err.log
```

#### 删除缓存目录
```bash
# Windows
rmdir /s /q backend\.pytest_cache
for /d /r backend %%d in (__pycache__) do rmdir /s /q "%%d"

# Linux/macOS
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf backend/.pytest_cache
```

## 清理后操作

### 1. 更新 .gitignore

确保 `.gitignore` 包含以下内容：
```gitignore
# 测试相关
*.test.*
*.spec.*
__tests__/
tests/

# 日志文件
*.log

# 缓存目录
__pycache__/
.pytest_cache/
```

### 2. 提交清理

```bash
# 从 Git 中移除已删除的文件
git rm -r --cached backend/tests
git rm -r --cached frontend/src/__tests__
git rm --cached check_console.py check_full.py SchedulePage.vue
git rm --cached frontend/vitest.config.ts
git rm --cached backend/uvicorn.log backend/uvicorn_err.log

# 提交更改
git add .
git commit -m "chore: remove unused test code and temporary files"
```

## 注意事项

⚠️ **重要提示：**

1. **备份重要数据**：在运行清理脚本之前，请确保没有重要的测试数据需要保留。

2. **检查依赖**：删除测试文件后，请检查项目是否仍然可以正常运行。

3. **IDE 重启**：清理完成后，建议重启 IDE 以清除缓存。

4. **重新安装依赖**：如果删除了 `node_modules`，需要重新运行 `npm install`。

## 恢复文件

如果误删了重要文件，可以从 Git 恢复：

```bash
# 恢复特定文件
git checkout HEAD -- backend/tests
git checkout HEAD -- frontend/src/__tests__

# 恢复所有删除的文件
git checkout HEAD -- .
```

## 常见问题

### Q: 清理后项目无法运行怎么办？

A: 检查是否删除了必要的配置文件，并重新安装依赖：
```bash
cd frontend && npm install
cd ../backend && pip install -r requirements.txt
```

### Q: 如何只清理部分文件？

A: 手动删除不需要的文件，或修改清理脚本中的文件列表。

### Q: 清理脚本没有执行权限怎么办？

A: 
- Windows：右键点击 `.bat` 文件，选择"以管理员身份运行"
- Linux/macOS：`chmod +x cleanup_project.py && ./cleanup_project.py`

## 联系支持

如果遇到问题，请联系项目维护者。
