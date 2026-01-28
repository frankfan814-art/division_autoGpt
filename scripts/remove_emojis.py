"""
移除 Python 代码中的 emoji

使用方法:
    python scripts/remove_emojis.py
"""

import re
import os
from pathlib import Path

# 常见的 emoji 映射（保留含义但使用文字）
EMOJI_REPLACEMENTS = {
    '🔥': '',
    '🔄': '',
    '📝': '',
    '⚠️': '',
    '✅': '',
    '❌': '',
    '📊': '',
    '🤖': '',
    '✏️': '',
    '📈': '',
    '⏸️': '',
    '📦': '',
    '📄': '',
    '🎯': '',
    '🚀': '',
    '💡': '',
    '⏳': '',
    '🔍': '',
    '🎉': '',
    '📋': '',
    '🔧': '',
    '🚨': '',
    '✨': '',
    '🏗️': '',
    '📚': '',
    '🔑': '',
    '🌟': '',
    '💻': '',
    '⚡': '',
    '🎨': '',
    '🔮': '',
    '🎪': '',
    '🎭': '',
}

# Unicode emoji 范围
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)


def remove_emojis_from_file(file_path: Path, base_path: Path) -> int:
    """
    从文件中移除 emoji

    Args:
        file_path: 文件路径
        base_path: 基础路径（用于相对路径显示）

    Returns:
        int: 移除的 emoji 数量
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 移除 emoji
        content = EMOJI_PATTERN.sub('', content)

        # 清理多余的空格
        content = re.sub(r'  +', ' ', content)  # 多个空格变成一个
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # 多个空行变成两个

        removed_count = len(original_content) - len(content)

        if removed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            try:
                rel_path = file_path.relative_to(base_path)
            except ValueError:
                rel_path = file_path
            print(f"[OK] {rel_path}: 移除了 {removed_count} 个字符")

        return removed_count

    except Exception as e:
        try:
            rel_path = file_path.relative_to(base_path)
        except ValueError:
            rel_path = file_path
        print(f"[ERROR] {rel_path}: {e}")
        return 0


def main():
    """主函数"""
    # 查找所有 Python 文件
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_dir = project_root / "src" / "creative_autogpt"

    if not src_dir.exists():
        print(f"错误: 找不到 {src_dir} 目录")
        return

    total_removed = 0
    file_count = 0

    for py_file in src_dir.rglob("*.py"):
        removed = remove_emojis_from_file(py_file, project_root)
        total_removed += removed
        if removed > 0:
            file_count += 1

    print(f"\n总计: 从 {file_count} 个文件中移除了约 {total_removed} 个字符")


if __name__ == "__main__":
    main()
