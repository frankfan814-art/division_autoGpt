#!/usr/bin/env python3
"""
小说创作自我评估脚本

功能：
1. 读取 result/export.md 中的小说内容
2. 使用 Qwen 或 Doubao 进行顶级视角评估
3. 生成评估报告
4. 根据评估报告提出提示词优化建议
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class LLMProvider(Enum):
    """LLM 提供商"""
    QWEN = "qwen"
    DOUBAO = "doubao"


class NovelEvaluator:
    """小说自我评估器"""

    def __init__(self, provider: str = "qwen"):
        """
        初始化评估器

        Args:
            provider: 使用的 LLM 提供商 (qwen 或 doubao)
        """
        self.provider = provider
        self.base_url = self._get_base_url(provider)

    def _get_base_url(self, provider: str) -> str:
        """获取 API 基础 URL"""
        if provider == "qwen":
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"
        elif provider == "doubao":
            return "https://ark.cn-beijing.volces.com/api/v3"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _get_api_key(self, provider: str) -> str:
        """获取 API 密钥"""
        if provider == "qwen":
            return os.getenv("ALIYUN_API_KEY", "")
        elif provider == "doubao":
            return os.getenv("ARK_API_KEY", "")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _get_model(self, provider: str) -> str:
        """获取模型名称"""
        if provider == "qwen":
            return "qwen-max"
        elif provider == "doubao":
            return "ep-20250126164345-hdpgm"  # Doubao-pro
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def evaluate_novel(
        self,
        novel_path: str = "result/export.md",
        output_dir: str = "result/evaluations"
    ) -> dict:
        """
        评估小说质量

        Args:
            novel_path: 小说文件路径
            output_dir: 评估报告输出目录

        Returns:
            评估报告字典
        """
        console.print(Panel.fit("[bold cyan]🔍 小说自我评估系统[/bold cyan]\n顶级视角审视 · 发现问题 · 持续进化"))

        # 1. 读取小说内容
        console.print("[dim]📖 读取小说内容...[/dim]")
        novel_path = Path(novel_path)
        if not novel_path.exists():
            console.print(f"[red]❌ 小说文件不存在: {novel_path}[/red]")
            return {}

        with open(novel_path, 'r', encoding='utf-8') as f:
            novel_content = f.read()

        # 智能采样：如果内容太长，只评估关键部分
        content_length = len(novel_content)
        console.print(f"[dim]📏 小说内容长度: {content_length:,} 字符[/dim]")

        # Qwen API 限制输入长度为 30720 tokens
        # 中文约 1-2 字符/token，提示词模板约 1000 字符
        # 保守估计，限制内容在 15000 字符以内
        max_chars = 15000
        if content_length > max_chars:
            console.print(f"[yellow]⚠️  内容过长，将进行智能采样...[/yellow]")
            # 智能采样策略：取开头、中间和结尾
            quarter = content_length // 4
            novel_content = (
                novel_content[:5000] +  # 前 5000 字符（开篇）
                "\n\n... [部分内容省略] ...\n\n" +
                novel_content[quarter:quarter+5000] +  # 中间 5000 字符
                "\n\n... [部分内容省略] ...\n\n" +
                novel_content[-5000:]  # 最后 5000 字符（结尾）
            )
            console.print(f"[dim]✂️  采样后长度: {len(novel_content):,} 字符[/dim]")

        # 读取评估提示词
        prompt_path = Path(__file__).parent / "novel_evaluator_prompt.md"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # 2. 构建完整提示词
        console.print("[dim]📝 构建评估提示词...[/dim]")
        full_prompt = prompt_template.replace(
            "[在此处插入小说内容]",
            f"\n\n--- 小说内容开始 ---\n\n{novel_content}\n\n--- 小说内容结束 ---\n\n"
        )

        # 3. 调用 LLM 进行评估
        console.print(f"[dim]🤖 调用 {self.provider} 进行评估...[/dim]")
        console.print("[dim]这可能需要 1-2 分钟，请耐心等待...[/dim]")

        evaluation = await self._call_llm(full_prompt)

        # 4. 保存评估报告
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"evaluation_{timestamp}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(evaluation)

        console.print(f"[green]✅ 评估报告已保存: {report_path}[/green]")

        # 5. 解析评分
        scores = self._parse_scores(evaluation)

        # 6. 显示评分概览
        self._display_scores(scores)

        return {
            "report_path": str(report_path),
            "evaluation": evaluation,
            "scores": scores
        }

    async def _call_llm(self, prompt: str) -> str:
        """调用 LLM API"""
        api_key = self._get_api_key(self.provider)
        if not api_key:
            raise ValueError(f"API key not found for {self.provider}")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self._get_model(self.provider),
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位顶级的小说创作顾问和编辑，拥有20年科幻小说编辑经验。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # 降低温度以获得更稳定的评估
            "max_tokens": 8000
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )

            # 打印错误详情用于调试
            if response.status_code != 200:
                console.print(f"[red]❌ API 请求失败: {response.status_code}[/red]")
                try:
                    error_detail = response.json()
                    console.print(f"[red]错误详情: {error_detail}[/red]")
                except:
                    console.print(f"[red]错误详情: {response.text[:500]}[/red]")
                console.print(f"[dim]提示词长度: {len(prompt)} 字符[/dim]")

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

    def _parse_scores(self, evaluation: str) -> dict:
        """解析评估报告中的评分"""
        import re

        scores = {
            "核心创意": 0,
            "人物塑造": 0,
            "世界观设定": 0,
            "叙事结构": 0,
            "文字质量": 0
        }

        # 查找评分表格
        table_pattern = r'\|\s*([^|]+)\s*\|\s*(\d+(?:\.\d+)?)/10\s*\|\s*([^|]+)\s*\|'
        for match in re.finditer(table_pattern, evaluation):
            dimension = match.group(1).strip()
            score_str = match.group(2)
            comment = match.group(3).strip()

            if dimension in scores and score_str:
                try:
                    scores[dimension] = float(score_str)
                except ValueError:
                    pass

        return scores

    def _display_scores(self, scores: dict):
        """显示评分概览"""
        table = Table(title="📊 评分概览", show_header=True, header_style="bold magenta")
        table.add_column("维度", style="cyan", width=20)
        table.add_column("评分", justify="right", style="yellow")
        table.add_column("评级", style="green")
        table.add_column("简评", style="dim")

        def get_grade(score: float) -> str:
            """根据评分返回等级"""
            if score >= 9:
                return "🏆 卓越"
            elif score >= 8:
                return "✨ 优秀"
            elif score >= 7:
                return "👍 良好"
            elif score >= 6:
                return "😐 及格"
            else:
                return "⚠️ 需改进"

        for dimension, score in scores.items():
            grade = get_grade(score)

            table.add_row(
                dimension,
                f"{score:.1f}/10",
                grade,
                "见详细报告"
            )

        console.print("\n")
        console.print(table)

        # 计算平均分
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        console.print(f"\n[bold]综合评分: {avg_score:.1f}/10[/bold]")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="小说创作自我评估")
    parser.add_argument(
        "--provider",
        choices=["qwen", "doubao"],
        default="qwen",
        help="LLM 提供商 (默认: qwen)"
    )
    parser.add_argument(
        "--novel",
        default="result/export.md",
        help="小说文件路径"
    )
    parser.add_argument(
        "--output",
        default="result/evaluations",
        help="评估报告输出目录"
    )

    args = parser.parse_args()

    evaluator = NovelEvaluator(provider=args.provider)

    try:
        result = await evaluator.evaluate_novel(
            novel_path=args.novel,
            output_dir=args.output
        )

        console.print("\n[green]✨ 评估完成！[/green]")
        console.print(f"[dim]📄 详细报告: {result.get('report_path')}[/dim]")

    except Exception as e:
        console.print(f"\n[red]❌ 评估失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
