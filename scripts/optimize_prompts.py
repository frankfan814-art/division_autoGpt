#!/usr/bin/env python3
"""
基于评估反馈改进提示词

功能：
1. 解析评估报告
2. 提取关键问题和改进建议
3. 生成具体的提示词改进方案
4. 输出改进后的提示词
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


class PromptOptimizer:
    """提示词优化器"""

    def __init__(self, evaluation_path: str):
        """
        初始化优化器

        Args:
            evaluation_path: 评估报告文件路径
        """
        self.evaluation_path = Path(evaluation_path)
        self.evaluation = self._load_evaluation()
        self.issues = self._extract_issues()

    def _load_evaluation(self) -> str:
        """加载评估报告"""
        if not self.evaluation_path.exists():
            raise FileNotFoundError(f"评估报告不存在: {self.evaluation_path}")

        with open(self.evaluation_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_issues(self) -> List[Dict]:
        """提取问题列表"""
        issues = []

        # 提取致命问题
        fatal_match = re.search(
            r'## 二、致命问题.*?(?=## 三、|$)',
            self.evaluation,
            re.DOTALL
        )
        if fatal_match:
            fatal_issues = self._parse_issues_section(fatal_match.group(), "fatal")
            issues.extend(fatal_issues)

        # 提取次要问题
        minor_match = re.search(
            r'## 三、次要问题.*?(?=## 四、|$)',
            self.evaluation,
            re.DOTALL
        )
        if minor_match:
            minor_issues = self._parse_issues_section(minor_match.group(), "minor")
            issues.extend(minor_issues)

        return issues

    def _parse_issues_section(self, section: str, severity: str) -> List[Dict]:
        """解析问题区块"""
        issues = []

        # 匹配问题块 - 支持多行内容
        problem_pattern = r'### 问题\d+：([^\n]+)\n(?:-\s*\*\*位置\*\*：([^\n]+)\n)?(?:-\s*\*\*问题描述\*\*：([^\n]+)\n)?(?:-\s*\*\*严重程度\*\*：([^\n]+)\n)?(?:-\s*\*\*修复建议\*\*：(.*?))(?=### 问题\d+|##|\Z)'

        for match in re.finditer(problem_pattern, section, re.DOTALL):
            # 清理多行文本
            fix_suggestion = match.group(5).strip() if match.group(5) else ""
            # 移除过多的换行符和空格
            fix_suggestion = re.sub(r'\s+', ' ', fix_suggestion)
            # 限制长度
            if len(fix_suggestion) > 500:
                fix_suggestion = fix_suggestion[:500] + "..."

            issues.append({
                "title": match.group(1).strip(),
                "location": match.group(2).strip() if match.group(2) else "未指定",
                "description": match.group(3).strip() if match.group(3) else "",
                "severity": severity,
                "fix_suggestion": fix_suggestion
            })

        return issues

    def generate_improvement_plan(self) -> Dict:
        """生成改进计划"""
        console.print(Panel.fit("[bold yellow]📋 生成改进计划[/bold yellow]"))

        plan = {
            "critical_fixes": [],
            "prompt_improvements": [],
            "workflow_changes": []
        }

        for issue in self.issues:
            if issue["severity"] == "fatal":
                plan["critical_fixes"].append({
                    "issue": issue["title"],
                    "suggestion": issue["fix_suggestion"]
                })

        # 提取提示词改进建议
        prompt_match = re.search(
            r'## 五、提示词改进建议.*$',
            self.evaluation,
            re.DOTALL
        )
        if prompt_match:
            prompt_section = prompt_match.group()

            # 提取需要优化的任务类型
            task_match = re.search(
                r'### 需要优化的任务类型(.*?)(?=### 提示词优化方向|$)',
                prompt_section,
                re.DOTALL
            )
            if task_match:
                task_text = task_match.group(1)
                for line in task_text.split('\n'):
                    if line.strip().startswith('1.') or line.strip().startswith('2.'):
                        plan["prompt_improvements"].append(line.strip())

            # 提取优化方向
            direction_match = re.search(
                r'### 提示词优化方向(.*?)(?=### 流程优化建议|$)',
                prompt_section,
                re.DOTALL
            )
            if direction_match:
                direction_text = direction_match.group(1)
                for line in direction_text.split('\n'):
                    if line.strip().startswith('-'):
                        plan["workflow_changes"].append(line.strip())

        return plan

    def display_issues(self):
        """显示问题列表"""
        console.print("\n[bold]🔍 发现的问题:[/bold]\n")

        if not self.issues:
            console.print("[green]✅ 未发现问题！[/green]")
            return

        for i, issue in enumerate(self.issues, 1):
            severity_icon = "🔴" if issue["severity"] == "fatal" else "🟡"
            console.print(f"{severity_icon} [bold]问题 {i}: {issue['title']}[/bold]")
            console.print(f"   [dim]位置: {issue['location']}[/dim]")
            console.print(f"   [dim]描述: {issue['description'][:100]}...[/dim]")
            console.print(f"   [cyan]建议: {issue['fix_suggestion'][:100]}...[/cyan]\n")

    def save_improvement_plan(self, output_path: str = "result/improvement_plan.json"):
        """保存改进计划"""
        plan = self.generate_improvement_plan()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        console.print(f"[green]✅ 改进计划已保存: {output_path}[/green]")

        return plan


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="基于评估反馈改进提示词")
    parser.add_argument(
        "evaluation",
        help="评估报告文件路径"
    )
    parser.add_argument(
        "--output",
        default="result/improvement_plan.json",
        help="改进计划输出路径"
    )

    args = parser.parse_args()

    try:
        optimizer = PromptOptimizer(args.evaluation)

        # 显示问题
        optimizer.display_issues()

        # 生成并保存改进计划
        plan = optimizer.save_improvement_plan(args.output)

        console.print("\n[green]✨ 改进计划生成完成！[/green]")
        console.print(f"[dim]📄 计划文件: {args.output}[/dim]")

    except Exception as e:
        console.print(f"\n[red]❌ 生成失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
