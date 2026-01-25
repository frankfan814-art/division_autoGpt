"""
Prompt Manager - Manages prompt templates and style injection

Provides centralized prompt management with template system.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template
from loguru import logger

from creative_autogpt.utils.config import get_settings


class PromptManager:
    """
    Manages prompt templates and style injection

    Responsibilities:
    - Load and render prompt templates
    - Inject style configurations
    - Manage prompt versions
    - Cache rendered prompts
    """

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        styles_dir: Optional[str] = None,
    ):
        """
        Initialize prompt manager

        Args:
            templates_dir: Directory for template files
            styles_dir: Directory for style configuration files
        """
        settings = get_settings()

        # Set default directories
        if templates_dir is None:
            # Check if prompts directory exists in project root
            project_root = Path.cwd()
            templates_path = project_root / "prompts" / "tasks"
            if templates_path.exists():
                templates_dir = str(templates_path)
            else:
                templates_dir = str(Path(__file__).parent.parent / "prompts" / "tasks")

        if styles_dir is None:
            project_root = Path.cwd()
            styles_path = project_root / "prompts" / "styles"
            if styles_path.exists():
                styles_dir = str(styles_path)
            else:
                styles_dir = str(Path(__file__).parent.parent / "prompts" / "styles")

        self.templates_dir = Path(templates_dir)
        self.styles_dir = Path(styles_dir)

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Cache for templates and styles
        self._template_cache: Dict[str, Template] = {}
        self._style_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"PromptManager initialized (templates: {self.templates_dir}, "
            f"styles: {self.styles_dir})"
        )

    def get_template(self, name: str) -> Template:
        """
        Get a Jinja2 template by name

        Args:
            name: Template name (without extension)

        Returns:
            Jinja2 Template object
        """
        if name not in self._template_cache:
            try:
                template_path = f"{name}.jinja2"
                self._template_cache[name] = self.env.get_template(template_path)
                logger.debug(f"Loaded template: {name}")
            except Exception as e:
                logger.warning(f"Template '{name}' not found: {e}")
                # Return a simple template
                self._template_cache[name] = Template("{{ content }}")

        return self._template_cache[name]

    def render_template(
        self,
        name: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Render a template with context

        Args:
            name: Template name
            context: Template variables

        Returns:
            Rendered prompt
        """
        template = self.get_template(name)
        return template.render(**context)

    def load_style(self, name: str) -> Dict[str, Any]:
        """
        Load a style configuration

        Args:
            name: Style name (e.g., "xuanhuan", "wuxia")

        Returns:
            Style configuration dict
        """
        if name not in self._style_cache:
            style_path = self.styles_dir / f"{name}.yaml"

            if not style_path.exists():
                logger.warning(f"Style '{name}' not found at {style_path}")
                self._style_cache[name] = self._get_default_style()
                return self._style_cache[name]

            try:
                import yaml

                with open(style_path, "r", encoding="utf-8") as f:
                    self._style_cache[name] = yaml.safe_load(f)

                logger.debug(f"Loaded style: {name}")

            except Exception as e:
                logger.error(f"Failed to load style '{name}': {e}")
                self._style_cache[name] = self._get_default_style()

        return self._style_cache[name]

    def _get_default_style(self) -> Dict[str, Any]:
        """Get default style configuration"""
        return {
            "narrative_style": "第三人称全知视角",
            "language_style": "通俗流畅，生动形象",
            "pacing": "张弛有度",
            "tone": "积极向上",
            "key_elements": [],
            "avoid_elements": [],
        }

    def inject_style(
        self,
        prompt: str,
        style_name: str,
    ) -> str:
        """
        Inject style configuration into a prompt

        Args:
            prompt: Base prompt
            style_name: Style to inject

        Returns:
            Prompt with style information
        """
        style = self.load_style(style_name)

        style_section = "\n\n## 风格要求\n\n"

        if style.get("narrative_style"):
            style_section += f"- 叙事风格: {style['narrative_style']}\n"

        if style.get("language_style"):
            style_section += f"- 语言风格: {style['language_style']}\n"

        if style.get("pacing"):
            style_section += f"- 节奏: {style['pacing']}\n"

        if style.get("tone"):
            style_section += f"- 基调: {style['tone']}\n"

        if style.get("key_elements"):
            style_section += f"- 核心元素: {', '.join(style['key_elements'])}\n"

        if style.get("avoid_elements"):
            style_section += f"- 避免元素: {', '.join(style['avoid_elements'])}\n"

        return prompt + style_section

    def get_available_styles(self) -> List[str]:
        """Get list of available style names"""
        if not self.styles_dir.exists():
            return []

        return [
            f.stem for f in self.styles_dir.glob("*.yaml")
            if f.is_file()
        ]

    def get_available_templates(self) -> List[str]:
        """Get list of available template names"""
        if not self.templates_dir.exists():
            return []

        return [
            f.stem for f in self.templates_dir.glob("*.jinja2")
            if f.is_file()
        ]


class PromptEnhancer:
    """
    Intelligently enhances user input into detailed configuration

    Uses LLM to expand simple user input into comprehensive novel settings.
    """

    def __init__(self, llm_client=None):
        """
        Initialize prompt enhancer

        Args:
            llm_client: LLM client for enhancement
        """
        self.llm_client = llm_client
        logger.info("PromptEnhancer initialized")

    async def enhance(
        self,
        user_input: str,
        current_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enhance user input into detailed configuration

        Args:
            user_input: User's simple input (e.g., "写个玄幻小说")
            current_config: Current configuration to update

        Returns:
            Enhanced configuration
        """
        if not self.llm_client:
            # Return basic enhancement without LLM
            return self._basic_enhancement(user_input, current_config)

        prompt = self._build_enhancement_prompt(user_input, current_config)

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="大纲",  # Use Qwen for comprehensive planning
                temperature=0.7,
                max_tokens=2000,
            )

            return self._parse_enhancement_response(response.content)

        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return self._basic_enhancement(user_input, current_config)

    def _build_enhancement_prompt(
        self,
        user_input: str,
        current_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for enhancement"""
        current_section = ""
        if current_config:
            current_section = f"\n### 当前配置\n```json\n{json.dumps(current_config, ensure_ascii=False, indent=2)}\n```\n"

        return f"""## 任务: 智能提示词增强

请将用户的简单输入扩展为详细的小说创作配置。

### 用户输入
{user_input}
{current_section}
### 输出要求

请以JSON格式输出扩展后的配置:

```json
{{
  "title": "小说标题",
  "genre": "类型（玄幻/武侠/都市/科幻/悬疑）",
  "theme": "核心主题",
  "style": "风格元素",
  "target_length": "目标字数（如：100万字）",
  "target_audience": "目标读者",
  "main_plot": "主线剧情概述",
  "key_elements": ["核心元素1", "核心元素2"],
  "avoid_elements": ["避免元素1"],
  "suggestions": ["创作建议1", "创作建议2"]
}}
```

请确保:
1. 标题吸引人
2. 类型准确
3. 主题鲜明
4. 情节完整
5. 元素符合类型特点

直接输出JSON，不需要其他说明。
"""

    def _parse_enhancement_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM enhancement response"""
        try:
            # Extract JSON
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                config = json.loads(json_str)
                return config

        except Exception as e:
            logger.error(f"Failed to parse enhancement response: {e}")

        # Fallback to basic enhancement
        return self._basic_enhancement(response)

    def _basic_enhancement(
        self,
        user_input: str,
        current_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Basic enhancement without LLM"""
        config = current_config or {}

        # Try to extract genre from input
        genre_keywords = {
            "玄幻": "玄幻",
            "武侠": "武侠",
            "都市": "都市",
            "科幻": "科幻",
            "悬疑": "悬疑",
        }

        genre = "玄幻"  # Default
        for keyword, value in genre_keywords.items():
            if keyword in user_input:
                genre = value
                break

        config.update({
            "title": config.get("title") or f"{genre}小说",
            "genre": genre,
            "theme": config.get("theme") or user_input[:100],
            "style": config.get("style") or "标准网文风格",
            "target_length": config.get("target_length") or "100万字",
        })

        return config


class FeedbackTransformer:
    """
    Transforms user feedback into professional prompt modifications

    Converts casual user feedback into structured prompt improvements.
    """

    def __init__(self, llm_client=None):
        """
        Initialize feedback transformer

        Args:
            llm_client: LLM client for transformation
        """
        self.llm_client = llm_client
        logger.info("FeedbackTransformer initialized")

    async def transform(
        self,
        feedback: str,
        task_type: str,
        current_content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Transform user feedback into prompt modification

        Args:
            feedback: User's feedback
            task_type: Type of task
            current_content: Current content being modified
            context: Additional context

        Returns:
            Transformed prompt instruction
        """
        if not self.llm_client:
            return self._basic_transformation(feedback, current_content)

        prompt = self._build_transformation_prompt(
            feedback,
            task_type,
            current_content,
            context,
        )

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                task_type="修订",
                temperature=0.7,
                max_tokens=1000,
            )

            return response.content

        except Exception as e:
            logger.error(f"Feedback transformation failed: {e}")
            return self._basic_transformation(feedback, current_content)

    def _build_transformation_prompt(
        self,
        feedback: str,
        task_type: str,
        current_content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for feedback transformation"""
        context_section = ""
        if context:
            context_section = f"\n### 上下文\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```\n"

        return f"""## 任务: 反馈意见转换

请将用户的反馈意见转换为专业的修改指令。

### 任务类型
{task_type}

### 用户反馈
{feedback}
{context_section}
### 当前内容（前500字）
```
{current_content[:500]}
```

### 输出要求

请输出具体的修改指令，指导如何改进内容：

1. **问题识别**: 明确指出问题所在
2. **修改方向**: 具体的改进方向
3. **实施建议**: 可操作的修改建议

请以清晰的结构输出修改指令。
"""

    def _basic_transformation(
        self,
        feedback: str,
        current_content: str,
    ) -> str:
        """Basic feedback transformation without LLM"""
        return f"""请根据以下反馈意见改进内容：

## 反馈意见
{feedback}

## 修改要求
1. 保持原有结构和核心情节
2. 针对反馈意见进行修改
3. 确保修改后的内容与整体风格一致

请直接输出修改后的内容。
"""
