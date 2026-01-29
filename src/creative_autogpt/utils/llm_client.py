"""
Multi-LLM Client with intelligent routing and fallback support

Supports Aliyun (Qwen), DeepSeek, Ark (Doubao), and NVIDIA providers.
Implements task-type-based routing for optimal LLM selection.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from creative_autogpt.utils.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    ALIYUN = "aliyun"  # Qwen
    DEEPSEEK = "deepseek"
    ARK = "ark"  # Doubao
    NVIDIA = "nvidia"


@dataclass
class LLMUsage:
    """Token usage information"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """Response from LLM generation"""

    content: str
    model: str
    provider: LLMProvider
    usage: LLMUsage
    raw_response: Optional[Dict[str, Any]] = None
    cached: bool = False
    generation_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider.value,
            "usage": self.usage.to_dict(),
            "cached": self.cached,
            "generation_time": self.generation_time,
        }


@dataclass
class LLMMessage:
    """Chat message"""

    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class LLMClientBase(ABC):
    """Base class for LLM clients"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        # Create async OpenAI client (works with OpenAI-compatible APIs)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Return the provider type"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text from the LLM

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            messages: Optional list of messages for chat completion
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content and metadata
        """
        pass

    async def _generate_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> Tuple[str, LLMUsage, Dict[str, Any]]:
        """Internal method with enhanced retry logic and exponential backoff"""

        last_error = None
        # 增加重试次数到 5 次
        max_retries = max(self.max_retries, 5)
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"LLM request attempt {attempt + 1}/{max_retries} for {self.provider.value}")
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                content = response.choices[0].message.content or ""

                usage = LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0,
                )

                raw = response.model_dump() if hasattr(response, "model_dump") else {}
                
                logger.debug(f"LLM request successful on attempt {attempt + 1}")
                return content, usage, raw

            except RateLimitError as e:
                last_error = e
                wait_time = min(2 ** attempt * 2, 60)  # 指数退避，最多等60秒
                logger.warning(
                    f"Rate limit hit for {self.provider.value}, "
                    f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                )
                await asyncio.sleep(wait_time)

            except (APIConnectionError, APIError) as e:
                last_error = e
                wait_time = min(2 ** attempt * 2, 30)  # 指数退避
                logger.warning(
                    f"API error for {self.provider.value}: {e}, "
                    f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    
            except asyncio.TimeoutError as e:
                last_error = e
                wait_time = min(2 ** attempt * 3, 45)  # 超时用更长的退避时间
                logger.warning(
                    f"⏰ Timeout for {self.provider.value}, "
                    f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                # Catch any other errors (including httpx timeout)
                last_error = e
                error_str = str(e).lower()
                if "timeout" in error_str or "timed out" in error_str or "read timed out" in error_str:
                    wait_time = min(2 ** attempt * 3, 45)  # 超时用更长的退避时间
                    logger.warning(
                        f"⏰ Request timeout for {self.provider.value}: {e}, "
                        f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                elif "connection" in error_str:
                    wait_time = min(2 ** attempt * 2, 30)
                    logger.warning(
                        f"🔌 Connection error for {self.provider.value}: {e}, "
                        f"waiting {wait_time}s before retry {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                else:
                    # Unknown error, re-raise immediately
                    logger.error(f"Unknown error for {self.provider.value}: {e}")
                    raise

        # All retries failed
        logger.error(f"❌ All {max_retries} retries failed for {self.provider.value}: {last_error}")
        raise Exception(
            f"All {max_retries} retries failed for {self.provider.value}: {last_error}"
        )


class AliyunLLMClient(LLMClientBase):
    """Aliyun (Qwen) LLM client - optimized for long context and planning"""

    def __init__(self, api_key: str, base_url: str, model: str = "qwen-long", **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ALIYUN

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using Qwen"""

        start_time = time.time()

        # Build messages
        if messages is None:
            messages = [LLMMessage(role="user", content=prompt)]

        message_dicts = [m.to_dict() for m in messages]

        logger.debug(f"Generating with {self.provider.value}, prompt length: {len(prompt)}")

        content, usage, raw = await self._generate_with_retry(
            messages=message_dicts,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        generation_time = time.time() - start_time

        logger.info(
            f"Generated {len(content)} chars with {self.provider.value} "
            f"in {generation_time:.2f}s, tokens: {usage.total_tokens}"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            raw_response=raw,
            generation_time=generation_time,
        )


class DeepSeekLLMClient(LLMClientBase):
    """DeepSeek LLM client - optimized for logic and reasoning"""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat", **kwargs):
        super().__init__(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.DEEPSEEK

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using DeepSeek"""

        start_time = time.time()

        # Build messages
        if messages is None:
            messages = [LLMMessage(role="user", content=prompt)]

        message_dicts = [m.to_dict() for m in messages]

        logger.debug(f"Generating with {self.provider.value}, prompt length: {len(prompt)}")

        content, usage, raw = await self._generate_with_retry(
            messages=message_dicts,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        generation_time = time.time() - start_time

        logger.info(
            f"Generated {len(content)} chars with {self.provider.value} "
            f"in {generation_time:.2f}s, tokens: {usage.total_tokens}"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            raw_response=raw,
            generation_time=generation_time,
        )


class ArkLLMClient(LLMClientBase):
    """Ark (Doubao) LLM client - optimized for creative writing"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "ep-20250118094854-wd5pp",
        **kwargs,
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ARK

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using Doubao"""

        start_time = time.time()

        # Build messages
        if messages is None:
            messages = [LLMMessage(role="user", content=prompt)]

        message_dicts = [m.to_dict() for m in messages]

        logger.debug(f"Generating with {self.provider.value}, prompt length: {len(prompt)}")

        content, usage, raw = await self._generate_with_retry(
            messages=message_dicts,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        generation_time = time.time() - start_time

        logger.info(
            f"Generated {len(content)} chars with {self.provider.value} "
            f"in {generation_time:.2f}s, tokens: {usage.total_tokens}"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            raw_response=raw,
            generation_time=generation_time,
        )


class NvidiaLLMClient(LLMClientBase):
    """NVIDIA LLM client - backup provider using NVIDIA's API gateway"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1/chat/completions",
        model: str = "deepseek-ai/DeepSeek-V3",
        **kwargs,
    ):
        super().__init__(api_key=api_key, base_url=base_url, model=model, **kwargs)

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.NVIDIA

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using NVIDIA API"""

        start_time = time.time()

        # Build messages
        if messages is None:
            messages = [LLMMessage(role="user", content=prompt)]

        message_dicts = [m.to_dict() for m in messages]

        logger.debug(f"Generating with {self.provider.value}, prompt length: {len(prompt)}")

        content, usage, raw = await self._generate_with_retry(
            messages=message_dicts,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        generation_time = time.time() - start_time

        logger.info(
            f"Generated {len(content)} chars with {self.provider.value} "
            f"in {generation_time:.2f}s, tokens: {usage.total_tokens}"
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage=usage,
            raw_response=raw,
            generation_time=generation_time,
        )


class MultiLLMClient:
    """
    Multi-LLM client with intelligent task-type routing

    Routes different task types to the optimal LLM:
    - Qwen Long (Aliyun): 所有任务统一使用 Qwen Long，通过优化的提示词直接生成高质量内容
    - DeepSeek: 备用提供商（推理能力强）
    - Doubao (Ark): 备用提供商
    """

    # Default task type routing map
    DEFAULT_TASK_TYPE_MAP: Dict[str, LLMProvider] = {
        # Planning tasks → Qwen (long context, global memory)
        "创意脑暴": LLMProvider.ALIYUN,
        "creative_brainstorm": LLMProvider.ALIYUN,
        "大纲": LLMProvider.ALIYUN,
        "outline": LLMProvider.ALIYUN,
        "风格元素": LLMProvider.ALIYUN,
        "style_elements": LLMProvider.ALIYUN,
        "人物设计": LLMProvider.ALIYUN,
        "character_design": LLMProvider.ALIYUN,
        "世界观规则": LLMProvider.ALIYUN,
        "worldview": LLMProvider.ALIYUN,
        "世界观": LLMProvider.ALIYUN,

        # 🔥 混合方案：批量章节生成 → Qwen Long (超大上下文)
        "批量章节生成": LLMProvider.ALIYUN,
        "batch_chapter_generation": LLMProvider.ALIYUN,

        # Logic tasks → Qwen
        "事件": LLMProvider.ALIYUN,
        "events": LLMProvider.ALIYUN,
        "场景物品冲突": LLMProvider.ALIYUN,
        "scenes_items_conflicts": LLMProvider.ALIYUN,
        "场景": LLMProvider.ALIYUN,
        "评估": LLMProvider.ALIYUN,
        "evaluation": LLMProvider.ALIYUN,

        # Creative tasks → Qwen Long (使用优化的提示词直接生成高质量内容)
        "章节内容": LLMProvider.ALIYUN,
        "chapter_content": LLMProvider.ALIYUN,
        "章节": LLMProvider.ALIYUN,
        "chapter": LLMProvider.ALIYUN,
        "修订": LLMProvider.ALIYUN,
        "revision": LLMProvider.ALIYUN,
        "润色": LLMProvider.ALIYUN,
        "polish": LLMProvider.ALIYUN,
        "章节润色": LLMProvider.ALIYUN,
        "chapter_polish": LLMProvider.ALIYUN,
        "对话检查": LLMProvider.ALIYUN,
        "dialogue_check": LLMProvider.ALIYUN,
    }

    def __init__(
        self,
        providers: Optional[List[LLMClientBase]] = None,
        task_type_map: Optional[Dict[str, LLMProvider]] = None,
        default_provider: LLMProvider = LLMProvider.ALIYUN,
        fallback_order: Optional[List[LLMProvider]] = None,
    ):
        """
        Initialize multi-LLM client

        Args:
            providers: List of LLM clients (if None, will create from settings)
            task_type_map: Custom task type routing map
            default_provider: Default provider if task type not found
            fallback_order: Fallback order for failed requests
        """
        settings = get_settings()

        # Create providers from settings if not provided
        if providers is None:
            providers = self._create_providers_from_settings(settings)

        self.providers: Dict[LLMProvider, LLMClientBase] = {
            p.provider: p for p in providers if p is not None
        }

        # Use default task type map or custom
        self.task_type_map = task_type_map or self.DEFAULT_TASK_TYPE_MAP.copy()

        # Set default provider
        self.default_provider = default_provider

        # Fallback order (try alternatives in this order)
        self.fallback_order = fallback_order or [
            LLMProvider.ALIYUN,
            LLMProvider.DEEPSEEK,
            LLMProvider.ARK,
            LLMProvider.NVIDIA,
        ]

        # Remove providers that aren't available from fallback order
        self.fallback_order = [p for p in self.fallback_order if p in self.providers]

        logger.info(
            f"MultiLLMClient initialized with providers: {list(self.providers.keys())}"
        )

    def _create_providers_from_settings(self, settings) -> List[Optional[LLMClientBase]]:
        """Create LLM providers from application settings"""
        providers = []

        # Aliyun (Qwen)
        if settings.aliyun_enabled and settings.aliyun_api_key:
            providers.append(
                AliyunLLMClient(
                    api_key=settings.aliyun_api_key,
                    base_url=settings.aliyun_base_url,
                    model=settings.aliyun_model,
                    timeout=settings.llm_request_timeout,
                    max_retries=settings.max_retries,
                )
            )
            logger.info("Aliyun (Qwen) provider enabled")
        else:
            providers.append(None)
            logger.warning("Aliyun (Qwen) provider disabled or missing API key")

        # DeepSeek
        if settings.deepseek_enabled and settings.deepseek_api_key:
            providers.append(
                DeepSeekLLMClient(
                    api_key=settings.deepseek_api_key,
                    base_url=settings.deepseek_base_url,
                    model=settings.deepseek_model,
                    timeout=settings.llm_request_timeout,
                    max_retries=settings.max_retries,
                )
            )
            logger.info("DeepSeek provider enabled")
        else:
            providers.append(None)
            logger.warning("DeepSeek provider disabled or missing API key")

        # Ark (Doubao)
        if settings.ark_enabled and settings.ark_api_key:
            providers.append(
                ArkLLMClient(
                    api_key=settings.ark_api_key,
                    base_url=settings.ark_base_url,
                    model=settings.ark_model,
                    timeout=settings.llm_request_timeout,
                    max_retries=settings.max_retries,
                )
            )
            logger.info("Ark (Doubao) provider enabled")
        else:
            providers.append(None)
            logger.warning("Ark (Doubao) provider disabled or missing API key")

        # NVIDIA (optional backup)
        if settings.nvidia_enabled and settings.nvidia_api_key:
            providers.append(
                NvidiaLLMClient(
                    api_key=settings.nvidia_api_key,
                    base_url=settings.nvidia_base_url,
                    model=settings.nvidia_model,
                    timeout=settings.llm_request_timeout,
                    max_retries=settings.max_retries,
                )
            )
            logger.info("NVIDIA provider enabled")
        else:
            providers.append(None)

        return [p for p in providers if p is not None]

    def _select_provider(self, task_type: Optional[str]) -> LLMProvider:
        """
        Select the optimal provider for a given task type

        Args:
            task_type: The type of task

        Returns:
            Selected LLM provider
        """
        if task_type and task_type in self.task_type_map:
            provider = self.task_type_map[task_type]
            if provider in self.providers:
                logger.debug(f"Routed task '{task_type}' to {provider.value}")
                return provider
            else:
                logger.warning(
                    f"Task '{task_type}' mapped to {provider.value}, but provider not available"
                )

        # Use default provider
        logger.debug(f"Using default provider {self.default_provider.value} for task '{task_type}'")
        return self.default_provider

    def _get_fallback_order(self, primary: LLMProvider) -> List[LLMProvider]:
        """Get fallback order excluding the primary provider"""
        return [p for p in self.fallback_order if p != primary and p in self.providers]

    async def generate(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        llm: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text with intelligent routing and fallback

        Args:
            prompt: The prompt to generate from
            task_type: The type of task (for routing)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            messages: Optional list of messages for chat completion
            llm: Override LLM selection (provider name)
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            APIError: If all providers fail
        """
        # Select provider
        if llm:
            # Manual override
            try:
                primary_provider = LLMProvider(llm.lower())
            except ValueError:
                logger.warning(f"Invalid provider '{llm}', using default")
                primary_provider = self.default_provider
        else:
            # Use task-based routing
            primary_provider = self._select_provider(task_type)

        # Try primary provider first, then fallbacks
        providers_to_try = [primary_provider] + self._get_fallback_order(primary_provider)

        last_error = None
        for provider in providers_to_try:
            if provider not in self.providers:
                continue

            client = self.providers[provider]
            try:
                logger.info(f"Generating with {provider.value} for task '{task_type}'")
                response = await client.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                    **kwargs,
                )
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Provider {provider.value} failed for task '{task_type}': {e}"
                )
                continue

        # All providers failed
        raise Exception(
            f"All providers failed for task '{task_type}': {last_error}"
        )

    async def generate_stream(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        messages: Optional[List[LLMMessage]] = None,
        **kwargs,
    ):
        """
        Generate text with streaming response

        Args:
            prompt: The prompt to generate from
            task_type: The type of task (for routing)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            messages: Optional list of messages for chat completion
            **kwargs: Additional parameters

        Yields:
            Chunks of generated text
        """
        # Select provider
        primary_provider = self._select_provider(task_type)
        client = self.providers[primary_provider]

        # Build messages
        if messages is None:
            messages = [LLMMessage(role="user", content=prompt)]

        message_dicts = [m.to_dict() for m in messages]

        logger.info(f"Streaming with {primary_provider.value} for task '{task_type}'")

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=message_dicts,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming failed for {primary_provider.value}: {e}")
            raise

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [p.value for p in self.providers.keys()]

    def add_task_type_mapping(self, task_type: str, provider: str) -> None:
        """
        Add or update a task type mapping

        Args:
            task_type: The task type name
            provider: The provider name (aliyun, deepseek, ark, nvidia)
        """
        try:
            provider_enum = LLMProvider(provider.lower())
            self.task_type_map[task_type] = provider_enum
            logger.info(f"Added mapping: {task_type} -> {provider}")
        except ValueError:
            logger.error(f"Invalid provider: {provider}")

    def get_task_type_mapping(self) -> Dict[str, str]:
        """Get all task type mappings as provider names"""
        return {k: v.value for k, v in self.task_type_map.items()}
