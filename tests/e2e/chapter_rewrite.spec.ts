/**
 * Chapter Rewrite E2E Test
 *
 * 端到端测试：完整的章节重写流程
 */

import { test, expect } from '@playwright/test';

test.describe('章节重写流程', () => {
  test.beforeEach(async ({ page }) => {
    // 导航到首页
    await page.goto('/');

    // 确保有测试会话可用
    // 在实际测试中，这里可能需要先创建测试会话
  });

  test('完整重写流程', async ({ page }) => {
    // 1. 打开会话列表
    await page.click('text=查看会话列表');

    // 2. 选择一个会话
    await page.click('.session-card >> nth=0');

    // 3. 进入章节列表
    await page.click('text=章节列表');

    // 4. 选择一个章节
    await page.click('[data-testid="chapter-card"] >> nth=0');

    // 5. 点击重写按钮
    await page.click('text=重写章节');

    // 6. 填写重写原因
    await page.fill('[data-testid="rewrite-reason"]', '测试重写功能');

    // 7. 确认重写
    await page.click('text=开始重写');

    // 8. 等待重写完成
    await page.waitForSelector('[data-testid="rewrite-complete"]', { timeout: 300000 });

    // 9. 验证新版本已创建
    const versionCount = await page.locator('[data-testid="version-item"]').count();
    expect(versionCount).toBeGreaterThan(1);

    // 10. 验证版本历史显示
    await page.click('text=版本历史');
    await expect(page.locator('[data-testid="version-item"]')).toHaveCount(versionCount);
  });

  test('版本恢复流程', async ({ page }) => {
    // 1. 导航到章节详情页
    await page.goto(`/dashboard/test-session/chapters/1`);

    // 2. 查看版本历史
    await page.click('text=版本历史');

    // 3. 选择一个历史版本
    await page.click('[data-testid="version-item"] >> nth=1');

    // 4. 点击恢复
    await page.click('text=恢复此版本');

    // 5. 确认恢复
    await page.click('text=确定');

    // 6. 验证恢复成功提示
    await expect(page.locator('text=版本已恢复')).toBeVisible();
  });

  test('Dashboard 统计信息', async ({ page }) => {
    // 1. 打开 Dashboard
    await page.goto('/dashboard/test-session');

    // 2. 验证统计卡片显示
    await expect(page.locator('text=总章节数')).toBeVisible();
    await expect(page.locator('text=版本总数')).toBeVisible();
    await expect(page.locator('text=优秀章节')).toBeVisible();
    await expect(page.locator('text=待改进')).toBeVisible();

    // 3. 验证质量概览
    await expect(page.locator('text=质量概览')).toBeVisible();
  });

  test('章节筛选和排序', async ({ page }) => {
    // 1. 打开章节列表
    await page.goto('/dashboard/test-session/chapters');

    // 2. 测试筛选功能
    await page.click('text=待改进');
    await expect(page.locator('[data-testid="chapter-card"]')).toBeVisible();

    // 3. 测试排序功能
    await page.selectOption('select', 'quality');
    const firstChapter = await page.locator('[data-testid="chapter-card"] >> nth=0').textContent();
    await expect(firstChapter).toContain('第'); // 确保排序后仍有内容
  });
});

test.describe('API 集成测试', () => {
  test('重写 API 调用', async ({ request }) => {
    // 直接测试 API 端点
    const response = await request.post('/api/chapters/test-session/rewrite', {
      params: {
        chapter_index: 1,
        reason: 'API 测试',
        max_retries: 1,
      },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.chapter_index).toBe(1);
  });

  test('版本历史 API 调用', async ({ request }) => {
    const response = await request.get('/api/chapters/test-session/chapters/1/versions');

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.versions).toBeInstanceOf(Array);
  });

  test('版本恢复 API 调用', async ({ request }) => {
    // 首先获取版本列表
    const listResponse = await request.get('/api/chapters/test-session/chapters/1/versions');
    const listData = await listResponse.json();

    if (listData.versions.length > 1) {
      const versionId = listData.versions[1].id;

      // 恢复到第一个版本
      const restoreResponse = await request.post(
        `/api/chapters/test-session/chapters/1/versions/${versionId}/restore`
      );

      expect(restoreResponse.ok()).toBeTruthy();
      const restoreData = await restoreResponse.json();
      expect(restoreData.success).toBe(true);
    }
  });
});
