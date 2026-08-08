#!/usr/bin/env python3
"""
项目清理脚本 - 删除不用的测试代码和临时文件
"""

import os
import shutil
import sys
from pathlib import Path


def remove_directory(path):
    """安全删除目录"""
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            print(f"✓ 已删除目录: {path}")
            return True
        except Exception as e:
            print(f"✗ 删除目录失败 {path}: {e}")
            return False
    return False


def remove_file(path):
    """安全删除文件"""
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"✓ 已删除文件: {path}")
            return True
        except Exception as e:
            print(f"✗ 删除文件失败 {path}: {e}")
            return False
    return False


def cleanup_project():
    """清理项目"""
    print("=" * 60)
    print("  智慧校园AI服务平台 - 项目清理工具")
    print("=" * 60)

    # 获取项目根目录
    root_dir = Path(__file__).parent.absolute()

    # 要删除的目录
    directories_to_remove = [
        # 测试目录
        root_dir / "backend" / "tests",
        root_dir / "frontend" / "src" / "__tests__",

        # 缓存目录
        root_dir / "backend" / ".pytest_cache",
        root_dir / "backend" / "__pycache__",

        # 日志文件目录（保留目录结构，只删文件）
        # root_dir / "backend" / "logs",

        # 临时目录
        root_dir / ".superpowers",

        # 上传目录（可选，可能有重要数据）
        # root_dir / "backend" / "uploads",
    ]

    # 要删除的文件
    files_to_remove = [
        # 测试脚本
        root_dir / "check_console.py",
        root_dir / "check_full.py",

        # 空文件
        root_dir / "SchedulePage.vue",

        # 测试配置
        root_dir / "frontend" / "vitest.config.ts",

        # 日志文件
        root_dir / "backend" / "uvicorn.log",
        root_dir / "backend" / "uvicorn_err.log",
    ]

    # 要清理的 __pycache__ 目录
    pycache_dirs = [
        root_dir / "backend" / "alembic" / "versions" / "__pycache__",
        root_dir / "backend" / "alembic" / "__pycache__",
        root_dir / "backend" / "app" / "api" / "__pycache__",
        root_dir / "backend" / "app" / "core" / "__pycache__",
        root_dir / "backend" / "app" / "models" / "__pycache__",
        root_dir / "backend" / "app" / "schemas" / "__pycache__",
        root_dir / "backend" / "app" / "services" / "__pycache__",
        root_dir / "backend" / "app" / "utils" / "__pycache__",
        root_dir / "backend" / "app" / "__pycache__",
    ]

    print("\n准备清理以下内容：")
    print("\n1. 测试目录：")
    for d in directories_to_remove[:2]:
        if d.exists():
            print(f"   - {d.relative_to(root_dir)}")
        else:
            print(f"   - {d.relative_to(root_dir)} (不存在)")

    print("\n2. 缓存目录：")
    for d in directories_to_remove[2:]:
        if d.exists():
            print(f"   - {d.relative_to(root_dir)}")
        else:
            print(f"   - {d.relative_to(root_dir)} (不存在)")

    print("\n3. 文件：")
    for f in files_to_remove:
        if f.exists():
            print(f"   - {f.relative_to(root_dir)}")
        else:
            print(f"   - {f.relative_to(root_dir)} (不存在)")

    print("\n4. __pycache__ 目录：")
    for d in pycache_dirs:
        if d.exists():
            print(f"   - {d.relative_to(root_dir)}")

    print("\n" + "=" * 60)
    confirm = input("确认删除以上内容？(y/N): ").strip().lower()

    if confirm != 'y':
        print("已取消清理操作")
        return

    print("\n开始清理...")

    # 删除目录
    for d in directories_to_remove:
        remove_directory(d)

    # 删除文件
    for f in files_to_remove:
        remove_file(f)

    # 删除 __pycache__ 目录
    for d in pycache_dirs:
        remove_directory(d)

    # 清理其他 __pycache__ 目录
    for pycache in root_dir.rglob("__pycache__"):
        remove_directory(pycache)

    print("\n" + "=" * 60)
    print("  清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    cleanup_project()
