@echo off
chcp 65001 >nul
echo ========================================
echo   快速清理 - 删除明显的测试文件
echo ========================================
echo.

echo 删除测试脚本...
if exist "check_console.py" del /q "check_console.py" && echo ✓ check_console.py
if exist "check_full.py" del /q "check_full.py" && echo ✓ check_full.py
if exist "SchedulePage.vue" del /q "SchedulePage.vue" && echo ✓ SchedulePage.vue

echo.
echo 删除测试配置...
if exist "frontend\vitest.config.ts" del /q "frontend\vitest.config.ts" && echo ✓ vitest.config.ts

echo.
echo 删除日志文件...
if exist "backend\uvicorn.log" del /q "backend\uvicorn.log" && echo ✓ uvicorn.log
if exist "backend\uvicorn_err.log" del /q "backend\uvicorn_err.log" && echo ✓ uvicorn_err.log

echo.
echo 删除缓存目录...
if exist "backend\.pytest_cache" rmdir /s /q "backend\.pytest_cache" && echo ✓ .pytest_cache

echo.
echo ========================================
echo   快速清理完成！
echo ========================================
echo.
pause
