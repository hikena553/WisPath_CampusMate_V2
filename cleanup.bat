@echo off
chcp 65001 >nul
echo ========================================
echo   智慧校园AI服务平台 - 项目清理工具
echo ========================================
echo.

echo 正在清理项目文件...
echo.

REM 删除测试目录
echo 1. 删除测试目录...
if exist "backend\tests" (
    rmdir /s /q "backend\tests"
    echo    ✓ 已删除 backend\tests
)

if exist "frontend\src\__tests__" (
    rmdir /s /q "frontend\src\__tests__"
    echo    ✓ 已删除 frontend\src\__tests__
)

REM 删除测试脚本
echo.
echo 2. 删除测试脚本...
if exist "check_console.py" (
    del /q "check_console.py"
    echo    ✓ 已删除 check_console.py
)

if exist "check_full.py" (
    del /q "check_full.py"
    echo    ✓ 已删除 check_full.py
)

if exist "SchedulePage.vue" (
    del /q "SchedulePage.vue"
    echo    ✓ 已删除 SchedulePage.vue
)

REM 删除测试配置
if exist "frontend\vitest.config.ts" (
    del /q "frontend\vitest.config.ts"
    echo    ✓ 已删除 frontend\vitest.config.ts
)

REM 删除日志文件
echo.
echo 3. 删除日志文件...
if exist "backend\uvicorn.log" (
    del /q "backend\uvicorn.log"
    echo    ✓ 已删除 backend\uvicorn.log
)

if exist "backend\uvicorn_err.log" (
    del /q "backend\uvicorn_err.log"
    echo    ✓ 已删除 backend\uvicorn_err.log
)

REM 删除缓存目录
echo.
echo 4. 删除缓存目录...
if exist "backend\.pytest_cache" (
    rmdir /s /q "backend\.pytest_cache"
    echo    ✓ 已删除 backend\.pytest_cache
)

REM 删除 __pycache__ 目录
echo.
echo 5. 删除 __pycache__ 目录...
for /d /r backend %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo    ✓ 已删除 %%d
    )
)

REM 删除 .superpowers 目录
echo.
echo 6. 删除临时目录...
if exist ".superpowers" (
    rmdir /s /q ".superpowers"
    echo    ✓ 已删除 .superpowers
)

echo.
echo ========================================
echo   清理完成！
echo ========================================
echo.
echo 建议执行以下命令清理 Git 缓存：
echo   git rm -r --cached backend/tests
echo   git rm -r --cached frontend/src/__tests__
echo   git rm --cached check_console.py check_full.py SchedulePage.vue
echo.
pause
