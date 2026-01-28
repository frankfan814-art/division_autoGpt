"""
章节衔接模块

确保章节之间的连贯性，提供开头/结尾框架
"""

from typing import Dict, Any, Optional
from loguru import logger


class ChapterContinuityManager:
    """
    章节连贯性管理器

    职责：
    1. 生成章节开头的衔接框架
    2. 生成章节结尾的悬念框架
    3. 确保与前后章节的连贯性
    """

    def __init__(self, llm_client):
        """
        初始化连贯性管理器

        Args:
            llm_client: LLM 客户端，用于生成衔接内容
        """
        self.llm_client = llm_client

    async def generate_continuity_framework(
        self,
        chapter_index: int,
        previous_chapter_ending: Optional[str],
        chapter_outline: str,
        context: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        生成章节衔接框架

        Args:
            chapter_index: 当前章节编号
            previous_chapter_ending: 上一章的结尾内容
            chapter_outline: 当前章节的大纲
            context: 创作上下文

        Returns:
            dict: {
                "opening_framework": "开头框架（150-200字）",
                "opening_instructions": "开头创作指导",
                "closing_hook_template": "结尾悬念模板",
                "closing_instructions": "结尾创作指导"
            }
        """

        # 第一章不需要衔接
        if chapter_index == 1 or not previous_chapter_ending:
            return self._generate_first_chapter_framework(chapter_outline)

        # 第2章及以后需要衔接上一章
        return await self._generate_continuation_framework(
            chapter_index,
            previous_chapter_ending,
            chapter_outline,
            context
        )

    def _generate_first_chapter_framework(self, chapter_outline: str) -> Dict[str, str]:
        """
        生成第一章的框架（不需要衔接）

        Args:
            chapter_outline: 第一章大纲

        Returns:
            第一章框架
        """
        return {
            "opening_framework": "",  # 第一章不需要开头框架，完全由LLM创作
            "opening_instructions": """
这是第一章，需要：
1. 吸引人的开场（100-150字）
2. 引入主角
3. 建立世界观基调
4. 制造初始悬念

建议开场方式：
- 从主角的日常/困境开始
- 从一个突发事件开始
- 从一个悬念场景开始
            """,
            "closing_hook_template": "",
            "closing_instructions": """
第一章结尾需要：
1. 引出故事的核心冲突
2. 让读者想知道接下来会发生什么
3. 可以暗示后续情节

结尾悬念示例：
- 主角面临一个重大选择
- 一个神秘人物出现
- 发现一个关键秘密
- 突然遇到危险
            """
        }

    async def _generate_continuation_framework(
        self,
        chapter_index: int,
        previous_ending: str,
        chapter_outline: str,
        context: Dict[str, Any],
    ) -> Dict[str, str]:
        """
        生成续章的衔接框架

        Args:
            chapter_index: 章节编号
            previous_ending: 上一章结尾
            chapter_outline: 当前章大纲
            context: 上下文

        Returns:
            衔接框架
        """

        # 分析上一章结尾的类型（悬念/动作/情绪/对话）
        ending_type = self._analyze_ending_type(previous_ending)

        # 根据结尾类型生成对应的衔接框架
        opening_framework = await self._generate_opening_framework(
            chapter_index,
            previous_ending,
            ending_type,
            chapter_outline
        )

        closing_hook = self._generate_closing_hook_template(chapter_outline)

        return {
            "opening_framework": opening_framework,
            "opening_instructions": f"""
**这是第{chapter_index}章，必须自然衔接上一章！**

上一章结尾类型：{ending_type}

衔接要求：
1. 开头150-200字，从上一章结尾自然过渡到本章场景
2. 人物状态、位置、情绪要延续上一章
3. 如果有时间/空间跳跃，用过渡语句交代
4. 不要让读者感觉"这是什么？怎么突然就..."

衔接方式参考：
- 场景直接衔接：继续上一章的动作
- 时间跳跃衔接："X小时后..."，"第二天..."
- 情绪延续衔接：延续上一章的情绪状态
- 悬念延续衔接：承接上一章的悬念，立即展开

请基于上面的"开头框架"，将其扩充为完整的开头。
            """,
            "closing_hook_template": closing_hook,
            "closing_instructions": """
本章结尾需要设置悬念，让读者想读下一章：

悬念类型：
- 行动悬念：主角即将采取某个行动
- 发现悬念：发现某个重要线索
- 危机悬念：突然遇到危险
- 情感悬念：人物关系的转折
- 未解悬念：提出新的问题

结尾钩子示例：
- "就在这时，[某事发生]"
- "他/她没有注意到，[某事正在发生]"
- "一个念头闪过：[新的疑问]"
            """
        }

    def _analyze_ending_type(self, ending: str) -> str:
        """
        分析上一章结尾的类型

        Args:
            ending: 上一章结尾内容（最后500字）

        Returns:
            结尾类型：悬念/动作/情绪/对话/情节转折
        """
        ending_lower = ending.lower()

        # 检测结尾类型
        if any(keyword in ending for keyword in ["？", "？", "想知道", "秘密", "真相", "为什么"]):
            return "悬念型（提出问题或谜团）"

        if any(keyword in ending for keyword in ["跳", "冲", "跑", "击", "杀", "逃", "战"]):
            return "动作型（动作正在进行或刚完成）"

        if any(keyword in ending for keyword in ["泪", "痛", "难过", "激动", "愤怒", "绝望", "希望"]):
            return "情绪型（强烈情感表达）"

        if "\"" in ending or '"' in ending or "说" in ending:
            return "对话型（对话结尾）"

        return "情节型（情节推进或转折）"

    async def _generate_opening_framework(
        self,
        chapter_index: int,
        previous_ending: str,
        ending_type: str,
        chapter_outline: str,
    ) -> str:
        """
        生成开头衔接框架

        Args:
            chapter_index: 章节编号
            previous_ending: 上一章结尾
            ending_type: 结尾类型
            chapter_outline: 本章大纲

        Returns:
            开头框架模板
        """

        # 提取上一章结尾的最后几句（用于分析衔接点）
        ending_sentences = previous_ending.split('。')[-3:]
        ending_context = '。'.join(ending_sentences).strip()

        # 根据结尾类型生成不同的衔接框架
        frameworks = {
            "悬念型（提出问题或谜团）": f"""
上一章结尾：
...{ending_context[:100]}...

**本章开头衔接框架**：
[承接上一章的悬念场景]
主角[带着疑问/为了寻找答案]，[过渡到本章场景]...
这个[谜团/问题]一直萦绕在他心头...
            """,

            "动作型（动作正在进行或刚完成）": f"""
上一章结尾：
...{ending_context[:100]}...

**本章开头衔接框架**：
[直接从动作的后果开始]
风/光/声音[描述环境变化]，主角[感觉/看到/听到]...
[描述动作结束后的状态]，[过渡到本章场景]...
            """,

            "情绪型（强烈情感表达）": f"""
上一章结尾：
...{ending_context[:100]}...

**本章开头衔接框架**：
[从情绪延续开始]
那句话/那种感觉[像什么一样]，深深烙在主角心里...
[X时间单位]过去了，主角[现在的状态]...
[从情绪过渡到当前场景]...
            """,

            "对话型（对话结尾）": f"""
上一章结尾：
...{ending_context[:100]}...

**本章开头衔接框架**：
[从对话的余韵开始]
声音还在回荡，但[主角]已经[做出反应/离开]...
[描述对话后的场景变化]，[过渡到本章场景]...
            """,

            "情节型（情节推进或转折）": f"""
上一章结尾：
...{ending_context[:100]}...

**本章开头衔接框架**：
[从情节的自然延续开始]
[承接上一章的情节]...
[描述场景/时间/状态的变化]，[过渡到本章场景]...
            """
        }

        return frameworks.get(ending_type, frameworks["情节型（情节推进或转折）"])

    def _generate_closing_hook_template(self, chapter_outline: str) -> str:
        """
        生成结尾悬念模板

        Args:
            chapter_outline: 本章大纲

        Returns:
            结尾悬念模板
        """
        return """
**本章结尾悬念模板**：

请根据本章情节，在结尾处设置一个悬念钩子。

推荐的悬念类型：
1. **行动悬念**："就在这时，[人物/事件]..."
2. **发现悬念**："他突然注意到，[细节]..."
3. **危机悬念**："警告来得太晚了，[危险]..."
4. **疑问悬念**："一个念头闪过：[问题]？"
5. **转折悬念**："但他没有注意到，[正在发生的事]..."

悬念长度：1-3句话，50-100字
        """

    async def validate_continuity(
        self,
        chapter_index: int,
        chapter_content: str,
        previous_ending: Optional[str],
    ) -> Dict[str, Any]:
        """
        验证章节衔接质量

        Args:
            chapter_index: 章节编号
            chapter_content: 章节内容
            previous_ending: 上一章结尾

        Returns:
            dict: {
                "passed": bool,
                "issues": list,
                "score": float
            }
        """

        # 第一章不需要验证衔接
        if chapter_index == 1 or not previous_ending:
            return {"passed": True, "issues": [], "score": 1.0}

        # 提取本章开头（前300字）
        opening = chapter_content[:300] if len(chapter_content) > 300 else chapter_content

        issues = []
        score = 1.0

        # 检查1：开头是否有明显的衔接尝试
        衔接关键词 = ["但是", "然而", "随后", "接着", "过了一会", "第二天", "几天后",
                      "那时", "此时", "回到", "继续", "仍然", "依然"]

        has_continuity_keywords = any(kw in opening for kw in 衔接关键词)

        if not has_continuity_keywords:
            # 检查是否直接从人物/动作开始（说明是直接衔接）
            if not any(name in opening for name in ["他", "她", "主角", "我"]):
                issues.append("开头缺少衔接元素，读者可能不知道与上一章的关系")
                score -= 0.3

        # 检查2：开头是否与上一章结尾的场景/情绪相关
        # （这个需要更复杂的NLP分析，暂时简化处理）

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "score": max(0.0, score)
        }
