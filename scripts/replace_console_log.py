"""
替换前端代码中的 console.log 为 logger

使用方法:
    python scripts/replace_console_log.py
"""

import re
from pathlib import Path


def replace_console_in_file(file_path: Path, base_path: Path) -> int:
    """
    替换文件中的 console 调用

    Args:
        file_path: 文件路径
        base_path: 基础路径

    Returns:
        int: 替换的数量
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        replacement_count = 0

        # 检查是否已经导入了 logger
        has_logger_import = "import logger from" in content or "import { logger" in content

        # 如果没有导入 logger，需要在导入部分添加
        if not has_logger_import and ('console.' in content):
            # 找到最后的 import 语句
            import_matches = list(re.finditer(r"^import .+;$", content, re.MULTILINE))
            if import_matches:
                last_import = import_matches[-1]
                insert_pos = last_import.end()
                # 添加 logger 导入
                content = content[:insert_pos] + f"\nimport logger from '@/utils/logger';" + content[insert_pos:]
                replacement_count += 1

        # 替换规则
        replacements = [
            # console.log -> logger.debug
            (r'console\.log\(', 'logger.debug(', 'debug'),
            # console.warn -> logger.warn
            (r'console\.warn\(', 'logger.warn(', 'warn'),
            # console.error -> logger.error
            (r'console\.error\(', 'logger.error(', 'error'),
            # console.info -> logger.info
            (r'console\.info\(', 'logger.info(', 'info'),
        ]

        for pattern, replacement, level in replacements:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                replacement_count += len(matches)

        if replacement_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            try:
                rel_path = file_path.relative_to(base_path)
            except ValueError:
                rel_path = file_path
            print(f"[OK] {rel_path}: 替换了 {replacement_count} 处")

        return replacement_count

    except Exception as e:
        try:
            rel_path = file_path.relative_to(base_path)
        except ValueError:
            rel_path = file_path
        print(f"[ERROR] {rel_path}: {e}")
        return 0


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    frontend_src = project_root / "frontend" / "src"

    if not frontend_src.exists():
        print(f"错误: 找不到 {frontend_src} 目录")
        return

    total_replaced = 0
    file_count = 0

    # 只处理 .ts, .tsx 文件
    for file_path in frontend_src.rglob("*.ts"):
        replaced = replace_console_in_file(file_path, project_root)
        total_replaced += replaced
        if replaced > 0:
            file_count += 1

    for file_path in frontend_src.rglob("*.tsx"):
        replaced = replace_console_in_file(file_path, project_root)
        total_replaced += replaced
        if replaced > 0:
            file_count += 1

    print(f"\n总计: 从 {file_count} 个文件中替换了约 {total_replaced} 处 console 调用")


if __name__ == "__main__":
    main()
