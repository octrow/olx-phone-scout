"""Centralized patterns for brand and model detection."""

from typing import Any

# First hit in this order wins: sub-brands (poco, redmi) come before xiaomi,
# so "Xiaomi Redmi Note 12 Pro" parses as Redmi, not as a Xiaomi flagship
BRAND_ALIASES = {
    "samsung": ["samsung", "самсунг"],
    "poco": ["poco", "поко"],
    "redmi": ["redmi", "редми"],
    "xiaomi": ["xiaomi", "ксиоми", "сяоми"],
    "google": ["pixel", "google", "гугл"],
    "oneplus": ["oneplus", "ванплюс"],
    "realme": ["realme", "реалми"],
    "oppo": ["oppo", "оппо"],
    "vivo": ["vivo", "виво"],
    "huawei": ["huawei", "хуавей"],
    "honor": ["honor", "хонор"],
    "motorola": ["motorola", "мото"],
    "nokia": ["nokia", "нокиа"],
    "asus": ["asus", "асус"],
    "zte": ["zte"],
    "tcl": ["tcl"],
    "nothing": ["nothing"],
}

MODEL_PATTERNS: dict[str, list[tuple[str, Any]]] = {
    "samsung": [
        (r"s(\d+)\s*ultra", lambda m: f"Galaxy S{m.group(1)} Ultra"),
        (r"s(\d+)\s*(plus|\+)", lambda m: f"Galaxy S{m.group(1)} Plus"),
        (r"s(\d+)\s*fe", lambda m: f"Galaxy S{m.group(1)} FE"),
        (r"s(\d+)", lambda m: f"Galaxy S{m.group(1)}"),
        (r"a(\d+)", lambda m: f"Galaxy A{m.group(1)}"),
        (r"z\s*fold\s*(\d+)", lambda m: f"Galaxy Z Fold{m.group(1)}"),
        (r"z\s*flip\s*(\d+)", lambda m: f"Galaxy Z Flip{m.group(1)}"),
    ],
    "xiaomi": [
        (r"(\d+)t\s*pro", lambda m: f"{m.group(1)}T Pro"),
        (r"(\d+)\s*pro", lambda m: f"{m.group(1)} Pro"),
        (r"(\d+)t", lambda m: f"{m.group(1)}T"),
        (r"(\d+)", lambda m: f"{m.group(1)}"),
        (r"mi\s*(\d+)", lambda m: f"Mi {m.group(1)}"),
    ],
    "redmi": [
        (r"note\s*(\d+)\s*pro\s*plus", lambda m: f"Note {m.group(1)} Pro Plus"),
        (r"note\s*(\d+)\s*pro", lambda m: f"Note {m.group(1)} Pro"),
        (r"note\s*(\d+)s", lambda m: f"Note {m.group(1)}S"),
        (r"note\s*(\d+)", lambda m: f"Note {m.group(1)}"),
        (r"(\d+)x", lambda m: f"{m.group(1)}X"),
        (r"(\d+)c", lambda m: f"{m.group(1)}C"),
        (r"(\d+)", lambda m: f"{m.group(1)}"),
    ],
    "poco": [
        (r"f(\d+)\s*pro", lambda m: f"F{m.group(1)} Pro"),
        (r"f(\d+)", lambda m: f"F{m.group(1)}"),
        (r"x(\d+)\s*pro", lambda m: f"X{m.group(1)} Pro"),
        (r"x(\d+)", lambda m: f"X{m.group(1)}"),
        (r"m(\d+)\s*pro", lambda m: f"M{m.group(1)} Pro"),
        (r"m(\d+)", lambda m: f"M{m.group(1)}"),
    ],
    "google": [
        (r"pixel\s*(\d+)\s*pro", lambda m: f"Pixel {m.group(1)} Pro"),
        (r"pixel\s*(\d+)a", lambda m: f"Pixel {m.group(1)}a"),
        (r"pixel\s*(\d+)", lambda m: f"Pixel {m.group(1)}"),
    ],
    "oneplus": [
        (r"(\d+)t", lambda m: f"{m.group(1)}T"),
        (r"(\d+)r", lambda m: f"{m.group(1)}R"),
        (r"(\d+)\s*pro", lambda m: f"{m.group(1)} Pro"),
        (r"(\d+)", lambda m: f"{m.group(1)}"),
    ],
}
