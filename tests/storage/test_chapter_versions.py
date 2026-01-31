"""
章节版本管理测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from creative_autogpt.storage.session import SessionStorage, ChapterVersionModel


class TestChapterVersionManagement:
    """章节版本管理测试"""

    @pytest.fixture
    async def storage(self):
        """创建存储实例"""
        storage = SessionStorage(":memory:")  # 使用内存数据库
        await storage.initialize()
        yield storage
        await storage.close()

    @pytest.fixture
    def sample_session_id(self, storage):
        """创建示例会话"""
        import asyncio
        session_id = asyncio.run(storage.create_session(
            title="测试会话",
            mode="novel",
            goal={"genre": "玄幻", "theme": "修仙"}
        ))
        return session_id

    @pytest.mark.asyncio
    async def test_create_chapter_version(self, storage, sample_session_id):
        """测试创建章节版本"""
        version_id = await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="这是第一章的内容",
            version_number=1,
            is_current=True,
            evaluation={"score": 0.8, "passed": True},
            created_by="auto",
            token_stats={"total_tokens": 1000, "cost": 0.01}
        )

        assert version_id is not None
        assert len(version_id) > 0

    @pytest.mark.asyncio
    async def test_get_chapter_versions(self, storage, sample_session_id):
        """测试获取章节版本列表"""
        # 创建多个版本
        await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="版本1",
            version_number=1,
            is_current=False,
            evaluation={"score": 0.6}
        )

        await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="版本2",
            version_number=2,
            is_current=True,
            evaluation={"score": 0.8}
        )

        # 获取版本列表
        versions = await storage.get_chapter_versions(sample_session_id, 1)

        assert len(versions) == 2
        assert versions[0]["version_number"] == 2  # 按版本号降序
        assert versions[1]["version_number"] == 1
        assert versions[0]["is_current"] is True

    @pytest.mark.asyncio
    async def test_restore_chapter_version(self, storage, sample_session_id):
        """测试恢复章节版本"""
        # 创建初始版本
        await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="原始内容",
            version_number=1,
            is_current=True,
            evaluation={"score": 0.6}
        )

        # 创建新版本
        version_id = await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="新内容",
            version_number=2,
            is_current=False,
            evaluation={"score": 0.8}
        )

        # 恢复到版本1
        success = await storage.restore_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            version_id=version_id
        )

        assert success is True

        # 验证当前版本
        current = await storage.get_current_chapter_version(sample_session_id, 1)
        assert current is not None
        assert current["content"] == "新内容"

    @pytest.mark.asyncio
    async def test_get_current_chapter_version(self, storage, sample_session_id):
        """测试获取当前章节版本"""
        # 创建版本
        await storage.create_chapter_version(
            session_id=sample_session_id,
            task_id="task_001",
            chapter_index=1,
            content="当前版本",
            version_number=1,
            is_current=True,
            evaluation={"score": 0.8}
        )

        # 获取当前版本
        current = await storage.get_current_chapter_version(sample_session_id, 1)

        assert current is not None
        assert current["version_number"] == 1
        assert current["content"] == "当前版本"

    @pytest.mark.asyncio
    async def test_update_task_version_count(self, storage, sample_session_id):
        """测试更新任务版本计数"""
        # 需要先创建任务结果
        await storage.save_task_result(
            session_id=sample_session_id,
            task_id="task_001",
            task_type="章节内容",
            status="completed",
            result="内容",
            task_metadata={"chapter_index": 1}
        )

        # 更新版本计数
        success = await storage.update_task_version_count("task_001", 3)
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
