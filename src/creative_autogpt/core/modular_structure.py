"""
Modular Three-Act Structure for Long-Form Web Novels

 Implements the "infinite repeating three-act structure" optimized for 
cultivation/level-up web novels (300-1000 chapters).

Structure Pattern:
- Macro: "Staircase" structure - multiple story arcs (100-200 chapters each)
- Micro: Each arc uses complete three-act structure
- Connection: Level-up progression links all arcs together

Each Story Arc (Module):
├── Act 1: Setup (20%) - Enter new map/world, establish new status quo
├── Act 2: Confrontation (60%) - Level up, conflicts, power struggles  
└── Act 3: Resolution (20%) - Climax, boss fight, transition to next arc
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import uuid

from loguru import logger


class ActType(str, Enum):
    """Three act types"""
    ACT_1_SETUP = "第一幕_ setup"
    ACT_2_CONFRONTATION = "第二幕_对抗" 
    ACT_3_RESOLUTION = "第三幕_解决"


class ChapterType(str, Enum):
    """Chapter types within an act"""
    # Act 1 chapters
    HOOK = "钩子"                    # Chapter 1: Hook the reader
    WORLD_INTRO = "世界引入"         # New map/world introduction
    STATUS_QUO = "现状建立"          # Establish new normal
    INCITING_INCIDENT = "引发事件"   # Inciting incident
    
    # Act 2 chapters  
    RISING_ACTION = "上升动作"       # Rising action, conflicts
    TRAINING = "修炼升级"            # Level up, power gain
    CONFLICT = "冲突对抗"            # Confrontations, battles
    MIDPOINT = "中点转折"            # Midpoint twist/revelation
    
    # Act 3 chapters
    CRISIS = "危机"                  # Darkest moment
    CLIMAX = "高潮"                  # Final confrontation
    RESOLUTION = "解决"              # Resolution
    TRANSITION = "过渡"              # Transition to next arc


@dataclass
class ChapterArchetype:
    """Defines the archetype/purpose of a chapter"""
    chapter_type: ChapterType
    description: str
    required_elements: List[str] = field(default_factory=list)
    suggested_length: int = 2500  # words
    
    
@dataclass  
class StoryModule:
    """
    A story module (arc) containing 100-200 chapters
    Each module is a complete three-act story
    """
    module_id: str
    module_number: int  # 1st arc, 2nd arc, etc.
    title: str          # e.g., "初入宗门", "州城争霸"
    
    # Chapter range
    start_chapter: int
    end_chapter: int
    
    # Three acts with chapter breakdown
    act_1_chapters: List[int] = field(default_factory=list)  # ~20%
    act_2_chapters: List[int] = field(default_factory=list)  # ~60%
    act_3_chapters: List[int] = field(default_factory=list)  # ~20%
    
    # Module-specific settings
    world_level: str = ""           # e.g., "凡俗界", "修真界", "仙界"
    power_level_start: str = ""     # Starting cultivation level
    power_level_end: str = ""       # Ending cultivation level
    
    # Key events in this module
    key_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Antagonist for this module
    module_antagonist: Optional[str] = None
    
    # Transition to next module
    transition_hook: str = ""       # Hook leading to next arc
    
    def get_chapter_count(self) -> int:
        """Get total chapters in this module"""
        return len(self.act_1_chapters) + len(self.act_2_chapters) + len(self.act_3_chapters)
    
    def get_act_for_chapter(self, chapter_index: int) -> Optional[ActType]:
        """Get which act a chapter belongs to"""
        if chapter_index in self.act_1_chapters:
            return ActType.ACT_1_SETUP
        elif chapter_index in self.act_2_chapters:
            return ActType.ACT_2_CONFRONTATION
        elif chapter_index in self.act_3_chapters:
            return ActType.ACT_3_RESOLUTION
        return None


@dataclass
class NovelStructure:
    """
    Overall novel structure using modular three-act approach
    """
    title: str
    total_chapters: int
    modules: List[StoryModule] = field(default_factory=list)
    
    # Global story elements
    global_antagonist: Optional[str] = None  # Final boss
    main_character_arc: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_module_for_chapter(self, chapter_index: int) -> Optional[StoryModule]:
        """Get which module a chapter belongs to"""
        for module in self.modules:
            if module.start_chapter <= chapter_index <= module.end_chapter:
                return module
        return None
    
    def get_progress_percentage(self, chapter_index: int) -> float:
        """Get overall progress percentage"""
        if self.total_chapters == 0:
            return 0.0
        return (chapter_index / self.total_chapters) * 100


class ModularStructurePlanner:
    """
    Plans novel structure using modular three-act approach
    """
    
    # Default module sizes for web novels
    DEFAULT_MODULE_SIZE = 100  # chapters per module
    MIN_MODULE_SIZE = 50
    MAX_MODULE_SIZE = 200
    
    # Act distribution within a module
    ACT_1_PERCENTAGE = 0.20  # 20%
    ACT_2_PERCENTAGE = 0.60  # 60%  
    ACT_3_PERCENTAGE = 0.20  # 20%
    
    # Cultivation realm progression (example for cultivation novels)
    CULTIVATION_REALMS = [
        ("炼气期", 1, 50),
        ("筑基期", 51, 150),
        ("金丹期", 151, 300),
        ("元婴期", 301, 500),
        ("化神期", 501, 700),
        ("渡劫期", 701, 850),
        ("大乘期", 851, 1000),
    ]
    
    # World levels for map switching
    WORLD_LEVELS = [
        "凡俗界",      # Mortal world
        "修真界",      # Cultivation world  
        "上界",        # Upper realm
        "仙界",        # Immortal realm
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.module_size = self.config.get("module_size", self.DEFAULT_MODULE_SIZE)
        
    def plan_structure(
        self,
        title: str,
        total_chapters: int,
        genre: str = "cultivation",
        outline: Optional[str] = None,
    ) -> NovelStructure:
        """
        Plan novel structure with modular three-act arcs
        
        Args:
            title: Novel title
            total_chapters: Total chapter count (e.g., 1000)
            genre: Genre type (default: cultivation)
            outline: Optional story outline
            
        Returns:
            NovelStructure with all modules planned
        """
        logger.info(f"Planning modular three-act structure for '{title}' ({total_chapters} chapters)")
        
        # Calculate number of modules
        num_modules = max(1, round(total_chapters / self.module_size))
        # Adjust module size to fit exactly
        actual_module_size = total_chapters // num_modules
        
        logger.info(f"Creating {num_modules} modules, ~{actual_module_size} chapters each")
        
        modules = []
        current_chapter = 1
        
        for module_num in range(1, num_modules + 1):
            # Calculate chapter range for this module
            start_chapter = current_chapter
            # Last module takes remaining chapters
            if module_num == num_modules:
                end_chapter = total_chapters
            else:
                end_chapter = min(current_chapter + actual_module_size - 1, total_chapters)
            
            module_chapter_count = end_chapter - start_chapter + 1
            
            # Determine cultivation realm for this module
            power_start, power_end = self._get_power_levels_for_range(start_chapter, end_chapter)
            
            # Determine world level
            world_level = self._get_world_level_for_module(module_num, num_modules)
            
            # Generate module title
            module_title = self._generate_module_title(module_num, world_level, power_start)
            
            # Split into three acts
            act_1_count = max(3, int(module_chapter_count * self.ACT_1_PERCENTAGE))
            act_3_count = max(3, int(module_chapter_count * self.ACT_3_PERCENTAGE))
            act_2_count = module_chapter_count - act_1_count - act_3_count
            
            act_1_chapters = list(range(start_chapter, start_chapter + act_1_count))
            act_2_chapters = list(range(start_chapter + act_1_count, start_chapter + act_1_count + act_2_count))
            act_3_chapters = list(range(start_chapter + act_1_count + act_2_count, end_chapter + 1))
            
            # Create module
            module = StoryModule(
                module_id=str(uuid.uuid4()),
                module_number=module_num,
                title=module_title,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                act_1_chapters=act_1_chapters,
                act_2_chapters=act_2_chapters,
                act_3_chapters=act_3_chapters,
                world_level=world_level,
                power_level_start=power_start,
                power_level_end=power_end,
                key_events=self._generate_key_events(module_num, act_1_chapters, act_2_chapters, act_3_chapters),
                module_antagonist=f"模块{module_num}反派",  # Placeholder
                transition_hook=f"通往下一个世界的线索",  # Placeholder
            )
            
            modules.append(module)
            logger.info(f"  Module {module_num}: {module_title} (Chapters {start_chapter}-{end_chapter}, {module_chapter_count} chapters)")
            logger.info(f"    Act 1 (Setup): {len(act_1_chapters)} chapters")
            logger.info(f"    Act 2 (Confrontation): {len(act_2_chapters)} chapters")
            logger.info(f"    Act 3 (Resolution): {len(act_3_chapters)} chapters")
            
            current_chapter = end_chapter + 1
        
        structure = NovelStructure(
            title=title,
            total_chapters=total_chapters,
            modules=modules,
            global_antagonist="终极反派",  # Placeholder
            main_character_arc=[],  # To be filled
        )
        
        logger.info(f"✅ Modular structure planning complete: {len(modules)} modules, {total_chapters} chapters")
        return structure
    
    def _get_power_levels_for_range(self, start: int, end: int) -> Tuple[str, str]:
        """Get cultivation realm for chapter range"""
        start_realm = "未知"
        end_realm = "未知"
        
        for realm, realm_start, realm_end in self.CULTIVATION_REALMS:
            if realm_start <= start <= realm_end:
                start_realm = realm
            if realm_start <= end <= realm_end:
                end_realm = realm
                
        return start_realm, end_realm
    
    def _get_world_level_for_module(self, module_num: int, total_modules: int) -> str:
        """Determine world level based on module progression"""
        # Distribute modules across world levels
        modules_per_world = max(1, total_modules // len(self.WORLD_LEVELS))
        world_index = min((module_num - 1) // modules_per_world, len(self.WORLD_LEVELS) - 1)
        return self.WORLD_LEVELS[world_index]
    
    def _generate_module_title(self, module_num: int, world_level: str, power_level: str) -> str:
        """Generate a title for the module"""
        module_titles = {
            1: "初入修仙路",
            2: "宗门风云",
            3: "州城争霸", 
            4: "中州风云",
            5: "上界之战",
            6: "仙界征途",
            7: "天道之争",
        }
        return module_titles.get(module_num, f"{world_level}篇·{power_level}")
    
    def _generate_key_events(
        self,
        module_num: int,
        act_1_chapters: List[int],
        act_2_chapters: List[int],
        act_3_chapters: List[int],
    ) -> List[Dict[str, Any]]:
        """Generate key events for a module"""
        events = []
        
        # Act 1 events
        if act_1_chapters:
            events.append({
                "name": f"进入新世界",
                "chapter": act_1_chapters[0],
                "act": ActType.ACT_1_SETUP.value,
                "description": "主角进入新的地图/世界",
            })
            if len(act_1_chapters) >= 3:
                events.append({
                    "name": f"引发事件",
                    "chapter": act_1_chapters[-1],
                    "act": ActType.ACT_1_SETUP.value,
                    "description": "触发本模块主要冲突的事件",
                })
        
        # Act 2 events
        if act_2_chapters:
            mid_index = len(act_2_chapters) // 2
            events.append({
                "name": f"中点转折",
                "chapter": act_2_chapters[mid_index],
                "act": ActType.ACT_2_CONFRONTATION.value,
                "description": "剧情发生重大转折",
            })
        
        # Act 3 events
        if act_3_chapters:
            events.append({
                "name": f"模块高潮",
                "chapter": act_3_chapters[len(act_3_chapters)//2],
                "act": ActType.ACT_3_RESOLUTION.value,
                "description": "本模块的最终决战",
            })
            if len(act_3_chapters) >= 2:
                events.append({
                    "name": f"前往下一世界",
                    "chapter": act_3_chapters[-1],
                    "act": ActType.ACT_3_RESOLUTION.value,
                    "description": "为下一个模块做铺垫",
                })
        
        return events
    
    def get_chapter_guidelines(self, chapter_index: int, structure: NovelStructure) -> Dict[str, Any]:
        """
        Get writing guidelines for a specific chapter
        
        Returns information about:
        - Which module/act this chapter is in
        - What type of chapter it should be
        - Required story beats
        """
        module = structure.get_module_for_chapter(chapter_index)
        if not module:
            return {}
        
        act = module.get_act_for_chapter(chapter_index)
        progress_in_module = (chapter_index - module.start_chapter) / module.get_chapter_count()
        
        # Determine chapter archetype based on position
        chapter_type = self._determine_chapter_type(chapter_index, module, act)
        
        return {
            "module": module.module_number,
            "module_title": module.title,
            "act": act.value if act else "未知",
            "chapter_type": chapter_type.value if chapter_type else "未知",
            "progress_in_module": progress_in_module,
            "world_level": module.world_level,
            "power_level": self._get_power_level_for_chapter(chapter_index),
            "required_beats": self._get_required_beats(chapter_type, act),
            "suggested_word_count": 2500,
        }
    
    def _determine_chapter_type(
        self,
        chapter_index: int,
        module: StoryModule,
        act: Optional[ActType],
    ) -> Optional[ChapterType]:
        """Determine what type of chapter this should be"""
        if not act:
            return None
        
        if act == ActType.ACT_1_SETUP:
            if chapter_index == module.start_chapter:
                return ChapterType.HOOK
            elif chapter_index == module.start_chapter + 1:
                return ChapterType.WORLD_INTRO
            elif chapter_index == module.act_1_chapters[-1]:
                return ChapterType.INCITING_INCIDENT
            else:
                return ChapterType.STATUS_QUO
                
        elif act == ActType.ACT_2_CONFRONTATION:
            if chapter_index == module.act_2_chapters[len(module.act_2_chapters)//2]:
                return ChapterType.MIDPOINT
            elif chapter_index % 10 == 0:  # Every 10th chapter is a training/conflict chapter
                return ChapterType.CONFLICT
            else:
                return ChapterType.RISING_ACTION
                
        elif act == ActType.ACT_3_RESOLUTION:
            if chapter_index == module.act_3_chapters[len(module.act_3_chapters)//2]:
                return ChapterType.CLIMAX
            elif chapter_index == module.end_chapter:
                return ChapterType.TRANSITION
            else:
                return ChapterType.CRISIS
        
        return ChapterType.RISING_ACTION
    
    def _get_power_level_for_chapter(self, chapter_index: int) -> str:
        """Get cultivation level for chapter"""
        for realm, start, end in self.CULTIVATION_REALMS:
            if start <= chapter_index <= end:
                return realm
        return "未知"
    
    def _get_required_beats(self, chapter_type: Optional[ChapterType], act: Optional[ActType]) -> List[str]:
        """Get required story beats for chapter type"""
        if not chapter_type:
            return []
        
        beats_map = {
            ChapterType.HOOK: ["吸引读者", "建立期待", "埋下伏笔"],
            ChapterType.WORLD_INTRO: ["展示新地图", "介绍新规则", "建立新目标"],
            ChapterType.INCITING_INCIDENT: ["打破现状", "引发冲突", "主角必须行动"],
            ChapterType.RISING_ACTION: ["推进剧情", "升级修炼", "积累矛盾"],
            ChapterType.MIDPOINT: ["重大转折", "真相揭露", "方向改变"],
            ChapterType.CONFLICT: ["正面冲突", "战斗/竞争", "展现实力"],
            ChapterType.CRISIS: ["至暗时刻", "最大危机", "背水一战"],
            ChapterType.CLIMAX: ["最终对决", "高潮战斗", "问题解决"],
            ChapterType.TRANSITION: ["收尾本模块", "铺垫下一模块", "钩子吸引继续"],
        }
        
        return beats_map.get(chapter_type, ["推进剧情"])


# Chapter archetype definitions
CHAPTER_ARCHETYPES = {
    ChapterType.HOOK: ChapterArchetype(
        chapter_type=ChapterType.HOOK,
        description="开篇钩子，吸引读者继续阅读",
        required_elements=["悬念", "冲突", "期待感"],
        suggested_length=2500,
    ),
    ChapterType.WORLD_INTRO: ChapterArchetype(
        chapter_type=ChapterType.WORLD_INTRO,
        description="引入新世界/新地图",
        required_elements=["世界观展示", "新规则介绍", "新目标建立"],
        suggested_length=2500,
    ),
    ChapterType.TRAINING: ChapterArchetype(
        chapter_type=ChapterType.TRAINING,
        description="修炼升级章节",
        required_elements=["修炼过程", "突破时刻", "实力提升"],
        suggested_length=2500,
    ),
    ChapterType.CONFLICT: ChapterArchetype(
        chapter_type=ChapterType.CONFLICT,
        description="冲突对抗章节",
        required_elements=["矛盾激化", "正面交锋", "实力展现"],
        suggested_length=2500,
    ),
    ChapterType.CLIMAX: ChapterArchetype(
        chapter_type=ChapterType.CLIMAX,
        description="高潮战斗章节",
        required_elements=["最终对决", "全力以赴", "胜负揭晓"],
        suggested_length=3000,
    ),
}
