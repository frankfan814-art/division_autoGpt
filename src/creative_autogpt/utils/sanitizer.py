"""
Security utilities for input sanitization and safe parsing.

Provides safe JSON parsing, input validation, and output sanitization.
"""

import html
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from loguru import logger

# Default security limits
MAX_JSON_SIZE = 10_000_000  # 10 MB
MAX_JSON_DEPTH = 50
_MAX_DESCRIPTION_LENGTH = 5000
_MAX_DEPENDENCIES = 10


def safe_json_parse(
    json_str: str,
    max_depth: int = MAX_JSON_DEPTH,
    max_size: int = MAX_JSON_SIZE,
) -> Optional[Dict[str, Any]]:
    """
    安全地解析 JSON 字符串，防止深度嵌套攻击和大文件攻击

    Args:
        json_str: JSON 字符串
        max_depth: 最大嵌套深度，默认 50
        max_size: JSON 最大字节数，默认 10MB

    Returns:
        Python 字典或 None（如果解析失败）

    Examples:
        >>> safe_json_parse('{"name": "test"}')
        {'name': 'test'}
        >>> safe_json_parse('{"a":' + '{' * 100 + '}')  # 超过深度限制
        None
    """
    # 检查大小
    try:
        json_bytes = json_str.encode('utf-8')
        if len(json_bytes) > max_size:
            logger.warning(f"JSON 大小 {len(json_bytes)} 超过限制 {max_size}")
            return None
    except UnicodeEncodeError as e:
        logger.warning(f"JSON 编码错误: {e}")
        return None

    # 检查深度
    depth = 0
    max_local_depth = 0
    in_string = False
    escape_next = False

    for char in json_str:
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                depth += 1
                max_local_depth = max(max_local_depth, depth)
            elif char == '}':
                depth -= 1

    if max_local_depth > max_depth:
        logger.warning(f"JSON 深度 {max_local_depth} 超过限制 {max_depth}")
        return None

    # 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析错误: {e}")
        return None

    # 验证类型
    if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
        logger.warning(f"JSON 类型无效: {type(data)}")
        return None

    return data


def sanitize_for_log(data: Any, max_length: int = 1000) -> Any:
    """
    清理数据用于日志输出，移除控制字符和超长内容

    Args:
        data: 要清理的数据
        max_length: 字符串最大长度

    Returns:
        清理后的数据
    """
    if isinstance(data, str):
        # 移除控制字符
        data = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data)
        # 截断超长字符串
        if len(data) > max_length:
            data = data[:max_length] + "... (truncated)"
        return data
    elif isinstance(data, dict):
        return {k: sanitize_for_log(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_log(v, max_length) for v in data]
    else:
        return data


def sanitize_for_json(data: Any) -> Any:
    """
    清理数据使其可以序列化为 JSON

    Args:
        data: 要清理的数据

    Returns:
        可以 JSON 序列化的数据
    """
    try:
        json.dumps(data)
        return data
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON 序列化失败: {e}")
        # 尝试清理数据
        if isinstance(data, dict):
            return {
                k: sanitize_for_json(v)
                for k, v in data.items()
                if k.isalnum() and isinstance(k, str)
            }
        elif isinstance(data, list):
            return [sanitize_for_json(v) for v in data]
        else:
            return str(data)


def extract_json_blocks(text: str) -> List[str]:
    """
    从文本中提取 JSON 块

    支持格式：
    - ```json ... ```
    - ``` ... ```
    - { ... }

    Args:
        text: 输入文本

    Returns:
        JSON 字符串列表
    """
    json_blocks = []

    # 方式1: ```json ... ``` 代码块
    json_code_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    json_blocks.extend(json_code_blocks)

    # 方式2: ``` ... ``` 代码块
    code_blocks = re.findall(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
    json_blocks.extend(code_blocks)

    # 方式3: { ... } 直接匹配
    if not json_blocks:
        start = text.find("{")
        if start >= 0:
            brace_count = 0
            in_string = False
            escape_next = False
            for i in range(start, len(text)):
                char = text[i]
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_blocks.append(text[start:i+1])
                            break

    return json_blocks


def validate_task_definition(
    task_def: Dict[str, Any],
    allowed_task_types: Set[str],
    max_dependencies: int = _MAX_DEPENDENCIES,
    max_description_length: int = _MAX_DESCRIPTION_LENGTH,
) -> Tuple[bool, List[str], List[str]]:
    """
    验证任务定义的有效性

    Args:
        task_def: 任务定义字典
        allowed_task_types: 允许的任务类型集合
        max_dependencies: 最大依赖数
        max_description_length: 描述最大长度

    Returns:
        (是否有效, 错误列表, 警告列表)
    """
    errors = []
    warnings = []

    # 检查 task_type
    task_type_str = task_def.get("task_type")
    if not task_type_str:
        errors.append("缺少 task_type")
    elif task_type_str not in allowed_task_types:
        errors.append(f"无效的 task_type: {task_type_str}")

    # 检查依赖
    depends_on = task_def.get("depends_on", [])
    if not isinstance(depends_on, list):
        errors.append(f"depends_on 类型错误: {type(depends_on)}")
    elif len(depends_on) > max_dependencies:
        errors.append(f"依赖数过多: {len(depends_on)} > {max_dependencies}")

    # 检查依赖有效性
    if isinstance(depends_on, list):
        for dep in depends_on:
            if dep not in allowed_task_types:
                warnings.append(f"未知依赖类型: {dep}")

    # 检查描述
    description = task_def.get("description", "")
    if not isinstance(description, str):
        errors.append(f"description 类型错误: {type(description)}")
    elif len(description) > max_description_length:
        errors.append(
            f"description 过长: {len(description)} > {max_description_length}"
        )

    # 检查自依赖
    if task_type_str and isinstance(depends_on, list) and task_type_str in depends_on:
        errors.append(f"任务自依赖: {task_type_str}")

    # 检查 optional 类型
    if "optional" in task_def and not isinstance(task_def["optional"], bool):
        errors.append(f"optional 类型错误: {type(task_def['optional'])}")

    # 检查 can_parallel 类型
    if "can_parallel" in task_def and not isinstance(task_def["can_parallel"], bool):
        errors.append(
            f"can_parallel 类型错误: {type(task_def['can_parallel'])}"
        )

    # 检查 is_foundation 类型
    if "is_foundation" in task_def and not isinstance(task_def["is_foundation"], bool):
        errors.append(
            f"is_foundation 类型错误: {type(task_def['is_foundation'])}"
        )

    return len(errors) == 0, errors, warnings


def sanitize_html(text: str) -> str:
    """
    转义 HTML 特殊字符

    Args:
        text: 输入文本

    Returns:
        转义后的文本
    """
    return html.escape(text)


def validate_plugin_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证插件配置的有效性

    Args:
        config: 插件配置字典

    Returns:
        (是否有效, 错误列表)
    """
    errors = []

    # 检查配置大小
    if len(config) > 100:
        errors.append(f"配置过大: {len(config)} > 100")
        return False, errors

    # 检查键名
    for key in config.keys():
        if not isinstance(key, str):
            errors.append(f"键名非字符串: {key} (类型: {type(key)})")
        elif len(key) > 100:
            errors.append(f"键名过长: {key} (长度: {len(key)})")

    # 检查值类型
    allowed_types = (str, int, float, bool, list, dict, type(None))
    for key, value in config.items():
        if not isinstance(value, allowed_types):
            errors.append(
                f"值类型无效: {key} = {type(value)} (允许: {allowed_types})"
            )

    return len(errors) == 0, errors
