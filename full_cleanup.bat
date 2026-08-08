@echo off
chcp 65001 >nul
echo ========================================
echo   完整清理 - 删除所有测试和临时文件
echo ========================================
echo.
echo ⚠️  警告：这将删除所有测试代码和临时文件！
echo.
set /p confirm="确认执行完整清理？(y/N): "
if /i not "%confirm%"=="y" (
    echo 已取消清理
    pause
    exit /b
)

echo.
echo 开始完整清理...

REM 删除测试目录
echo.
echo 1. 删除测试目录...
if exist "backend\tests" (
    rmdir /s /q "backend\tests"
    echo    ✓ 已删除 backend\tests
) else (
    echo    - backend\tests 不存在，跳过
)

if exist "frontend\src\__tests__" (
    rmdir /s /q "frontend\src\__tests__"
    echo    ✓ 已删除 frontend\src\__tests__
) else (
    echo    - frontend\src\__tests__ 不存在，跳过
)

REM 删除测试文件
echo.
echo 2. 删除测试文件...
if exist "check_console.py" del /q "check_console.py" && echo    ✓ check_console.py
if exist "check_full.py" del /q "check_full.py" && echo    ✓ check_full.py
if exist "SchedulePage.vue" del /q "SchedulePage.vue" && echo    ✓ SchedulePage.vue
if exist "frontend\vitest.config.ts" del /q "frontend\vitest.config.ts" && echo    ✓ vitest.config.ts

REM 删除日志文件
echo.
echo 3. 删除日志文件...
if exist "backend\uvicorn.log" del /q "backend\uvicorn.log" && echo    ✓ uvicorn.log
if exist "backend\uvicorn_err.log" del /q "backend\uvicorn_err.log" && echo    ✓ uvicorn_err.log

REM 删除缓存目录
echo.
echo 4. 删除缓存目录...
if exist "backend\.pytest_cache" rmdir /s /q "backend\.pytest_cache" && echo    ✓ .pytest_cache

REM 删除 __pycache__ 目录
echo.
echo 5. 删除 __pycache__ 目录...
for /d /r backend %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo    ✓ 已删除 %%d
    )
)

REM 删除临时目录
echo.
echo 6. 删除临时目录...
if exist ".superpowers" (
    rmdir /s /q ".superpowers"
    echo    ✓ 已删除 .superpowers
) else (
    echo    - .superpowers 不存在，跳过
)

echo.
echo ========================================
echo   完整清理完成！
echo ========================================
echo.
echo 建议执行以下 Git 命令：
echo   git add .
echo   git commit -m "chore: remove unused test code and temporary files"
echo.
pause
