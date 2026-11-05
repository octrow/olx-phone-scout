#!/usr/bin/env python3
"""
Phone Value Scoring Configuration
=================================
This file contains all scoring rules and weights for calculating phone value scores.
Customize these settings to change how phones are ranked.

UPDATED: 2025-11-03 - Added display quality + warranty scoring (Phase 2)

The total score is calculated from multiple factors:
- Discount percentage (0-35 points) [REDUCED from 40]
- Phone age (0-25 points) [REDUCED from 30]
- Tier/quality (0-40 points) [REDUCED from 50]
- Storage (0-20 points) [REDUCED from 34]
- RAM (0-18 points) [REDUCED from 26]
- Price range bonus (0-20 points) [REDUCED from 25]
- Condition (-90 to +20 points) [UNCHANGED]
- Brand reputation (0-20 points) [REDUCED from 30]
- Camera (0-30 points) [REDUCED from 50]
- 🆕 Processor/Chipset (0-30 points) [NEW Phase 1]
- 🆕 Battery Health (-30 to +20 points) [NEW Phase 1]
- 🆕 Display Quality (0-20 points) [NEW Phase 2]
- 🆕 Warranty/Seller (0-10 points) [NEW Phase 2]

Maximum possible score: ~278 points before AI bonuses; the report shows raw points
Typical high-value phone: 120-140 points
"""

import json
import logging
import re
from typing import Any, TypedDict, cast

from src.core import constants


# Type definitions for scoring dictionaries
class DisplayScoringItem(TypedDict):
    keywords: list[str]
    points: int
    label: str


class WarrantyScoringItem(TypedDict):
    keywords: list[str]
    points: int
    label: str


class WarrantyNegativeItem(TypedDict):
    keywords: list[str]
    penalty: int
    label: str | None


# =============================================================================
# DISCOUNT SCORING (0-35 points) - REDUCED to balance with new factors
# =============================================================================
# Higher discount = better value
# NOTE: Realistic max discount ~70-80% for used flagships
# UPDATED: 2025-11-02 - Reduced from 40 to 35 to accommodate processor/battery scoring

DISCOUNT_THRESHOLDS = [
    {"min": 80, "points": 35, "label": "💎 Amazing deal"},  # 80%+ off (rare)
    {"min": 70, "points": 27, "label": "🔥 Great deal"},  # 70-79% off
    {"min": 60, "points": 20, "label": "✅ Good deal"},  # 60-69% off
    {"min": 50, "points": 14, "label": "👍 Fair deal"},  # 50-59% off
    {"min": 40, "points": 9, "label": "📊 Decent discount"},  # 40-49% off
]

# =============================================================================
# AGE FACTOR (0-25 points) - IMPROVED with non-linear decay
# =============================================================================
# Newer phones score higher
# UPDATED: 2025-11-02 - Reduced from 30 to 25, improved decay curve to match real depreciation

AGE_SCORING = [
    {"max_age": 1, "points": 25, "label": "📱 Very recent phone"},  # Released this/last year
    {"max_age": 2, "points": 18, "label": "📅 Recent phone"},  # 2 years old (still good)
    {"max_age": 3, "points": 10, "label": "📆 Still modern"},  # 3 years old
    {"max_age": 4, "points": 4, "label": "📜 Getting old"},  # 4 years old
    {"max_age": 5, "points": 1, "label": "📜 Old phone"},  # 5 years old
]

# Current year for age calculation
CURRENT_YEAR = 2025

# =============================================================================
# TIER SCORING (0-40 points) - REBALANCED to reduce flagship bias
# =============================================================================
# Phone quality tier bonus
# UPDATED: 2025-11-02 - Reduced all tiers by ~20% to prevent flagship inflation
# NOTE: Mid-range phones are now more competitive

TIER_SCORES = {
    "flagship-ultra": 40,  # Ultra flagships (S24 Ultra, iPhone 16 Pro Max, Xiaomi 14 Ultra)
    "flagship+": 35,  # Plus flagships (S24+, iPhone 16 Plus)
    "flagship": 30,  # Flagships (S24, Pixel 9, iPhone 16, OnePlus 12)
    "flagship-lite": 24,  # Flagship Lite/FE (S24 FE, S21 FE)
    "mid-flagship": 18,  # Upper mid-range (Pixel 8a, OnePlus 12R, POCO F5)
    "mid": 10,  # Mid-range (Redmi Note, Samsung A52)
    "budget-mid": 5,  # Lower mid-range (Redmi 9, Samsung A32)
    "budget": 2,  # Budget phones (Redmi C series)
}

# =============================================================================
# STORAGE BONUS (0-20 points) - REDUCED by 41% (was overweighted)
# =============================================================================
# More storage = better
# UPDATED: 2025-11-02 - Storage less critical in cloud-first era, reduced from 34 to 20

STORAGE_BONUS = [
    {"keywords": ["1tb", "1 tb"], "points": 20, "label": "💾 Excellent 1TB storage"},
    {"keywords": ["512gb", "512 gb"], "points": 15, "label": "💾 Great 512GB storage"},
    {"keywords": ["256gb", "256 gb"], "points": 8, "label": "💾 Good 256GB storage"},
    {"keywords": ["128gb", "128 gb"], "points": 3, "label": "💾 Adequate 128GB storage"},
    {"keywords": ["64gb", "64 gb"], "points": 0, "label": "💾 Limited 64GB storage"},
]

# =============================================================================
# RAM BONUS (0-18 points) - REDUCED by 31% (moderate adjustment)
# =============================================================================
# More RAM = better multitasking
# UPDATED: 2025-11-02 - RAM less critical than processor, reduced from 26 to 18

RAM_BONUS = [
    {"patterns": [r"16\s*gb", r"16/", r"ram\s*16"], "points": 18, "label": "🚀 Excellent 16GB RAM"},
    {"patterns": [r"12\s*gb", r"12/", r"ram\s*12"], "points": 14, "label": "🚀 Great 12GB RAM"},
    {"patterns": [r"8\s*gb", r"8/", r"ram\s*8"], "points": 10, "label": "🚀 Good 8GB RAM"},
    {"patterns": [r"6\s*gb", r"6/", r"ram\s*6"], "points": 6, "label": "🚀 Decent 6GB RAM"},
    {"patterns": [r"4\s*gb", r"4/", r"ram\s*4"], "points": 0, "label": "🚀 Limited 4GB RAM"},
]

# =============================================================================
# PRICE RANGE BONUS (0-20 points) - SLIGHT REDUCTION
# =============================================================================
# Lower current price = bonus points (finding cheap gems)
# UPDATED: 2025-11-02 - Reduced from 25 to 20 for better balance

PRICE_RANGE_SCORING = [
    {"max_price": 40000, "points": 20, "label": "💰 Very affordable"},
    {"max_price": 50000, "points": 16, "label": "💰 Affordable"},
    {"max_price": 60000, "points": 12, "label": "💰 Reasonable price"},
    {"max_price": 80000, "points": 8, "label": "💵 Fair price"},
    {"max_price": 100000, "points": 4, "label": "💵 Mid-range price"},
]

# =============================================================================
# CONDITION SCORING (0-20 points)
# =============================================================================
# Phone condition based on description keywords


class ConditionConfig(TypedDict):
    """Type definition for condition scoring configuration"""

    keywords: list[str]
    points: int
    label: str


# Positive condition keywords (add points)
# UPDATED: 2025-11-02 - Expanded based on 264 real OLX listings analysis
CONDITION_POSITIVE: list[ConditionConfig] = [
    {
        "keywords": [
            # Russian (stem: отлич-)
            "отличное",
            "отличное состояние",
            "отличном состоянии",
            "отлично",
            "отличная",
            "отличный",
            "отличного",
            # Common typos
            "атличное",
            "атлично",
            "атличном",  # а instead of о
            # Russian (stem: идеал-)
            "идеальное",
            "идеальное состояние",
            "идеальном состоянии",
            "идеально",
            "идеальный",
            "идеальная",
            "идеале",
            # Common typos
            "идал состояние",
            "идал",
            "идалом",
            "идале",  # missing е
            "идиальное",
            "идиальном",
            "идиал",  # extra и
            "идеалное",
            "идеалом",  # missing ь
            # English
            "perfect",
            "perfect condition",
            "excellent",
            "excellent condition",
            # Kazakh
            "керемет",
            "тамаша",
            "өте жақсы",
        ],
        "points": 15,
        "label": "✨ Excellent condition",
    },
    {
        "keywords": [
            # Russian (stem: хорош-)
            "хорошее",
            "хорошее состояние",
            "хорошем состоянии",
            "хороший",
            "хорошо",
            "хорошая",
            "хорошие",
            "хорошего",
            "хорошим",
            # Common typos
            "харошее",
            "харошо",
            "харошем",
            "харош",  # а instead of о
            "хорошое",
            "харошое",  # о instead of е
            # English
            "good",
            "good condition",
            "very good",
            # Kazakh
            "жақсы",
            "жақсы жағдай",
        ],
        "points": 7,
        "label": "👍 Good condition",
    },
    {
        "keywords": [
            # Completeness
            "полный комплект",
            "комплект полный",
            "комплектация полная",
            "полная комплектация",
            "полная комплект",  # grammar error but common
            # Box variants
            "коробка",
            "коробке",
            "с коробкой",
            "коробки",
            "коробкой",
            # Common typos
            "каробка",
            "каробке",
            "каробки",  # а instead of о
            "коропка",
            "коропке",  # п instead of б
            # English
            "box",
            "complete set",
            "full set",
            # Kazakh
            "толық жинақ",
        ],
        "points": 3,
        "label": "📦 With box/full set",
    },
]

# Negative condition keywords (subtract points)
CONDITION_NEGATIVE: list[ConditionConfig] = [
    # Critical issues (basically unusable)
    {
        "keywords": [
            # Not working
            "не работает",
            "не работают",
            "не включается",
            "не вкл",
            # Typos
            "не роботает",
            "нераб отает",
            "не раб",  # Common typos
            # English
            "broken",
            "dead",
            "not working",
            "does not work",
            "doesn't work",
        ],
        "points": -80,
        "label": "❌ Not working",
    },
    {
        "keywords": ["на запчасти", "for parts", "запчасти", "на детали"],
        "points": -90,
        "label": "🔧 For parts",
    },
    {
        # Activation-locked iPhones can't be set up: unusable. Not bare "icloud": sellers write "icloud чистый"
        "keywords": [
            "айклауд блок",
            "айклаудта блок",
            "блок айклауд",
            "icloud блок",
            "блок icloud",
            "icloud lock",
            "activation lock",
            "на блоке",
            "блокта",
            "айклаул",
        ],
        "points": -100,
        "label": "🔒 iCloud locked (unusable)",
    },
    {
        "keywords": [
            "сеть не ловит",
            "нет сети",
            "no network",
            "no signal",
            "только wifi",
            "только вайфай",
            "лучше использовать на вайфай",
        ],
        "points": -70,
        "label": "📡 Network issues",
    },
    {
        "keywords": ["дисплей не работает", "экран не работает", "screen broken", "display broken"],
        "points": -75,
        "label": "📵 Screen broken",
    },
    # Major issues (significant defects)
    {
        "keywords": ["треснут", "трещина", "cracked", "crack", "треснул", "трескается"],
        "points": -35,
        "label": "🔴 Cracked",
    },
    {
        "keywords": ["выгорание", "burn-in", "burn in", "выгорел экран", "выгорание экрана"],
        "points": -40,
        "label": "🔥 Screen burn-in",
    },
    {
        "keywords": [
            "полоса",
            "полосы",
            "полосу",
            "полоска",
            "полоски",
            "засвет",
            "пятно на экране",
            "пятна на экране",
            "битый пиксел",
            "битые пиксел",
            "мерцает",
            "мерцание",
            "рябит",
            "line on screen",
            "lines on screen",
            "green line",
            "dead pixel",
        ],
        "points": -45,
        "label": "📺 Screen defect (lines/spots)",
    },
    {
        # Kazakh: сынган/сынған = broken, тез бітеді = drains fast
        "keywords": ["сынган", "сынған", "сынык", "сынық", "тез бітед", "тез битед"],
        "points": -45,
        "label": "🔴 Damage (Kazakh description)",
    },
    {
        "keywords": [
            "фейс нет",
            "face нет",
            "face id нет",
            "без фейс",
            "без face",
            "кроме фейс",
            "кроме face",
            "фейс не",
            "face не",
            "face id не",
            "фейс айди не",
            "только фейс",
            "минус фейс",
        ],
        "points": -30,
        "label": "🙈 Face ID not working",
    },
    {
        "keywords": ["залит", "попала вода", "water damage", "был в воде"],
        "points": -50,
        "label": "💧 Water damage",
    },
    {
        "keywords": [
            # Battery problems
            "не держит батарея",
            "плохая батарея",
            "слабая батарея",
            "батарея не держит",
            "батарея умерла",
            "быстро разряжается",
            # Typos
            "батарейка не держит",
            "батарея недержит",  # Spacing errors
            "батареия",
            "батарэя",  # Typo variations
            # English
            "battery dead",
            "poor battery",
            "battery doesn't hold",
            "drains fast",
            "bad battery",
        ],
        "points": -30,
        "label": "🔋 Battery issues",
    },
    {
        "keywords": ["камера не работает", "camera broken", "камера сломана", "не фотографирует"],
        "points": -25,
        "label": "📷 Camera broken",
    },
    {
        "keywords": [
            "Экран менянный",
            "screen replaced",
            "замена экрана",
            "дисплей меняли",
            "экран меняли",
        ],
        "points": -15,
        "label": "🔥 Screen replaced",
    },
    # Minor issues
    {
        "keywords": ["царапины", "scratches", "worn", "потертости", "потёртости"],
        "points": -8,
        "label": "⚠️ Scratches/wear",
    },
    {
        "keywords": ["сколы", "chips", "небольшие повреждения"],
        "points": -12,
        "label": "⚠️ Chips/damage",
    },
    {
        "keywords": ["без комплекта", "без коробки", "нет зарядки", "нет кабеля"],
        "points": -5,
        "label": "📦 No accessories",
    },
]

# Missing critical components (severe penalties)
# UPDATED: 2025-11-02 - Expanded based on real listings
MISSING_COMPONENTS: list[ConditionConfig] = [
    {
        "keywords": [
            # S Pen missing (Samsung Note/Ultra)
            "без стилуса",
            "нет стилуса",
            "стилуса нет",
            "отсутствие s pen",
            "нет s pen",
            "s pen нет",
            "s pen отсутствует",
            "умер s pen",
            "s pen умер",
            "no s pen",
            "missing s pen",
            "s pen dead",
        ],
        "points": -15,
        "label": "🖊️ Missing S Pen",
    },
    {
        "keywords": ["без симки", "нет сим", "sim locked", "заблокирован"],
        "points": -25,
        "label": "🔒 SIM locked",
    },
]

# Urgency keywords (add points - seller motivated)
URGENCY_KEYWORDS = ["срочно", "urgent", "быстро", "торг", "negotiable"]
URGENCY_BONUS = 5
URGENCY_LABEL = "⚡ Urgent sale"

# =============================================================================
# BRAND REPUTATION (0-20 points) - REDUCED fallback weight
# =============================================================================
# Used when no market price data is available
# Higher score = more trusted brand
# UPDATED: 2025-11-02 - Reduced from 30 to 20, proportionally scaled all brands

BRAND_SCORES = {
    "google": 20,  # Google Pixel
    "samsung": 18,  # Samsung
    "oneplus": 17,  # OnePlus
    "xiaomi": 18,  # Xiaomi
    "poco": 12,  # POCO
    "realme": 11,  # Realme
    "oppo": 11,  # OPPO
    "vivo": 11,  # Vivo
    "motorola": 13,  # Motorola
    "huawei": 15,  # Huawei (good hardware, limited software)
    "honor": 11,  # Honor
    "asus": 13,  # ASUS ROG
    "nothing": 15,  # Nothing Phone
}

# Default score for unknown brands
DEFAULT_BRAND_SCORE = 8

# =============================================================================
# CAMERA SCORING (0-30 points) - REDUCED by 40% (was overweighted)
# =============================================================================
# Based on DXOMark camera rankings (https://www.dxomark.com/smartphones/)
# UPDATED: 2025-11-02 - Reduced from 50 to 30 points (camera < processor importance)
# All scores scaled by 0.6x to maintain proportions

CAMERA_SCORES = {
    # Top tier cameras (24-30 points) - DXOMark 140+
    "huawei p60 pro": {"score": 30, "dxomark": 156, "label": "📸 Top camera"},
    "huawei mate 60 pro": {"score": 27, "dxomark": 149, "label": "📸 Top camera"},
    "oppo find x7 ultra": {"score": 26, "dxomark": 147, "label": "📸 Top camera"},
    "honor magic6 pro": {"score": 25, "dxomark": 146, "label": "📸 Top camera"},
    "vivo x100 ultra": {"score": 25, "dxomark": 145, "label": "📸 Top camera"},
    "vivo x100 pro": {"score": 24, "dxomark": 144, "label": "📸 Top camera"},
    # Excellent cameras (18-23 points) - DXOMark 135-140
    "xiaomi 14 ultra": {"score": 23, "dxomark": 143, "label": "📸 Excellent camera"},
    "google pixel 9 pro": {"score": 22, "dxomark": 140, "label": "📸 Excellent camera"},
    "google pixel 8 pro": {"score": 20, "dxomark": 138, "label": "📸 Excellent camera"},
    "xiaomi 13 ultra": {"score": 20, "dxomark": 137, "label": "📸 Excellent camera"},
    "samsung s24 ultra": {"score": 19, "dxomark": 136, "label": "📸 Excellent camera"},
    "oneplus 12": {"score": 19, "dxomark": 135, "label": "📸 Excellent camera"},
    # Very good cameras (15-18 points) - DXOMark 130-135
    "samsung s23 ultra": {"score": 19, "dxomark": 135, "label": "📸 Very good camera"},
    "xiaomi 14": {"score": 18, "dxomark": 134, "label": "📸 Very good camera"},
    "google pixel 9": {"score": 17, "dxomark": 133, "label": "📸 Very good camera"},
    "google pixel 8": {"score": 17, "dxomark": 132, "label": "📸 Very good camera"},
    "samsung s24": {"score": 16, "dxomark": 131, "label": "📸 Very good camera"},
    "oneplus 11": {"score": 16, "dxomark": 130, "label": "📸 Very good camera"},
    # Good cameras (12-15 points) - DXOMark 125-130
    "samsung s23": {"score": 15, "dxomark": 129, "label": "📸 Good camera"},
    "google pixel 7 pro": {"score": 14, "dxomark": 128, "label": "📸 Good camera"},
    "samsung s22 ultra": {"score": 14, "dxomark": 127, "label": "📸 Good camera"},
    "xiaomi 13": {"score": 13, "dxomark": 126, "label": "📸 Good camera"},
    "samsung s24+": {"score": 13, "dxomark": 126, "label": "📸 Good camera"},
    "google pixel 7": {"score": 13, "dxomark": 125, "label": "📸 Good camera"},
    # Solid cameras (9-12 points) - DXOMark 120-125
    "samsung s22": {"score": 12, "dxomark": 124, "label": "📸 Solid camera"},
    "samsung s21 ultra": {"score": 11, "dxomark": 123, "label": "📸 Solid camera"},
    "google pixel 6 pro": {"score": 11, "dxomark": 122, "label": "📸 Solid camera"},
    "oneplus 10 pro": {"score": 10, "dxomark": 121, "label": "📸 Solid camera"},
    "samsung s23+": {"score": 10, "dxomark": 121, "label": "📸 Solid camera"},
    "xiaomi 12": {"score": 10, "dxomark": 120, "label": "📸 Solid camera"},
    # Decent cameras (6-9 points) - DXOMark 115-120
    "google pixel 6": {"score": 9, "dxomark": 119, "label": "📸 Decent camera"},
    "samsung s21": {"score": 8, "dxomark": 118, "label": "📸 Decent camera"},
    "oneplus 9 pro": {"score": 8, "dxomark": 117, "label": "📸 Decent camera"},
    "samsung s20 ultra": {"score": 7, "dxomark": 116, "label": "📸 Decent camera"},
    "google pixel 8a": {"score": 7, "dxomark": 115, "label": "📸 Decent camera"},
    "xiaomi 11": {"score": 6, "dxomark": 115, "label": "📸 Decent camera"},
    # Average cameras (3-6 points) - DXOMark 110-115
    "samsung s21 fe": {"score": 5, "dxomark": 114, "label": "📸 Average camera"},
    "oneplus 9": {"score": 5, "dxomark": 113, "label": "📸 Average camera"},
    "samsung s20": {"score": 4, "dxomark": 112, "label": "📸 Average camera"},
    "poco f5": {"score": 4, "dxomark": 111, "label": "📸 Average camera"},
    "samsung s24 fe": {"score": 3, "dxomark": 110, "label": "📸 Average camera"},
    # Mid-range cameras (0-3 points) - DXOMark <110
    "redmi note 13 pro": {"score": 2, "dxomark": 109, "label": "📸 Mid-range camera"},
    "redmi note 12 pro": {"score": 2, "dxomark": 105, "label": "📸 Mid-range camera"},
    "poco f4": {"score": 1, "dxomark": 104, "label": "📸 Mid-range camera"},
    "redmi note 11 pro": {"score": 1, "dxomark": 100, "label": "📸 Basic camera"},
}

# Camera score tiers for brands without specific data
CAMERA_TIER_DEFAULTS = {
    "flagship-ultra": 25,  # Assume excellent camera
    "flagship+": 20,  # Assume very good camera
    "flagship": 17,  # Assume good camera
    "flagship-lite": 13,  # Assume solid camera
    "mid-flagship": 10,  # Assume decent camera
    "mid": 6,  # Assume average camera
    "budget-mid": 2,  # Assume basic camera
    "budget": 0,  # Assume entry-level camera
}

# =============================================================================
# PROCESSOR/CHIPSET SCORING (0-30 points) 🆕 NEW
# =============================================================================
# Based on performance benchmarks (AnTuTu v10, Geekbench)
# IMPORTANT: Keep modest weight - modern processors are "good enough" for daily tasks
# Sources: AnTuTu rankings, Geekbench database, manufacturer specs

PROCESSOR_SCORES = {
    # === QUALCOMM SNAPDRAGON (Flagship 8-series) ===
    "snapdragon 8 gen 3": {
        "score": 30,
        "tier": "flagship-ultra",
        "antutu": 1900000,
        "label": "⚡ SD 8 Gen 3 (top-tier)",
    },
    "snapdragon 8 gen 2": {
        "score": 28,
        "tier": "flagship",
        "antutu": 1400000,
        "label": "⚡ SD 8 Gen 2 (flagship)",
    },
    "snapdragon 8+ gen 1": {
        "score": 26,
        "tier": "flagship",
        "antutu": 1100000,
        "label": "⚡ SD 8+ Gen 1",
    },
    "snapdragon 8 gen 1": {
        "score": 25,
        "tier": "flagship",
        "antutu": 1000000,
        "label": "⚡ SD 8 Gen 1",
    },
    "snapdragon 888+": {
        "score": 23,
        "tier": "flagship-lite",
        "antutu": 820000,
        "label": "⚡ SD 888+",
    },
    "snapdragon 888": {
        "score": 22,
        "tier": "flagship-lite",
        "antutu": 800000,
        "label": "⚡ SD 888",
    },
    "snapdragon 870": {
        "score": 21,
        "tier": "flagship-lite",
        "antutu": 700000,
        "label": "⚡ SD 870 (efficient)",
    },
    "snapdragon 865+": {
        "score": 19,
        "tier": "flagship-lite",
        "antutu": 650000,
        "label": "⚡ SD 865+",
    },
    "snapdragon 865": {
        "score": 18,
        "tier": "flagship-lite",
        "antutu": 630000,
        "label": "⚡ SD 865",
    },
    "snapdragon 860": {
        "score": 17,
        "tier": "flagship-lite",
        "antutu": 600000,
        "label": "⚡ SD 860",
    },
    # === QUALCOMM SNAPDRAGON (7-series upper mid-range) ===
    "snapdragon 7+ gen 3": {
        "score": 24,
        "tier": "mid-flagship",
        "antutu": 950000,
        "label": "⚡ SD 7+ Gen 3",
    },
    "snapdragon 7 gen 3": {
        "score": 23,
        "tier": "mid-flagship",
        "antutu": 900000,
        "label": "⚡ SD 7 Gen 3",
    },
    "snapdragon 7+ gen 2": {
        "score": 21,
        "tier": "mid-flagship",
        "antutu": 850000,
        "label": "⚡ SD 7+ Gen 2",
    },
    "snapdragon 778g+": {"score": 18, "tier": "mid", "antutu": 570000, "label": "⚡ SD 778G+"},
    "snapdragon 778g": {"score": 17, "tier": "mid", "antutu": 550000, "label": "⚡ SD 778G"},
    "snapdragon 695": {"score": 14, "tier": "mid", "antutu": 400000, "label": "⚡ SD 695 (5G)"},
    "snapdragon 680": {"score": 12, "tier": "mid", "antutu": 280000, "label": "⚡ SD 680"},
    # === QUALCOMM SNAPDRAGON (4/6-series budget) ===
    "snapdragon 4 gen 2": {
        "score": 10,
        "tier": "budget-mid",
        "antutu": 330000,
        "label": "⚡ SD 4 Gen 2",
    },
    "snapdragon 685": {"score": 11, "tier": "mid", "antutu": 290000, "label": "⚡ SD 685"},
    # === MEDIATEK DIMENSITY (Flagship) ===
    "dimensity 9300": {
        "score": 29,
        "tier": "flagship-ultra",
        "antutu": 1850000,
        "label": "⚡ Dimensity 9300",
    },
    "dimensity 9200": {
        "score": 27,
        "tier": "flagship",
        "antutu": 1300000,
        "label": "⚡ Dimensity 9200",
    },
    "dimensity 9000": {
        "score": 25,
        "tier": "flagship",
        "antutu": 1000000,
        "label": "⚡ Dimensity 9000",
    },
    "dimensity 8300": {
        "score": 22,
        "tier": "mid-flagship",
        "antutu": 920000,
        "label": "⚡ Dimensity 8300",
    },
    "dimensity 8200": {
        "score": 21,
        "tier": "mid-flagship",
        "antutu": 880000,
        "label": "⚡ Dimensity 8200",
    },
    "dimensity 8100": {
        "score": 20,
        "tier": "mid-flagship",
        "antutu": 820000,
        "label": "⚡ Dimensity 8100",
    },
    "dimensity 7200": {"score": 17, "tier": "mid", "antutu": 650000, "label": "⚡ Dimensity 7200"},
    "dimensity 7020": {"score": 14, "tier": "mid", "antutu": 380000, "label": "⚡ Dimensity 7020"},
    # === MEDIATEK HELIO (Budget/Mid) ===
    "helio g99": {"score": 12, "tier": "mid", "antutu": 380000, "label": "⚡ Helio G99"},
    "helio g96": {"score": 11, "tier": "budget-mid", "antutu": 330000, "label": "⚡ Helio G96"},
    "helio g88": {"score": 10, "tier": "budget-mid", "antutu": 290000, "label": "⚡ Helio G88"},
    "helio g85": {"score": 8, "tier": "budget-mid", "antutu": 220000, "label": "⚡ Helio G85"},
    "helio g36": {"score": 5, "tier": "budget", "antutu": 120000, "label": "⚡ Helio G36"},
    # === APPLE A-SERIES (iPhone) ===
    "a17 pro": {
        "score": 30,
        "tier": "flagship-ultra",
        "antutu": 1900000,
        "label": "⚡ A17 Pro (iPhone 15 Pro)",
    },
    "a16 bionic": {
        "score": 28,
        "tier": "flagship",
        "antutu": 1400000,
        "label": "⚡ A16 Bionic (iPhone 14 Pro)",
    },
    "a15 bionic": {
        "score": 26,
        "tier": "flagship",
        "antutu": 1100000,
        "label": "⚡ A15 Bionic (iPhone 13 Pro)",
    },
    "a14 bionic": {
        "score": 22,
        "tier": "flagship-lite",
        "antutu": 800000,
        "label": "⚡ A14 Bionic (iPhone 12)",
    },
    "a13 bionic": {
        "score": 19,
        "tier": "flagship-lite",
        "antutu": 650000,
        "label": "⚡ A13 Bionic (iPhone 11)",
    },
    # === SAMSUNG EXYNOS ===
    "exynos 2400": {"score": 27, "tier": "flagship", "antutu": 1350000, "label": "⚡ Exynos 2400"},
    "exynos 2200": {"score": 24, "tier": "flagship", "antutu": 950000, "label": "⚡ Exynos 2200"},
    "exynos 2100": {
        "score": 21,
        "tier": "flagship-lite",
        "antutu": 720000,
        "label": "⚡ Exynos 2100",
    },
    "exynos 1380": {
        "score": 16,
        "tier": "mid-flagship",
        "antutu": 570000,
        "label": "⚡ Exynos 1380",
    },
    # === GOOGLE TENSOR ===
    "tensor g4": {
        "score": 25,
        "tier": "flagship",
        "antutu": 1100000,
        "label": "⚡ Tensor G4 (Pixel 9)",
    },
    "tensor g3": {
        "score": 24,
        "tier": "flagship",
        "antutu": 1050000,
        "label": "⚡ Tensor G3 (Pixel 8)",
    },
    "tensor g2": {
        "score": 21,
        "tier": "flagship-lite",
        "antutu": 850000,
        "label": "⚡ Tensor G2 (Pixel 7)",
    },
    "tensor": {
        "score": 19,
        "tier": "flagship-lite",
        "antutu": 750000,
        "label": "⚡ Tensor (Pixel 6)",
    },
}

# Fallback scores by tier when processor not explicitly detected
PROCESSOR_TIER_DEFAULTS = {
    "flagship-ultra": 28,
    "flagship+": 26,
    "flagship": 24,
    "flagship-lite": 20,
    "mid-flagship": 18,
    "mid": 12,
    "budget-mid": 8,
    "budget": 4,
}

# Detection patterns for processor names
PROCESSOR_PATTERNS = [
    r"snapdragon\s*(\d+)\s*(gen\s*\d+|\+)?",
    r"dimensity\s*(\d+)",
    r"helio\s*([a-z]\d+)",
    r"a(\d{1,2})\s*(bionic|pro)?",
    r"exynos\s*(\d+)",
    r"tensor\s*(g\d+)?",
    r"sd\s*(\d+)\s*gen\s*(\d+)",  # Abbreviated "SD 8 Gen 2"
    r"sd\s*(\d+)",  # "SD 888"
]

# =============================================================================
# BATTERY HEALTH SCORING (-30 to +20 points) 🆕 NEW
# =============================================================================
# Battery replacement costs 10k-30k KZT, major factor for buyers
# Many sellers mention battery percentage in descriptions

BATTERY_HEALTH_SCORING = [
    {"min_health": 95, "points": 20, "label": "🔋 Excellent battery (95%+)"},
    {"min_health": 90, "points": 15, "label": "🔋 Great battery (90-94%)"},
    {"min_health": 85, "points": 10, "label": "🔋 Good battery (85-89%)"},
    {"min_health": 80, "points": 5, "label": "🔋 Decent battery (80-84%)"},
    {"min_health": 70, "points": 0, "label": "🔋 Acceptable battery (70-79%)"},
    {"min_health": 60, "points": -10, "label": "⚠️ Degraded battery (60-69%)"},
    {"min_health": 0, "points": -30, "label": "⚠️ Poor battery (<60%)"},
]

# Battery health detection keywords (Russian + English)
BATTERY_KEYWORDS = {
    # Explicit percentage patterns (regex)
    "health_percentage": [
        r"battery\s*health\s*:?\s*(\d+)",
        # Word endings: "аккумулятора 78%", "батарейка 100%", "состояние батареи 85"
        r"(?:акб|akb|ёмкост\w*|емкост\w*|аккумулятор\w*|батаре\w*)\s*:?\s*(\d+)",
        r"(\d+)\s*%\s*(?:акб|akb|батаре|аккум|ёмкост|емкост)",
    ],
    # Positive keywords (battery replaced/excellent)
    "positive": [
        "новая батарея",
        "new battery",
        "заменена батарея",
        "replaced battery",
        "батарея заменена",
        "battery replaced",
        "свежая батарея",
        "fresh battery",
        "идеальная батарея",
        "perfect battery",
        "отличная батарея",
    ],
    # Negative keywords (battery issues)
    "negative": [
        "слабая батарея",
        "weak battery",
        "быстро разряжается",
        "drains fast",
        "не держит",
        "плохо держит",
        "поменять батар",
        "поменять акб",
        "заменить батар",
        "заменить акб",
        "батарейка тез",
        "doesn't hold",
        "батарея умерла",
        "battery dead",
        "требует замены",
        "needs replacement",
        "плохая батарея",
        "poor battery",
        "батарея не держит",
        "износ батареи",
        "battery wear",
    ],
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def normalize_text(text: str) -> str:
    """
    Normalize text for better typo handling

    Handles:
    - Multiple spaces
    - Latin/Cyrillic confusion (e.g., 'a' vs 'а', 'o' vs 'о')
    - Common punctuation issues

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Convert to lowercase
    normalized = text.lower().strip()

    # Replace multiple spaces with single space
    normalized = " ".join(normalized.split())

    # Remove excessive punctuation
    normalized = normalized.replace("!!!", "!").replace("???", "?")

    # TODO: Add Latin/Cyrillic confusion handling if needed
    # Examples: 'a' vs 'а', 'o' vs 'о', 'e' vs 'е'
    # Note: Be careful not to break real English words

    return normalized


def get_discount_score(discount_percent):
    """Calculate score based on discount percentage"""
    for threshold in DISCOUNT_THRESHOLDS:
        if discount_percent >= threshold["min"]:
            return threshold["points"], f"{threshold['label']}! {discount_percent:.0f}% off"
    return 0, None


def get_age_score(release_year):
    """Calculate score based on phone age"""
    age = CURRENT_YEAR - release_year
    for age_rule in AGE_SCORING:
        if age <= age_rule["max_age"]:
            return age_rule["points"], age_rule["label"]
    return 0, None


def get_tier_score(tier):
    """Get score for phone tier"""
    return TIER_SCORES.get(tier, 0)


def get_storage_score(  # noqa: PLR0912
    title_lower: str, specs: dict[str, Any] | None = None
) -> tuple[int, str | None]:
    """
    Calculate storage bonus

    🆕 NEW Phase 3: Now uses Kimovil specs for 100% accuracy!

    Args:
        title_lower: Lowercase title (fallback)
        specs: Optional Kimovil specs dict (contains storage_variants)

    Returns:
        tuple: (points, label)
    """

    # 🆕 PHASE 3: Use Kimovil specs if available
    if specs:
        storage_variants: Any = specs.get("storage_variants")
        if storage_variants:
            try:
                # Parse JSON array [256, 512, 1024]
                storage_list: list[int] = []
                if isinstance(storage_variants, str):
                    parsed = json.loads(storage_variants)
                    storage_list = parsed if isinstance(parsed, list) else []
                elif isinstance(storage_variants, list):
                    storage_list = [int(x) for x in storage_variants if isinstance(x, (int, str))]
                else:
                    storage_list = []

                # Get max storage
                max_storage: int = max(storage_list) if storage_list else 0

                # Score based on max storage
                for storage in STORAGE_BONUS:
                    if not isinstance(storage, dict):
                        continue
                    keywords_any = storage.get("keywords", [])
                    if isinstance(keywords_any, list) and keywords_any:
                        first_kw_any = keywords_any[0]
                        first_kw = str(first_kw_any)
                    else:
                        first_kw = str(keywords_any) if keywords_any is not None else "0"

                    storage_value = int("".join(c for c in first_kw if c.isdigit()) or "0")

                    if max_storage >= storage_value:
                        spec_points_any = storage.get("points", 0)
                        # coerce via str() so mypy matches int(str) overload
                        try:
                            spec_points = int(str(spec_points_any))
                        except (ValueError, TypeError):
                            spec_points = 0
                        spec_label_any = storage.get("label", "")
                        spec_label = (
                            spec_label_any
                            if isinstance(spec_label_any, str)
                            else str(spec_label_any or "")
                        )
                        return spec_points, f"{spec_label} (from specs)"
            except (json.JSONDecodeError, ValueError, TypeError):
                pass  # Fall through to text parsing

        # Fallback: Parse from title
    for storage in STORAGE_BONUS:
        if not isinstance(storage, dict):
            continue
        keywords_list_any = storage.get("keywords", [])
        if isinstance(keywords_list_any, list) and any(
            isinstance(kw, str) and kw in title_lower for kw in keywords_list_any
        ):
            fallback_points_any = storage.get("points", 0)
            try:
                fallback_points = int(str(fallback_points_any))
            except (ValueError, TypeError):
                fallback_points = 0
            fallback_label_any = storage.get("label", "")
            fallback_label = (
                fallback_label_any
                if isinstance(fallback_label_any, str)
                else str(fallback_label_any or "")
            )
            return fallback_points, fallback_label
    return 0, None


def get_ram_score(title_lower: str, specs: dict[str, Any] | None = None) -> tuple[int, str | None]:  # noqa: PLR0912
    """
    Calculate RAM bonus

    🆕 NEW Phase 3: Now uses Kimovil specs for 100% accuracy!

    Args:
        title_lower: Lowercase title (fallback)
        specs: Optional Kimovil specs dict (contains ram_variants)

    Returns:
        tuple: (points, label)
    """

    # 🆕 PHASE 3: Use Kimovil specs if available
    if specs:
        ram_variants: Any = specs.get("ram_variants")
        if ram_variants:
            try:
                # Parse JSON array [8, 12, 16]
                ram_list: list[int] = []
                if isinstance(ram_variants, str):
                    parsed = json.loads(ram_variants)
                    ram_list = parsed if isinstance(parsed, list) else []
                elif isinstance(ram_variants, list):
                    ram_list = [int(x) for x in ram_variants if isinstance(x, (int, str))]
                else:
                    ram_list = []

                # Get max RAM
                max_ram: int = max(ram_list) if ram_list else 0

                # Score based on max RAM
                for ram in RAM_BONUS:
                    if not isinstance(ram, dict):
                        continue
                    label_any = ram.get("label", "")
                    label_str = str(label_any)
                    ram_value = int("".join(c for c in label_str if c.isdigit()) or "0")

                    if max_ram >= ram_value:
                        spec_points_any = ram.get("points", 0)
                        try:
                            spec_points = int(str(spec_points_any))
                        except (ValueError, TypeError):
                            spec_points = 0
                        return spec_points, f"{label_str} (from specs)"
            except (json.JSONDecodeError, ValueError, TypeError):
                pass  # Fall through to text parsing

        # Fallback: Parse from title
    for ram in RAM_BONUS:
        if not isinstance(ram, dict):
            continue
        patterns_any = ram.get("patterns", [])
        if not isinstance(patterns_any, list):
            continue
        for pattern in patterns_any:
            if not isinstance(pattern, str):
                continue
            if re.search(pattern, title_lower):
                fallback_points_any = ram.get("points", 0)
                try:
                    fallback_points = int(str(fallback_points_any))
                except (ValueError, TypeError):
                    fallback_points = 0
                fallback_label_any = ram.get("label", "")
                fallback_label = (
                    fallback_label_any
                    if isinstance(fallback_label_any, str)
                    else str(fallback_label_any or "")
                )
                return fallback_points, fallback_label
    return 0, None


def get_price_range_score(price):
    """Calculate price range bonus"""
    for price_rule in PRICE_RANGE_SCORING:
        if price <= price_rule["max_price"]:
            return price_rule["points"], price_rule["label"]
    return 0, None


def _check_positive_condition(desc_lower: str) -> tuple[int, list[str]]:
    """Check positive condition keywords (only first match applies)"""
    for condition in CONDITION_POSITIVE:
        if any(kw in desc_lower for kw in condition["keywords"]):
            return condition["points"], [condition["label"]]
    return 0, []


def _check_negative_conditions(desc_lower: str) -> tuple[int, list[str]]:
    """Check negative condition keywords (multiple can apply)"""
    score = 0
    factors = []
    for condition in CONDITION_NEGATIVE:
        if any(kw in desc_lower for kw in condition["keywords"]):
            score += condition["points"]
            factors.append(condition["label"])
    return score, factors


def _check_missing_components(desc_lower: str) -> tuple[int, list[str]]:
    """Check for missing components"""
    score = 0
    factors = []
    for missing in MISSING_COMPONENTS:
        if any(kw in desc_lower for kw in missing["keywords"]):
            score += missing["points"]
            factors.append(missing["label"])
    return score, factors


def _check_urgency(desc_lower: str) -> tuple[int, list[str]]:
    """Check for urgency keywords"""
    if any(kw in desc_lower for kw in URGENCY_KEYWORDS):
        return URGENCY_BONUS, [URGENCY_LABEL]
    return 0, []


def get_condition_score(description):
    """
    Calculate condition score from description

    Args:
        description: Phone description text (Russian/English/Kazakh)

    Returns:
        tuple: (total_score, list of factor labels)

    Note: Uses normalize_text() to handle typos and formatting issues
    """
    if not description:
        return 0, []

    # Normalize text for better typo handling
    try:
        desc_lower = normalize_text(description)
    except Exception:
        # Fallback to simple lowercase if normalization fails
        desc_lower = str(description).lower().strip() if description else ""

    total_score = 0
    all_factors = []

    # Check all condition types
    try:
        pos_score, pos_factors = _check_positive_condition(desc_lower)
        neg_score, neg_factors = _check_negative_conditions(desc_lower)
        miss_score, miss_factors = _check_missing_components(desc_lower)
        urg_score, urg_factors = _check_urgency(desc_lower)

        # "Отличное, не считая полосы на экране" is not excellent: defects cancel the praise
        if neg_factors:
            pos_score, pos_factors = 0, []

        total_score = pos_score + neg_score + miss_score + urg_score
        all_factors = pos_factors + neg_factors + miss_factors + urg_factors
    except Exception as e:
        # Log error but don't crash
        logging.warning(f"Error in condition scoring: {e}")
        return 0, []

    return total_score, all_factors


def get_brand_score(brand):
    """Get brand reputation score"""
    return BRAND_SCORES.get(brand, DEFAULT_BRAND_SCORE)


def get_camera_score(model_name, tier=None):
    """
    Get camera score for a phone model

    Args:
        model_name: Normalized model name (e.g., 'samsung s24 ultra')
        tier: Phone tier for fallback scoring

    Returns:
        tuple: (score, label) or (0, None) if not found
    """
    model_lower = model_name.lower() if model_name else ""

    # No model: "" would partial-match every key, so skip the table and use the tier default
    table = CAMERA_SCORES if model_lower else {}

    # Check for exact match
    if model_lower in table:
        camera_data = table[model_lower]
        return camera_data["score"], camera_data["label"]

    # Check for partial match (e.g., "s24 ultra" matches "samsung s24 ultra")
    for camera_model, camera_data in table.items():
        if camera_model in model_lower or model_lower in camera_model:
            return camera_data["score"], camera_data["label"]

    # Fallback to tier-based scoring
    if tier and tier in CAMERA_TIER_DEFAULTS:
        score = CAMERA_TIER_DEFAULTS[tier]
        label = f"📸 {tier.replace('-', ' ').title()} camera"
        return score, label

    return 0, None


def get_dxomark_score(model_name):
    """
    Get DXOMark score for a phone model (for display purposes)

    Args:
        model_name: Normalized model name

    Returns:
        int: DXOMark score or None
    """
    model_lower = model_name.lower() if model_name else ""
    if not model_lower:
        return None

    if model_lower in CAMERA_SCORES:
        return CAMERA_SCORES[model_lower]["dxomark"]

    for camera_model, camera_data in CAMERA_SCORES.items():
        if camera_model in model_lower or model_lower in camera_model:
            return camera_data["dxomark"]

    return None


def get_processor_score(
    title: str, tier: str | None = None, specs: dict[str, Any] | None = None
) -> tuple[int, str | None]:
    """
    Get processor score from phone title or specs

    🆕 NEW Phase 3: Now uses Kimovil specs for 100% accuracy!

    Args:
        title: Phone title (may contain processor name, fallback)
        tier: Phone tier for fallback scoring
        specs: Optional Kimovil specs dict (contains processor_chipset)

    Returns:
        tuple: (score, label) or (0, None) if not found
    """
    # 🆕 PHASE 3: Use Kimovil specs if available
    if specs:
        processor_chipset = (specs.get("processor_chipset") or "").lower()
        if processor_chipset:
            # Check for exact processor match in specs
            for proc_name, proc_data in PROCESSOR_SCORES.items():
                if proc_name in processor_chipset:
                    return cast(int, proc_data["score"]), f"{proc_data['label']} (from specs)"

    # Fallback: Parse from title
    if not title or title is None:
        if tier and tier in PROCESSOR_TIER_DEFAULTS:
            score: int = PROCESSOR_TIER_DEFAULTS[tier]
            label: str = f"⚡ {tier.replace('-', ' ').title()} processor (estimated)"
            return score, label
        return 0, None

    title_lower = str(title).lower()

    # Check for exact processor match in title
    for proc_name, proc_data in PROCESSOR_SCORES.items():
        if proc_name in title_lower:
            # Use cast to satisfy type checker
            return cast(int, proc_data["score"]), cast(str, proc_data["label"])

    # Fallback to tier-based estimation
    if tier and tier in PROCESSOR_TIER_DEFAULTS:
        score = PROCESSOR_TIER_DEFAULTS[tier]
        label = f"⚡ {tier.replace('-', ' ').title()} processor (estimated)"
        return int(score), label

    return 0, None


# ponytail: a bare 50-100% in a TITLE ("Iphone 12 128gb 78%") is nearly always battery health;
# in descriptions it's "оригинал 100%", "сенсор работает на 100%", so titles only
TITLE_BATTERY_PERCENT = r"\b([5-9]\d|100)\s*%"


def get_battery_health_score(  # noqa: PLR0912
    description: str, specs: dict[str, Any] | None = None, title: str = ""
) -> tuple[int, str | None]:
    """
    Extract and score battery health from description or specs

    🆕 NEW Phase 3: Now uses Kimovil specs to get battery capacity!

    Args:
        description: Listing description (Russian/English, fallback)
        specs: Optional Kimovil specs dict (contains battery_capacity)

    Returns:
        tuple: (score, label) or (0, None) if no info found
    """
    # 🆕 PHASE 3: Use Kimovil specs to bonus for large batteries
    if specs:
        battery_capacity = specs.get("battery_capacity", 0)
        if battery_capacity and battery_capacity >= constants.BATTERY_CAPACITY:
            # Bonus points for large batteries (5000mAh+)
            # Still check description for health percentage, but add capacity bonus
            pass  # Continue to description checks below

    if not description and not title:
        return 0, None

    try:
        # Normalize text for better detection
        desc_lower = normalize_text(description)
    except Exception:
        desc_lower = str(description).lower().strip() if description else ""

    # Check for explicit battery percentage
    try:
        sources = [(p, desc_lower) for p in BATTERY_KEYWORDS["health_percentage"]]
        sources.append((TITLE_BATTERY_PERCENT, title.lower()))
        for pattern, text in sources:
            match = re.search(pattern, text)
            if match:
                try:
                    health_pct = int(match.group(1))
                    # Validate reasonable range
                    if 0 <= health_pct <= 100:  # noqa: PLR2004
                        for threshold in BATTERY_HEALTH_SCORING:
                            # Use cast to satisfy type checker
                            min_health = cast(int, threshold["min_health"])
                            if health_pct >= min_health:
                                return cast(int, threshold["points"]), cast(str, threshold["label"])
                except (ValueError, IndexError, AttributeError):
                    continue
    except Exception:
        pass  # Continue to keyword checks

    # Check for positive keywords (battery replaced/excellent)
    try:
        if any(kw in desc_lower for kw in BATTERY_KEYWORDS["positive"]):
            return 15, "🔋 Battery replaced/excellent"
    except Exception:
        pass

    # Check for negative keywords (battery issues)
    try:
        if any(kw in desc_lower for kw in BATTERY_KEYWORDS["negative"]):
            return -15, "⚠️ Battery issues mentioned"
    except Exception:
        pass

    # No battery info found
    return 0, None


# =============================================================================
# VALIDATION FUNCTIONS - NEW (from unknown.json analysis)
# =============================================================================


def validate_discount_realism(
    current_price: int, discount_pct: float, tier: str | None = None
) -> tuple[float, str | None]:
    """
    Validate if discount percentage is realistic and adjust if suspicious

    Args:
        current_price: Current listing price (KZT)
        discount_pct: Calculated discount percentage
        tier: Phone tier (optional)

    Returns:
        tuple: (adjusted_discount_pct, warning_message)

    Rules:
    - Budget phones (<60k) with 80%+ discount = likely inflated market price
    - Flagship phones (>200k) with 80%+ discount = suspicious (maybe broken)
    - Discount > 85% = almost always unrealistic
    """
    warning = None
    adjusted_discount = discount_pct

    # Rule 1: Budget phone with extreme discount = inflated market price
    if current_price < constants.PRICE_RANGE_60K and discount_pct > constants.PERCENT_80:
        # Likely market price is wrong (e.g., Redmi 13C: 35k from "320k")
        adjusted_discount = discount_pct * 0.65  # Apply 35% penalty
        warning = (
            f"⚠️ Suspicious: Budget phone ({current_price:,} KZT) claiming {discount_pct:.0f}% off"
        )

    # Rule 2: Any phone with 85%+ discount = extremely suspicious
    elif discount_pct > 85:  # noqa: PLR2004
        adjusted_discount = min(
            discount_pct * 0.70, constants.PERCENT_80
        )  # Cap at 80% with penalty
        warning = (
            f"⚠️ Unrealistic: {discount_pct:.0f}% discount adjusted to {adjusted_discount:.0f}%"
        )

    # Rule 3: Flagship with 80%+ discount but low price = likely broken
    elif (
        tier in ["flagship", "flagship-ultra", "flagship+"]
        and discount_pct > constants.PERCENT_80
        and current_price < constants.PRICE_RANGE_100K
    ):
        # This might be legit but risky
        warning = f"⚠️ Caution: Flagship at {current_price:,} KZT with {discount_pct:.0f}% off (check condition!)"

    return adjusted_discount, warning


def check_price_tier_consistency(price: int, tier: str) -> tuple[int, str | None]:
    """
    Check if price matches expected tier and return penalty/bonus

    Args:
        price: Current price (KZT)
        tier: Phone tier

    Returns:
        tuple: (score_adjustment, warning_message)

    Expected price ranges (used, Kazakhstan market):
    - flagship-ultra: 250k-500k
    - flagship: 150k-350k
    - mid-flagship: 100k-200k
    - mid: 50k-120k
    - budget-mid: 30k-70k
    - budget: 20k-50k
    """
    adjustment = 0
    warning = None

    tier_price_ranges = {
        "flagship-ultra": (250000, 500000),
        "flagship+": (200000, 400000),
        "flagship": (150000, 350000),
        "flagship-lite": (120000, 250000),
        "mid-flagship": (100000, 200000),
        "mid": (50000, 120000),
        "budget-mid": (30000, 70000),
        "budget": (20000, 50000),
    }

    if tier not in tier_price_ranges:
        return 0, None

    min_price, max_price = tier_price_ranges[tier]

    # Price too low for tier = suspicious (broken?) or wrong tier
    if price < min_price * 0.5:  # More than 50% below expected
        adjustment = -15
        warning = f"⚠️ Price {price:,} KZT too low for {tier} (expected {min_price:,}-{max_price:,})"

    # Price too high for tier = overpriced or wrong tier
    elif price > max_price * 1.3:  # More than 30% above expected
        adjustment = -10
        warning = (
            f"⚠️ Price {price:,} KZT too high for {tier} (expected {min_price:,}-{max_price:,})"
        )

    # Perfect price range = bonus
    elif min_price <= price <= max_price:
        adjustment = 3

    return adjustment, warning


def detect_market_price_issues(
    phone_title: str, market_price: int, current_price: int
) -> tuple[bool, str | None]:
    """
    Detect if market price seems inflated or incorrect

    Args:
        phone_title: Phone title/model
        market_price: Market price from database
        current_price: Current listing price

    Returns:
        tuple: (is_suspicious, reason)

    Heuristics:
    - If market_price > current_price * 5 = probably wrong (e.g., 35k vs 320k)
    - Budget model names with flagship prices = wrong data
    """
    title_lower = str(phone_title).lower() if phone_title else ""

    # Check for budget model names with high market prices
    budget_keywords = ["redmi 12c", "redmi 13c", "poco c", "samsung a0", "samsung a1", "samsung a2"]
    is_budget_model = any(kw in title_lower for kw in budget_keywords)

    # Rule 1: Market price more than 5x current price = suspicious
    if market_price > current_price * 5:
        ratio = market_price / current_price
        return (
            True,
            f"Market price {market_price:,} is {ratio:.1f}x current price {current_price:,}",
        )

    # Rule 2: Budget model with flagship price = wrong data
    if is_budget_model and market_price > constants.PRICE_RANGE_150K:
        return True, f"Budget model '{phone_title}' has flagship price {market_price:,}"

    return False, None


# =============================================================================
# 🆕 DISPLAY QUALITY SCORING (0-20 points) - NEW Phase 2
# =============================================================================
# Display tech matters: AMOLED > IPS LCD, high refresh rate is premium

DISPLAY_SCORING: list[DisplayScoringItem] = [
    # AMOLED/OLED variants (best)
    {
        "keywords": ["amoled", "super amoled", "dynamic amoled", "супер амолед"],
        "points": 12,
        "label": "📱 AMOLED display",
    },
    {"keywords": ["oled", "олед"], "points": 11, "label": "📱 OLED display"},
    {"keywords": ["ltpo", "лтпо"], "points": 10, "label": "📱 LTPO display (adaptive)"},
    # IPS LCD (mid-tier)
    {"keywords": ["ips", "lcd", "ипс", "лсд"], "points": 5, "label": "📱 IPS LCD display"},
    # TFT (basic)
    {"keywords": ["tft", "тфт"], "points": 2, "label": "📱 TFT display"},
]

# Refresh rate bonus (additively stacks with display type)
REFRESH_RATE_BONUS: list[DisplayScoringItem] = [
    {"keywords": ["165hz", "165 hz", "165гц"], "points": 8, "label": "⚡ 165Hz refresh"},
    {"keywords": ["144hz", "144 hz", "144гц"], "points": 7, "label": "⚡ 144Hz refresh"},
    {"keywords": ["120hz", "120 hz", "120гц"], "points": 6, "label": "⚡ 120Hz refresh"},
    {"keywords": ["90hz", "90 hz", "90гц"], "points": 3, "label": "⚡ 90Hz refresh"},
]


def get_display_score(
    title: str, description: str, specs: dict[str, Any] | None = None
) -> tuple[int, list[str]]:
    """
    Calculate display quality score based on panel type and refresh rate

    🆕 NEW Phase 3: Now uses Kimovil specs for 100% accuracy!

    Args:
        title: Phone title
        description: Full listing description
        specs: Optional Kimovil specs dict (contains display_type, display_refresh_rate)

    Returns:
        tuple: (total_points, list_of_labels)

    Algorithm:
    - Check display tech (AMOLED/OLED/IPS/TFT) - up to 12 points
    - Check refresh rate (90/120/144/165 Hz) - up to 8 points
    - Max total: 20 points

    Examples:
    - "AMOLED 120Hz" → 18 points
    - "IPS 90Hz" → 8 points
    - "OLED" (no refresh rate) → 11 points
    """
    score = 0
    labels = []

    # 🆕 PHASE 3: Use Kimovil specs if available (100% accurate!)
    if specs:
        display_type = (specs.get("display_type") or "").lower()
        refresh_rate = specs.get("display_refresh_rate") or 0

        # Check display tech from specs
        if display_type:
            for display in DISPLAY_SCORING:
                keywords = display["keywords"]
                if keywords and any(str(kw) in display_type for kw in keywords):
                    score += display["points"]
                    labels.append(f"{display['label']} (from specs)")
                    break

        # Check refresh rate from specs
        if refresh_rate and refresh_rate >= constants.HZ_90:
            for rate in REFRESH_RATE_BONUS:
                # Extract numeric value from keywords (e.g., "120hz" -> 120)
                rate_keywords = rate["keywords"]
                if rate_keywords:
                    first_keyword = str(rate_keywords[0])
                    rate_value = int("".join(filter(str.isdigit, first_keyword)) or "0")
                    if refresh_rate >= rate_value:
                        score += rate["points"]
                        labels.append(f"{rate['label']} (from specs)")
                        break

        return score, labels

    # Fallback: Parse from title/description (less accurate)
    title_str = str(title) if title else ""
    description_str = str(description) if description else ""
    text = f"{title_str} {description_str}".lower()

    # Check display tech
    for display in DISPLAY_SCORING:
        keywords = display["keywords"]
        if keywords and any(str(kw) in text for kw in keywords):
            score += display["points"]
            labels.append(display["label"])
            break  # Only match one display type

    # Check refresh rate (additive)
    for rate in REFRESH_RATE_BONUS:
        keywords = rate["keywords"]
        if keywords and any(str(kw) in text for kw in keywords):
            score += rate["points"]
            labels.append(rate["label"])
            break  # Only match one refresh rate

    return score, labels


# =============================================================================
# 🆕 WARRANTY & SELLER SCORING (0-10 points) - NEW Phase 2
# =============================================================================
# Official stores, warranties, and authorized sellers add trust and value

WARRANTY_SCORING: list[WarrantyScoringItem] = [
    # Warranty indicators
    {
        "keywords": ["гарантия 2 года", "2 года гарантии", "2 year warranty"],
        "points": 6,
        "label": "🛡️ 2-year warranty",
    },
    {
        "keywords": ["гарантия 1 год", "год гарантии", "1 year warranty", "гарантия"],
        "points": 4,
        "label": "🛡️ 1-year warranty",
    },
    {
        "keywords": ["официальный магазин", "official store", "authorized dealer"],
        "points": 5,
        "label": "🏪 Official store",
    },
    {
        "keywords": ["с чеком", "чек есть", "receipt included", "с документами"],
        "points": 3,
        "label": "📄 Receipt included",
    },
]

# Negative signals (reduce score)
WARRANTY_NEGATIVE: list[WarrantyNegativeItem] = [
    {
        "keywords": ["без гарантии", "no warranty", "гарантии нет"],
        "penalty": 0,
        "label": None,
    },  # No penalty for private sellers
    {
        "keywords": ["на запчасти", "for parts", "не работает", "broken"],
        "penalty": 5,
        "label": "⚠️ Sold as-is/parts",
    },
]


def get_warranty_score(title: str, description: str) -> tuple[int, list[str]]:
    """
    Calculate warranty/seller trust score

    Args:
        title: Phone title
        description: Full listing description

    Returns:
        tuple: (total_points, list_of_labels)

    Algorithm:
    - Check warranty indicators (0-6 points)
    - Check seller type (0-5 points)
    - Apply penalties if broken/parts (-5 points)
    - Max total: 10 points

    Examples:
    - "Official store, 2 years warranty" → 11 points (capped at 10)
    - "With receipt" → 3 points
    - "For parts" → -5 points
    """
    title_str = str(title) if title else ""
    description_str = str(description) if description else ""
    text = f"{title_str} {description_str}".lower()
    score = 0
    labels = []

    # Check positive signals
    for item in WARRANTY_SCORING:
        keywords = item["keywords"]
        if keywords and any(str(kw) in text for kw in keywords):
            score += item["points"]
            labels.append(item["label"])

    # Check negative signals
    for neg_item in WARRANTY_NEGATIVE:
        keywords = neg_item["keywords"]
        if keywords and any(str(kw) in text for kw in keywords):
            score -= neg_item["penalty"]
            label = neg_item["label"]
            if label:
                labels.append(label)

    # Cap at 10 points max
    score = min(score, 10)

    return int(score), labels
