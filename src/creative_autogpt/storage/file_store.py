"""
File Store - Manages file-based content storage

Handles export of novels to various formats (TXT, DOCX, PDF, etc.)
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from creative_autogpt.utils.config import get_settings


class ExportFormat(str, Enum):
    """Supported export formats"""

    TXT = "txt"
    JSON = "json"
    MARKDOWN = "md"


class FileStore:
    """
    File-based storage for novel exports

    Manages:
    - Export to various formats
    - Chapter file organization
    - Backup management
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize file store

        Args:
            base_path: Base directory for storage
        """
        settings = get_settings()
        self.base_path = Path(base_path or settings.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"FileStore initialized at {self.base_path}")

    def _get_session_path(self, session_id: str) -> Path:
        """Get path for a session"""
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path

    async def save_chapter(
        self,
        session_id: str,
        chapter_index: int,
        content: str,
        title: Optional[str] = None,
    ) -> Path:
        """
        Save a chapter to a file

        Args:
            session_id: The session ID
            chapter_index: Chapter index
            content: Chapter content
            title: Optional chapter title

        Returns:
            Path to saved file
        """
        session_path = self._get_session_path(session_id)

        if title:
            filename = f"{chapter_index:03d}_{title}.txt"
        else:
            filename = f"{chapter_index:03d}.txt"

        file_path = session_path / "chapters" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Saved chapter {chapter_index} to {file_path}")
        return file_path

    async def save_full_novel(
        self,
        session_id: str,
        title: str,
        chapters: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save complete novel as a single file

        Args:
            session_id: The session ID
            title: Novel title
            chapters: List of chapter data
            metadata: Optional metadata

        Returns:
            Path to saved file
        """
        session_path = self._get_session_path(session_id)
        file_path = session_path / f"{title}.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            # Title page
            f.write(f"{title}\n")
            f.write("=" * len(title) + "\n\n")

            if metadata:
                f.write(f"作者: {metadata.get('author', '未知')}\n")
                f.write(f"类型: {metadata.get('genre', '未知')}\n")
                f.write(f"创建时间: {metadata.get('created_at', '未知')}\n")
                f.write("\n" + "-" * 50 + "\n\n")

            # Chapters
            for chapter in chapters:
                chapter_index = chapter.get("chapter_index", 0)
                chapter_title = chapter.get("title", f"第{chapter_index}章")
                content = chapter.get("content", "")

                f.write(f"\n{chapter_title}\n")
                f.write("\n")
                f.write(content)
                f.write("\n\n")

        logger.info(f"Saved full novel to {file_path}")
        return file_path

    async def export_to_json(
        self,
        session_id: str,
        title: str,
        data: Dict[str, Any],
    ) -> Path:
        """
        Export session data as JSON

        Args:
            session_id: The session ID
            title: Novel title
            data: Session data to export

        Returns:
            Path to exported file
        """
        session_path = self._get_session_path(session_id)
        file_path = session_path / f"{title}.json"

        export_data = {
            "title": title,
            "exported_at": datetime.utcnow().isoformat(),
            **data,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported to JSON: {file_path}")
        return file_path

    async def export_to_markdown(
        self,
        session_id: str,
        title: str,
        chapters: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Export novel as Markdown

        Args:
            session_id: The session ID
            title: Novel title
            chapters: List of chapter data
            metadata: Optional metadata

        Returns:
            Path to exported file
        """
        session_path = self._get_session_path(session_id)
        file_path = session_path / f"{title}.md"

        with open(file_path, "w", encoding="utf-8") as f:
            # Title
            f.write(f"# {title}\n\n")

            if metadata:
                f.write("## 元信息\n\n")
                if metadata.get("author"):
                    f.write(f"- **作者**: {metadata['author']}\n")
                if metadata.get("genre"):
                    f.write(f"- **类型**: {metadata['genre']}\n")
                if metadata.get("description"):
                    f.write(f"- **简介**: {metadata['description']}\n")
                f.write("\n---\n\n")

            # Chapters
            for chapter in chapters:
                chapter_index = chapter.get("chapter_index", 0)
                chapter_title = chapter.get("title", f"第{chapter_index}章")
                content = chapter.get("content", "")

                f.write(f"\n## {chapter_title}\n\n")
                f.write(content)
                f.write("\n\n")

        logger.info(f"Exported to Markdown: {file_path}")
        return file_path

    async def export_full_creative_process(
        self,
        session_id: str,
        title: str,
        tasks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        导出完整的创作过程，包含所有任务的输出

        格式：
        - 创意脑暴
        - 大纲
        - 人物设计
        - 世界观规则
        - 主题确认
        - 风格元素
        - 市场定位
        - 事件设定
        - 场景物品冲突
        - 伏笔列表
        - 章节大纲 + 章节内容 (每章)

        Args:
            session_id: 会话ID
            title: 小说标题
            tasks: 所有任务结果列表
            metadata: 元数据

        Returns:
            导出文件路径
        """
        session_path = self._get_session_path(session_id)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        file_path = session_path / f"{title}_完整创作_{timestamp}.md"
        
        # 定义任务类型的顺序和标题
        task_order = [
            ("创意脑暴", "# 🎯 创意脑暴"),
            ("大纲", "# 📋 故事大纲"),
            ("人物设计", "# 👥 人物设计"),
            ("世界观规则", "# 🌍 世界观规则"),
            ("主题确认", "# 🎭 主题确认"),
            ("风格元素", "# ✨ 风格元素"),
            ("市场定位", "# 📊 市场定位"),
            ("事件", "# ⚡ 事件设定"),
            ("场景物品冲突", "# 🎬 场景物品冲突"),
            ("伏笔列表", "# 🔮 伏笔列表"),
            ("一致性检查", "# ✅ 一致性检查"),
        ]
        
        # 按任务类型整理结果
        task_results = {}
        chapter_outlines = {}  # 章节大纲
        chapter_contents = {}  # 章节内容
        
        for task in tasks:
            task_type = task.get("task_type", "")
            result = task.get("result", "")
            chapter_index = task.get("chapter_index")
            
            if task_type == "章节大纲" and chapter_index is not None:
                chapter_outlines[chapter_index] = result
            elif task_type in ("章节内容", "章节润色") and chapter_index is not None:
                # 如果已有内容且是润色后的，用润色后的替换
                if task_type == "章节润色" or chapter_index not in chapter_contents:
                    chapter_contents[chapter_index] = result
            elif task_type not in ("章节大纲", "章节内容", "章节润色", "场景生成"):
                if task_type not in task_results:
                    task_results[task_type] = result
        
        with open(file_path, "w", encoding="utf-8") as f:
            # 标题页
            f.write(f"# 📚 {title}\n\n")
            f.write(f"**导出时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")
            
            if metadata:
                f.write("## 📝 基本信息\n\n")
                if metadata.get("genre"):
                    f.write(f"- **类型**: {metadata['genre']}\n")
                if metadata.get("theme"):
                    f.write(f"- **主题**: {metadata['theme']}\n")
                if metadata.get("style"):
                    f.write(f"- **风格**: {metadata['style']}\n")
                if metadata.get("length"):
                    f.write(f"- **目标字数**: {metadata['length']}\n")
                f.write("\n---\n\n")
            
            # 按顺序输出准备阶段的任务结果
            f.write("# 第一部分：创作准备\n\n")
            f.write("> 以下是小说创作的准备工作，包含创意脑暴、人物设计、世界观构建等内容。\n\n")
            
            for task_type, section_title in task_order:
                if task_type in task_results and task_results[task_type]:
                    f.write(f"{section_title}\n\n")
                    f.write(task_results[task_type])
                    f.write("\n\n---\n\n")
            
            # 输出章节内容
            if chapter_contents:
                f.write("# 第二部分：正文内容\n\n")
                f.write("> 以下是小说的正文章节。\n\n")
                
                # 按章节顺序排序
                sorted_chapters = sorted(chapter_contents.keys())
                
                for chapter_index in sorted_chapters:
                    # 章节大纲（可选）
                    if chapter_index in chapter_outlines:
                        f.write(f"## 第{chapter_index}章 大纲\n\n")
                        f.write("```\n")
                        f.write(chapter_outlines[chapter_index])
                        f.write("\n```\n\n")
                    
                    # 章节内容
                    f.write(f"## 第{chapter_index}章\n\n")
                    f.write(chapter_contents[chapter_index])
                    f.write("\n\n---\n\n")
            
            # 统计信息
            f.write("# 📊 统计信息\n\n")
            total_words = sum(len(content) for content in chapter_contents.values())
            f.write(f"- **总章节数**: {len(chapter_contents)}\n")
            f.write(f"- **正文总字数**: 约{total_words}字\n")
            f.write(f"- **任务总数**: {len(tasks)}\n")
        
        logger.info(f"Exported full creative process to: {file_path}")
        return file_path

    async def load_chapter(
        self,
        session_id: str,
        chapter_index: int,
    ) -> Optional[str]:
        """
        Load a chapter from file

        Args:
            session_id: The session ID
            chapter_index: Chapter index

        Returns:
            Chapter content or None
        """
        session_path = self._get_session_path(session_id)
        chapter_dir = session_path / "chapters"

        # Try to find the chapter file
        for pattern in [f"{chapter_index:03d}.txt", f"{chapter_index:03d}_*.txt"]:
            matches = list(chapter_dir.glob(pattern))
            if matches:
                with open(matches[0], "r", encoding="utf-8") as f:
                    return f.read()

        return None

    async def list_sessions(self) -> List[str]:
        """
        List all session directories

        Returns:
            List of session IDs
        """
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]

    async def delete_session_files(self, session_id: str) -> bool:
        """
        Delete all files for a session

        Args:
            session_id: The session ID

        Returns:
            True if successful
        """
        session_path = self._get_session_path(session_id)

        try:
            # Remove all contents
            for item in session_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    for sub_item in item.iterdir():
                        sub_item.unlink()
                    item.rmdir()

            # Remove directory
            session_path.rmdir()

            logger.info(f"Deleted files for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session files: {e}")
            return False

    async def get_session_size(self, session_id: str) -> int:
        """
        Get total size of session files in bytes

        Args:
            session_id: The session ID

        Returns:
            Size in bytes
        """
        session_path = self._get_session_path(session_id)

        if not session_path.exists():
            return 0

        total_size = 0
        for item in session_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        return total_size
