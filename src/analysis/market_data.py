#!/usr/bin/env python3
"""
Market Price Database for Phone Models
======================================
This file contains initial retail prices, release years, and tier classifications
for various phone models. Used for calculating value scores and discounts.

Format:
    'model_name': {
        'initial': original_price_in_KZT,
        'year': release_year,
        'tier': 'flagship' | 'mid-flagship' | 'mid' | 'budget-mid' | 'budget'
    }

TODO:
- Replace with real-time API (publicapi.dev/phone-specification-api)
- Add PhoneDB.net integration
- Add more models from e-commerce sites
"""

# Conversion rates 29.10.2025
USDTOKZT_RATE = 533.51
EURTOKZT_RATE = 621.60

# Market price database (approximate initial prices in KZT)
MARKET_PRICES = {
    # =============================================================================
    # SAMSUNG
    # =============================================================================
    # Samsung Flagships (S Series)
    # S25 series (2025)
    "samsung s25": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2025,
        "tier": "flagship",
    },
    "samsung s25+": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2025,
        "tier": "flagship+",
    },
    "samsung s25 ultra": {
        "initial": round(1299 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1299,
        "year": 2025,
        "tier": "flagship-ultra",
    },
    "samsung s25 fe": {
        "initial": round(649 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 649,
        "year": 2025,
        "tier": "flagship-lite",
    },
    # S24 series (2024)
    "samsung s24": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2024,
        "tier": "flagship",
    },
    "samsung s24+": {
        "initial": round(999.99 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999.99,
        "year": 2024,
        "tier": "flagship+",
    },
    "samsung s24 ultra": {
        "initial": round(1269 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1269,
        "year": 2024,
        "tier": "flagship-ultra",
    },
    "samsung s24 fe": {
        "initial": round(649 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 649,
        "year": 2024,
        "tier": "flagship-lite",
    },
    "samsung s23": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2023,
        "tier": "flagship",
    },  # base S23 :contentReference[oaicite:1]{index=1}
    "samsung s23+": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2023,
        "tier": "flagship+",
    },  # S23+ :contentReference[oaicite:2]{index=2}
    "samsung s23 ultra": {
        "initial": round(1199 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1199,
        "year": 2023,
        "tier": "flagship-ultra",
    },  # S23 Ultra :contentReference[oaicite:3]{index=3}
    # S22 series
    "samsung s22": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2022,
        "tier": "flagship",
    },  # S22 base :contentReference[oaicite:4]{index=4}
    "samsung s22+": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2022,
        "tier": "flagship+",
    },  # S22+ :contentReference[oaicite:5]{index=5}
    "samsung s22 ultra": {
        "initial": round(1199 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1199,
        "year": 2022,
        "tier": "flagship-ultra",
    },  # S22 Ultra :contentReference[oaicite:6]{index=6}
    # S21 series
    "samsung s21": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2021,
        "tier": "flagship",
    },  # S21 base
    "samsung s21+": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2021,
        "tier": "flagship+",
    },  # S21+
    "samsung s21 ultra": {
        "initial": round(1199 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1199,
        "year": 2021,
        "tier": "flagship-ultra",
    },  # S21 Ultra
    "samsung s21 fe": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2022,
        "tier": "flagship-lite",
    },  # S21 FE
    "samsung s20": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2020,
        "tier": "flagship",
    },
    "samsung s20+": {
        "initial": round(1199 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1199,
        "year": 2020,
        "tier": "flagship+",
    },
    "samsung s20 ultra": {
        "initial": round(1399 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1399,
        "year": 2020,
        "tier": "flagship-ultra",
    },
    "samsung s10": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2019,
        "tier": "flagship",
    },
    "samsung s9": {
        "initial": round(719 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 719,
        "year": 2018,
        "tier": "flagship",
    },
    # Samsung Mid-range (A Series)
    "samsung a73": {
        "initial": round(449 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 449,
        "year": 2022,
        "tier": "mid",
    },
    "samsung a72": {
        "initial": round(379 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 379,
        "year": 2021,
        "tier": "mid",
    },
    "samsung a71": {
        "initial": round(369 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 369,
        "year": 2020,
        "tier": "mid",
    },
    "samsung a52": {
        "initial": round(349 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 349,
        "year": 2021,
        "tier": "mid",
    },
    "samsung a51": {
        "initial": round(279 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 279,
        "year": 2020,
        "tier": "mid",
    },
    # Source: https://news.samsung.com/de/zuwachs-fur-die-galaxy-a-serie-das-samsung-galaxy-a34-5g-und-galaxy-a54-5g-erweitern-die-galaxy-familie
    "samsung a54": {
        "initial": round(489 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 489,
        "year": 2023,
        "tier": "mid",
    },
    # Source: https://news.samsung.com/de/samsung-galaxy-a55-5g-und-galaxy-a35-5g-spannende-neuheiten-und-verbesserte-sicherheit
    "samsung a35": {
        "initial": round(379 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 379,
        "year": 2024,
        "tier": "mid",
    },
    # Source: https://news.samsung.com/at/samsung-bringt-ai-auf-die-neuen-modelle-der-a-serie
    "samsung a36": {
        "initial": round(379 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 379,
        "year": 2025,
        "tier": "mid",
    },
    "samsung a56": {
        "initial": round(479 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 479,
        "year": 2025,
        "tier": "mid",
    },
    "samsung a41": {
        "initial": round(249 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 249,
        "year": 2020,
        "tier": "budget-mid",
    },
    "samsung a32": {
        "initial": round(229 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 229,
        "year": 2021,
        "tier": "budget",
    },
    # =============================================================================
    # XIAOMI
    # =============================================================================
    # Xiaomi Flagships
    "xiaomi 15 ultra": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2025,
        "tier": "flagship-ultra",
    },
    "xiaomi 15 pro": {
        "initial": round(849 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 849,
        "year": 2025,
        "tier": "flagship",
    },
    "xiaomi 15": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2025,
        "tier": "flagship",
    },
    "xiaomi 14 ultra": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2024,
        "tier": "flagship-ultra",
    },
    "xiaomi 14": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2024,
        "tier": "flagship",
    },
    "xiaomi 13 ultra": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2023,
        "tier": "flagship-ultra",
    },
    "xiaomi 13": {
        "initial": round(599 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 599,
        "year": 2023,
        "tier": "flagship",
    },
    "xiaomi 12 ultra": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2022,
        "tier": "flagship-ultra",
    },
    "xiaomi 12": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2022,
        "tier": "flagship",
    },
    "xiaomi 12 pro": {
        "initial": round(849 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 849,
        "year": 2022,
        "tier": "flagship",
    },
    "xiaomi 11": {
        "initial": round(749 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 749,
        "year": 2021,
        "tier": "flagship",
    },
    # Redmi Note Series (Mid-range)
    "redmi note 14 pro": {
        "initial": round(329 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 329,
        "year": 2025,
        "tier": "mid",
    },
    "redmi note 14": {
        "initial": round(249 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 249,
        "year": 2025,
        "tier": "mid",
    },
    "redmi note 13 pro": {
        "initial": round(299 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 299,
        "year": 2024,
        "tier": "mid",
    },
    "redmi note 12 pro": {
        "initial": round(269 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 269,
        "year": 2023,
        "tier": "mid",
    },
    "redmi note 11 pro": {
        "initial": round(249 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 249,
        "year": 2022,
        "tier": "mid",
    },
    "redmi note 10 pro": {
        "initial": round(279 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 279,
        "year": 2021,
        "tier": "mid",
    },
    "redmi note 9 pro": {
        "initial": round(269 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 269,
        "year": 2020,
        "tier": "mid",
    },
    # Redmi Budget
    "redmi 13c": {
        "initial": round(149 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 149,
        "year": 2023,
        "tier": "budget",
    },
    "redmi 12c": {
        "initial": round(129 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 129,
        "year": 2022,
        "tier": "budget",
    },
    # =============================================================================
    # POCO
    # =============================================================================
    "poco f6": {
        "initial": round(549 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 549,
        "year": 2025,
        "tier": "mid-flagship",
    },
    "poco x6 pro": {
        "initial": round(329 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 329,
        "year": 2025,
        "tier": "mid",
    },
    "poco f5": {
        "initial": round(499 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 499,
        "year": 2023,
        "tier": "mid-flagship",
    },
    "poco f4": {
        "initial": round(399 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 399,
        "year": 2022,
        "tier": "mid-flagship",
    },
    "poco f3": {
        "initial": round(349 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 349,
        "year": 2021,
        "tier": "mid-flagship",
    },
    "poco x5 pro": {
        "initial": round(299 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 299,
        "year": 2023,
        "tier": "mid",
    },
    "poco x4 pro": {
        "initial": round(279 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 279,
        "year": 2022,
        "tier": "mid",
    },
    "poco x3 pro": {
        "initial": round(249 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 249,
        "year": 2021,
        "tier": "mid",
    },
    # =============================================================================
    # GOOGLE PIXEL
    # =============================================================================
    "pixel 10 pro": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2025,
        "tier": "flagship",
    },
    "pixel 10": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2025,
        "tier": "flagship",
    },
    "pixel 9 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2024,
        "tier": "flagship",
    },
    "pixel 9": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2024,
        "tier": "flagship",
    },
    "pixel 8 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2023,
        "tier": "flagship",
    },
    "pixel 8": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2023,
        "tier": "flagship",
    },
    "pixel 7 pro": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2022,
        "tier": "flagship",
    },
    "pixel 7": {
        "initial": round(599 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 599,
        "year": 2022,
        "tier": "flagship",
    },
    "pixel 6 pro": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2021,
        "tier": "flagship",
    },
    "pixel 6": {
        "initial": round(599 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 599,
        "year": 2021,
        "tier": "flagship",
    },
    "pixel 8a": {
        "initial": round(499 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 499,
        "year": 2024,
        "tier": "mid-flagship",
    },
    "pixel 6a": {
        "initial": round(449 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 449,
        "year": 2022,
        "tier": "mid-flagship",
    },
    # =============================================================================
    # ONEPLUS
    # =============================================================================
    "oneplus 13": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2025,
        "tier": "flagship",
    },
    "oneplus 13r": {
        "initial": round(599 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 599,
        "year": 2025,
        "tier": "mid-flagship",
    },
    "oneplus 12": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2024,
        "tier": "flagship",
    },
    "oneplus 12r": {
        "initial": round(600 * USDTOKZT_RATE),  # Corrected from Kimovil: $600 launch price
        "launch_currency": "USD",
        "original_price": 600,
        "year": 2024,
        "tier": "mid-flagship",  # Not a true flagship - uses Snapdragon 8 Gen 2 (last year's chip)
    },
    "oneplus 11": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2023,
        "tier": "flagship",
    },
    "oneplus 10 pro": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2022,
        "tier": "flagship",
    },
    "oneplus 9 pro": {
        "initial": round(969 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 969,
        "year": 2021,
        "tier": "flagship",
    },
    "oneplus 9": {
        "initial": round(729 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 729,
        "year": 2021,
        "tier": "flagship",
    },
    "oneplus 8 pro": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2020,
        "tier": "flagship",
    },
    "oneplus 8": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2020,
        "tier": "flagship",
    },
    # =============================================================================
    # HUAWEI
    # =============================================================================
    "huawei p40 pro": {
        "initial": 624255,
        "launch_currency": "EUR",
        "original_price": "999",
        "year": 2020,
        "tier": "flagship",
    },
    "huawei p30 pro": {
        "initial": 561767,
        "launch_currency": "EUR",
        "original_price": "899",
        "year": 2019,
        "tier": "flagship",
    },
    "huawei mate 40": {
        "initial": round(899 * EURTOKZT_RATE),
        "launch_currency": "EUR",
        "original_price": 899,
        "year": 2020,
        "tier": "flagship",
    },
    # =============================================================================
    # APPLE IPHONE (for comparison)
    # =============================================================================
    "iphone 16 pro max": {
        "initial": round(1299 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1299,
        "year": 2024,
        "tier": "flagship-ultra",
    },
    "iphone 16 pro": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2024,
        "tier": "flagship-ultra",
    },
    "iphone 16 plus": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2024,
        "tier": "flagship",
    },
    "iphone 16": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2024,
        "tier": "flagship",
    },
    "iphone 15 pro max": {
        "initial": round(1199 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1199,
        "year": 2023,
        "tier": "flagship-ultra",
    },
    "iphone 15 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2023,
        "tier": "flagship-ultra",
    },
    "iphone 15 plus": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2023,
        "tier": "flagship",
    },
    "iphone 15": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2023,
        "tier": "flagship",
    },
    "iphone 14 pro max": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2022,
        "tier": "flagship-ultra",
    },
    "iphone 14 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2022,
        "tier": "flagship-ultra",
    },
    "iphone 14 plus": {
        "initial": round(899 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 899,
        "year": 2022,
        "tier": "flagship",
    },
    "iphone 14": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2022,
        "tier": "flagship",
    },
    "iphone 13 pro max": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2021,
        "tier": "flagship-ultra",
    },
    "iphone 13 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2021,
        "tier": "flagship-ultra",
    },
    "iphone 13": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2021,
        "tier": "flagship",
    },
    "iphone 12 pro max": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2020,
        "tier": "flagship-ultra",
    },
    "iphone 12 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2020,
        "tier": "flagship-ultra",
    },
    "iphone 12": {
        "initial": round(799 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 799,
        "year": 2020,
        "tier": "flagship",
    },
    "iphone 11": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2019,
        "tier": "flagship",
    },
    "iphone xr": {
        "initial": round(749 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 749,
        "year": 2018,
        "tier": "flagship",
    },
    # Popular in the sub-80k used market; US launch prices
    "iphone xs max": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2018,
        "tier": "flagship+",
    },
    "iphone xs": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2018,
        "tier": "flagship",
    },
    "iphone 11 pro max": {
        "initial": round(1099 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 1099,
        "year": 2019,
        "tier": "flagship-ultra",
    },
    "iphone 11 pro": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2019,
        "tier": "flagship-ultra",
    },
    "iphone x": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2017,
        "tier": "flagship",
    },
    "samsung s20 fe": {
        "initial": round(699 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 699,
        "year": 2020,
        "tier": "flagship-lite",
    },
    "samsung s10+": {
        "initial": round(999 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 999,
        "year": 2019,
        "tier": "flagship+",
    },
    "samsung s9+": {
        "initial": round(839 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 839,
        "year": 2018,
        "tier": "flagship+",
    },
    "pixel 7a": {
        "initial": round(499 * USDTOKZT_RATE),
        "launch_currency": "USD",
        "original_price": 499,
        "year": 2023,
        "tier": "mid",
    },
}


def get_market_info(model_name):
    """
    Get market price information for a phone model

    Args:
        model_name: Normalized model name (e.g., 'samsung s23')

    Returns:
        dict: {'initial': price, 'year': year, 'tier': tier} or None
    """
    return MARKET_PRICES.get(model_name.lower())


def add_custom_price(model_name, initial_price, release_year, tier):
    """
    Add or update a custom price entry

    Args:
        model_name: Model name (e.g., 'samsung s25')
        initial_price: Original retail price in KZT
        release_year: Year the phone was released
        tier: One of: 'flagship', 'mid-flagship', 'mid', 'budget-mid', 'budget'
    """
    MARKET_PRICES[model_name.lower()] = {
        "initial": initial_price,
        "year": release_year,
        "tier": tier,
    }


def get_all_models():
    """Get list of all models in the database"""
    return list(MARKET_PRICES.keys())


def get_models_by_brand(brand):
    """Get all models for a specific brand"""
    brand_lower = brand.lower()
    return {k: v for k, v in MARKET_PRICES.items() if k.startswith(brand_lower)}


def get_models_by_tier(tier):
    """Get all models in a specific tier"""
    return {k: v for k, v in MARKET_PRICES.items() if v["tier"] == tier}
