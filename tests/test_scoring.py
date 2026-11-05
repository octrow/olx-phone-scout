"""
Comprehensive tests for src/analysis/scoring.py

Tests all scoring functions with correct signatures:
- Discount scoring (0-35 points)
- Age scoring (0-25 points)
- Tier scoring (0-40 points)
- Storage scoring (0-20 points)
- RAM scoring (0-18 points)
- Price range scoring (0-20 points)
- Condition scoring (-90 to +20 points)
- Brand scoring (0-20 points)
- Camera scoring (0-30 points)
- Processor scoring (0-30 points)
- Battery health scoring (-30 to +20 points)
- Display quality scoring (0-20 points)
- Warranty/seller scoring (0-10 points)

Target: 80%+ coverage for scoring.py (391 statements)
"""

from src.analysis.scoring import (
    CURRENT_YEAR,
    check_price_tier_consistency,
    detect_market_price_issues,
    get_age_score,
    get_battery_health_score,
    get_brand_score,
    get_camera_score,
    get_condition_score,
    get_discount_score,
    get_display_score,
    get_dxomark_score,
    get_price_range_score,
    get_processor_score,
    get_ram_score,
    get_storage_score,
    get_tier_score,
    get_warranty_score,
    normalize_text,
    validate_discount_realism,
)


class TestDiscountScoring:
    """Test discount percentage scoring (0-35 points)"""

    def test_extreme_discount_80_plus(self):
        """80%+ discount = 35 points (amazing deal)"""
        score, label = get_discount_score(85)
        assert score == 35
        assert "Amazing deal" in label
        assert "85%" in label

    def test_high_discount_70_to_79(self):
        """70-79% discount = 27 points (great deal)"""
        score, label = get_discount_score(75)
        assert score == 27
        assert "Great deal" in label

    def test_good_discount_60_to_69(self):
        """60-69% discount = 20 points (good deal)"""
        score, label = get_discount_score(65)
        assert score == 20
        assert "Good deal" in label

    def test_fair_discount_50_to_59(self):
        """50-59% discount = 14 points (fair deal)"""
        score, label = get_discount_score(55)
        assert score == 14
        assert "Fair deal" in label

    def test_decent_discount_40_to_49(self):
        """40-49% discount = 9 points (decent discount)"""
        score, label = get_discount_score(45)
        assert score == 9
        assert "Decent discount" in label

    def test_low_discount_under_40(self):
        """Under 40% discount = 0 points"""
        score, label = get_discount_score(30)
        assert score == 0
        assert label is None

    def test_zero_discount(self):
        """0% discount = 0 points"""
        score, _label = get_discount_score(0)
        assert score == 0

    def test_edge_case_exactly_80(self):
        """Exactly 80% discount = 35 points"""
        score, _ = get_discount_score(80)
        assert score == 35


class TestAgeScoring:
    """Test phone age scoring (0-25 points)"""

    def test_brand_new_phone(self):
        """Released this year = 25 points"""
        score, label = get_age_score(CURRENT_YEAR)
        assert score == 25
        assert "Very recent" in label

    def test_one_year_old(self):
        """1 year old = 25 points"""
        score, _label = get_age_score(CURRENT_YEAR - 1)
        assert score == 25

    def test_two_years_old(self):
        """2 years old = 18 points"""
        score, label = get_age_score(CURRENT_YEAR - 2)
        assert score == 18
        assert "Recent" in label

    def test_three_years_old(self):
        """3 years old = 10 points"""
        score, label = get_age_score(CURRENT_YEAR - 3)
        assert score == 10
        assert "Still modern" in label

    def test_four_years_old(self):
        """4 years old = 4 points"""
        score, label = get_age_score(CURRENT_YEAR - 4)
        assert score == 4
        assert "Getting old" in label

    def test_five_years_old(self):
        """5 years old = 1 point"""
        score, _label = get_age_score(CURRENT_YEAR - 5)
        assert score == 1

    def test_very_old_phone(self):
        """6+ years old = 0 points"""
        score, _label = get_age_score(CURRENT_YEAR - 7)
        assert score == 0


class TestTierScoring:
    """Test tier scoring (0-40 points)"""

    def test_flagship_ultra(self):
        """Flagship Ultra = 40 points"""
        assert get_tier_score("flagship-ultra") == 40

    def test_flagship_plus(self):
        """Flagship Plus = 35 points"""
        assert get_tier_score("flagship+") == 35

    def test_flagship(self):
        """Flagship = 30 points"""
        assert get_tier_score("flagship") == 30

    def test_flagship_lite(self):
        """Flagship Lite/FE = 24 points"""
        assert get_tier_score("flagship-lite") == 24

    def test_mid_flagship(self):
        """Mid-flagship = 18 points"""
        assert get_tier_score("mid-flagship") == 18

    def test_mid_range(self):
        """Mid-range = 10 points"""
        assert get_tier_score("mid") == 10

    def test_budget_mid(self):
        """Budget mid-range = 5 points"""
        assert get_tier_score("budget-mid") == 5

    def test_budget(self):
        """Budget = 2 points"""
        assert get_tier_score("budget") == 2

    def test_unknown_tier(self):
        """Unknown tier = 0 points"""
        assert get_tier_score("unknown") == 0
        assert get_tier_score("") == 0


class TestStorageScoring:
    """Test storage scoring (0-20 points)"""

    def test_1tb_storage(self):
        """1TB = 20 points"""
        score, label = get_storage_score("samsung s24 ultra 1tb")
        assert score == 20
        assert "1TB" in label

    def test_512gb_storage(self):
        """512GB = 15 points"""
        score, label = get_storage_score("xiaomi 14 ultra 512gb")
        assert score == 15
        assert "512GB" in label

    def test_256gb_storage(self):
        """256GB = 8 points"""
        score, label = get_storage_score("samsung s24 256gb")
        assert score == 8
        assert "256GB" in label

    def test_128gb_storage(self):
        """128GB = 3 points"""
        score, label = get_storage_score("pixel 8 128gb")
        assert score == 3
        assert "128GB" in label

    def test_64gb_storage(self):
        """64GB = 0 points"""
        score, label = get_storage_score("redmi note 64gb")
        assert score == 0
        assert "64GB" in label

    def test_no_storage_mentioned(self):
        """No storage = 0 points, None label"""
        score, label = get_storage_score("samsung s24")
        assert score == 0
        assert label is None

    def test_storage_with_spaces(self):
        """'256 gb' (with space) should be detected"""
        score, _label = get_storage_score("phone 256 gb")
        assert score == 8


class TestRAMScoring:
    """Test RAM scoring (0-18 points)"""

    def test_16gb_ram(self):
        """16GB RAM = 18 points"""
        score, label = get_ram_score("samsung s24 ultra 16gb ram")
        assert score == 18
        assert "16GB" in label

    def test_12gb_ram(self):
        """12GB RAM = 14 points"""
        score, label = get_ram_score("xiaomi 14 ultra 12gb")
        assert score == 14
        assert "12GB" in label

    def test_8gb_ram(self):
        """8GB RAM = 10 points"""
        score, label = get_ram_score("pixel 8 8gb")
        assert score == 10
        assert "8GB" in label

    def test_6gb_ram(self):
        """6GB RAM = 6 points"""
        score, label = get_ram_score("redmi note 6gb")
        assert score == 6
        assert "6GB" in label

    def test_4gb_ram(self):
        """4GB RAM = 0 points"""
        score, label = get_ram_score("budget phone 4gb")
        assert score == 0
        assert "4GB" in label

    def test_no_ram_mentioned(self):
        """No RAM = 0 points, None label"""
        score, label = get_ram_score("samsung s24")
        assert score == 0
        assert label is None

    def test_ram_slash_format(self):
        """'12/256' format should detect 12GB RAM"""
        score, _label = get_ram_score("phone 12/256")
        assert score == 14


class TestPriceRangeScoring:
    """Test price range scoring (0-20 points)"""

    def test_very_affordable_under_40k(self):
        """Under 40k = 20 points"""
        score, label = get_price_range_score(35000)
        assert score == 20
        assert "Very affordable" in label

    def test_affordable_40k_to_50k(self):
        """40k-50k = 16 points"""
        score, label = get_price_range_score(45000)
        assert score == 16
        assert "Affordable" in label

    def test_reasonable_50k_to_60k(self):
        """50k-60k = 12 points"""
        score, label = get_price_range_score(55000)
        assert score == 12
        assert "Reasonable" in label

    def test_fair_60k_to_80k(self):
        """60k-80k = 8 points"""
        score, label = get_price_range_score(70000)
        assert score == 8
        assert "Fair" in label

    def test_mid_range_80k_to_100k(self):
        """80k-100k = 4 points"""
        score, label = get_price_range_score(90000)
        assert score == 4
        assert "Mid-range" in label

    def test_expensive_over_100k(self):
        """Over 100k = 0 points"""
        score, label = get_price_range_score(150000)
        assert score == 0
        assert label is None


class TestConditionScoring:
    """Test condition scoring (-90 to +20 points)"""

    def test_excellent_condition_russian(self):
        """'отличное состояние' = +15 points"""
        score, factors = get_condition_score("отличное состояние")
        assert score == 15
        assert len(factors) == 1
        assert "Excellent" in factors[0]

    def test_excellent_condition_english(self):
        """'perfect condition' = +15 points"""
        score, _factors = get_condition_score("perfect condition")
        assert score == 15

    def test_good_condition(self):
        """'хорошее состояние' = +7 points"""
        score, factors = get_condition_score("хорошее состояние")
        assert score == 7
        assert "Good" in factors[0]

    def test_with_box(self):
        """'с коробкой' = +3 points"""
        score, factors = get_condition_score("телефон с коробкой")
        assert score == 3
        assert "box" in factors[0].lower() or "full set" in factors[0].lower()

    def test_urgent_sale(self):
        """'срочно' = +5 points"""
        score, factors = get_condition_score("срочно продам")
        assert score == 5
        assert "Urgent" in factors[0]

    def test_not_working(self):
        """'не работает' = -80 points"""
        score, factors = get_condition_score("не работает")
        assert score == -80
        assert "Not working" in factors[0]

    def test_for_parts(self):
        """'на запчасти' = -90 points"""
        score, factors = get_condition_score("продаю на запчасти")
        assert score == -90
        assert "parts" in factors[0].lower()

    def test_network_issues(self):
        """'сеть не ловит' = -70 points"""
        score, _factors = get_condition_score("сеть не ловит")
        assert score == -70

    def test_screen_broken(self):
        """'экран не работает' = -155 points (screen broken -75 + not working -80)"""
        score, factors = get_condition_score("экран не работает")
        assert score == -155  # Matches both patterns
        assert len(factors) == 2  # Both penalties apply

    def test_cracked_screen(self):
        """'треснут' = -35 points"""
        score, _factors = get_condition_score("экран треснут")
        assert score == -35

    def test_battery_issues(self):
        """'батарея не держит' = -30 points"""
        score, _factors = get_condition_score("батарея не держит")
        assert score == -30

    def test_scratches(self):
        """'царапины' = -8 points"""
        score, _factors = get_condition_score("есть царапины")
        assert score == -8

    def test_no_accessories(self):
        """'без коробки' matches 'без' keywords"""
        score, factors = get_condition_score("продам без коробки без кабеля")
        assert score <= -2  # At least some penalty for missing accessories
        assert len(factors) >= 1

    def test_missing_s_pen(self):
        """'без стилуса' = -15 points"""
        score, _factors = get_condition_score("ultra без стилуса")
        assert score == -15

    def test_multiple_positive_only_first(self):
        """Multiple positive conditions: only first counts"""
        score, factors = get_condition_score("отличное состояние хорошее")
        assert score == 15  # Only 'excellent' counts
        assert len(factors) == 1

    def test_multiple_negatives_stack(self):
        """Multiple negative conditions stack"""
        score, factors = get_condition_score("треснут, царапины")
        assert score == -35 + -8  # Both penalties apply
        assert len(factors) == 2

    def test_empty_description(self):
        """Empty description = 0 points"""
        score, factors = get_condition_score("")
        assert score == 0
        assert factors == []

    def test_none_description(self):
        """None description = 0 points"""
        score, _factors = get_condition_score(None)
        assert score == 0


class TestBrandScoring:
    """Test brand reputation scoring (0-20 points)"""

    def test_google_brand(self):
        """Google = 20 points"""
        assert get_brand_score("google") == 20

    def test_samsung_brand(self):
        """Samsung = 18 points"""
        assert get_brand_score("samsung") == 18

    def test_xiaomi_brand(self):
        """Xiaomi = 18 points"""
        assert get_brand_score("xiaomi") == 18

    def test_oneplus_brand(self):
        """OnePlus = 17 points"""
        assert get_brand_score("oneplus") == 17

    def test_huawei_brand(self):
        """Huawei = 15 points"""
        assert get_brand_score("huawei") == 15

    def test_motorola_brand(self):
        """Motorola = 13 points"""
        assert get_brand_score("motorola") == 13

    def test_poco_brand(self):
        """POCO = 12 points"""
        assert get_brand_score("poco") == 12

    def test_unknown_brand_returns_default(self):
        """Unknown brand = 8 points (DEFAULT_BRAND_SCORE)"""
        assert get_brand_score("unknown_brand") == 8
        assert get_brand_score("") == 8


class TestCameraScoring:
    """Test camera scoring (0-30 points)"""

    def test_huawei_p60_pro_top_camera(self):
        """Huawei P60 Pro = 30 points (top DXOMark)"""
        score, label = get_camera_score("huawei p60 pro")
        assert score == 30
        assert "Top camera" in label

    def test_xiaomi_14_ultra_excellent(self):
        """Xiaomi 14 Ultra = 23 points (excellent camera)"""
        score, label = get_camera_score("xiaomi 14 ultra")
        assert score == 23
        assert "Excellent camera" in label

    def test_samsung_s24_ultra(self):
        """Samsung S24 Ultra = 19 points"""
        score, _label = get_camera_score("samsung s24 ultra")
        assert score == 19

    def test_google_pixel_9_pro(self):
        """Google Pixel 9 Pro = 22 points"""
        score, _label = get_camera_score("google pixel 9 pro")
        assert score == 22

    def test_partial_match(self):
        """Partial model name should match"""
        score, _label = get_camera_score("s24 ultra")
        assert score == 19  # Should match 'samsung s24 ultra'

    def test_unknown_model_with_tier_fallback(self):
        """Unknown model uses tier fallback"""
        score, label = get_camera_score("unknown phone", tier="flagship-ultra")
        assert score == 25
        assert "Flagship Ultra" in label

    def test_unknown_model_no_tier(self):
        """Unknown model without tier = 0 points"""
        score, label = get_camera_score("unknown phone")
        assert score == 0
        assert label is None

    def test_no_model_does_not_match_the_first_table_entry(self):
        """No extracted model ("" / None) gets the tier default, not Huawei P60 Pro's 30"""
        assert get_camera_score(None) == (0, None)
        assert get_camera_score("") == (0, None)
        score, _label = get_camera_score(None, tier="mid")
        assert score == 6


class TestDXOMarkScore:
    """Test DXOMark score retrieval (returns int, not tuple)"""

    def test_huawei_p60_pro_dxomark(self):
        """Huawei P60 Pro = 156 DXOMark score"""
        score = get_dxomark_score("huawei p60 pro")
        assert score == 156

    def test_xiaomi_14_ultra_dxomark(self):
        """Xiaomi 14 Ultra = 143 DXOMark score"""
        score = get_dxomark_score("xiaomi 14 ultra")
        assert score == 143

    def test_samsung_s24_ultra_dxomark(self):
        """Samsung S24 Ultra = 136 DXOMark score"""
        score = get_dxomark_score("samsung s24 ultra")
        assert score == 136

    def test_unknown_model_returns_none(self):
        """Unknown model = None"""
        score = get_dxomark_score("unknown phone")
        assert score is None

    def test_no_model_returns_none(self):
        """No extracted model = None, not the first table entry's 156"""
        assert get_dxomark_score(None) is None
        assert get_dxomark_score("") is None


class TestProcessorScoring:
    """Test processor/chipset scoring (0-30 points)"""

    def test_snapdragon_8_gen_3(self):
        """Snapdragon 8 Gen 3 = 30 points"""
        score, label = get_processor_score("phone with snapdragon 8 gen 3")
        assert score == 30
        assert "SD 8 Gen 3" in label

    def test_snapdragon_8_gen_2(self):
        """Snapdragon 8 Gen 2 = 28 points"""
        score, _label = get_processor_score("snapdragon 8 gen 2 phone")
        assert score == 28

    def test_dimensity_9300(self):
        """Dimensity 9300 = 29 points"""
        score, _label = get_processor_score("dimensity 9300")
        assert score == 29

    def test_a17_pro(self):
        """A17 Pro = 30 points"""
        score, _label = get_processor_score("iphone 15 pro with a17 pro")
        assert score == 30

    def test_tensor_g4(self):
        """Tensor G4 = 25 points"""
        score, _label = get_processor_score("pixel 9 tensor g4")
        assert score == 25

    def test_unknown_processor_with_tier(self):
        """Unknown processor uses tier fallback"""
        score, label = get_processor_score("unknown phone", tier="flagship-ultra")
        assert score == 28
        assert "estimated" in label

    def test_no_processor_no_tier(self):
        """No processor, no tier = 0 points"""
        score, label = get_processor_score("", tier=None)
        assert score == 0
        assert label is None


class TestBatteryHealthScoring:
    """Test battery health scoring (-30 to +20 points)"""

    def test_excellent_battery_95_plus(self):
        """95%+ battery = +20 points"""
        score, label = get_battery_health_score("батарея 98%")
        assert score == 20
        assert "Excellent" in label

    def test_great_battery_90_to_94(self):
        """90-94% battery = +15 points"""
        score, label = get_battery_health_score("battery health 92%")
        assert score == 15
        assert "Great" in label

    def test_good_battery_85_to_89(self):
        """85-89% battery = +10 points"""
        score, _label = get_battery_health_score("аккумулятор 87%")
        assert score == 10

    def test_decent_battery_80_to_84(self):
        """80-84% battery = +5 points"""
        score, label = get_battery_health_score("батарея 82%")
        assert score == 5
        assert "Decent" in label

    def test_degraded_battery_60_to_69(self):
        """60-69% battery = -10 points"""
        score, _label = get_battery_health_score("батарея 65%")
        assert score == -10

    def test_poor_battery_under_60(self):
        """Under 60% battery = -30 points"""
        score, _label = get_battery_health_score("battery health 45%")
        assert score == -30

    def test_new_battery_keyword(self):
        """'новая батарея' = +15 points"""
        score, label = get_battery_health_score("новая батарея")
        assert score == 15
        assert "replaced" in label.lower() or "excellent" in label.lower()

    def test_battery_replaced_keyword(self):
        """'battery replaced' = +15 points"""
        score, _label = get_battery_health_score("battery replaced recently")
        assert score == 15

    def test_battery_issues_keyword(self):
        """'быстро разряжается' = -15 points"""
        score, label = get_battery_health_score("быстро разряжается")
        assert score == -15
        assert "issues" in label.lower()

    def test_no_battery_info(self):
        """No battery info = 0 points"""
        score, label = get_battery_health_score("good phone")
        assert score == 0
        assert label is None


class TestDisplayScoring:
    """Test display quality scoring (0-20 points)"""

    def test_amoled_120hz_max_score(self):
        """AMOLED + 120Hz = 12 + 6 = 18 points"""
        score, labels = get_display_score("phone", "super amoled 120hz display")
        assert score == 18
        assert len(labels) == 2

    def test_oled_display(self):
        """OLED = 11 points"""
        score, labels = get_display_score("oled display phone", "")
        assert score == 11
        assert any("OLED" in label for label in labels)

    def test_ips_lcd(self):
        """IPS LCD = 5 points"""
        score, _labels = get_display_score("ips lcd screen", "")
        assert score == 5

    def test_tft_display(self):
        """TFT = 2 points"""
        score, _labels = get_display_score("tft display", "")
        assert score == 2

    def test_120hz_alone(self):
        """120Hz without display type = 6 points"""
        score, _labels = get_display_score("phone 120hz", "")
        assert score == 6

    def test_90hz_bonus(self):
        """90Hz = 3 points"""
        score, _labels = get_display_score("", "90hz refresh rate")
        assert score == 3

    def test_no_display_info(self):
        """No display info = 0 points"""
        score, labels = get_display_score("", "")
        assert score == 0
        assert labels == []


class TestWarrantyScoring:
    """Test warranty/seller scoring (0-10 points)"""

    def test_two_year_warranty(self):
        """2-year warranty = 10 points (matches both '2 года' and 'гарантия')"""
        score, labels = get_warranty_score("", "гарантия 2 года")
        assert score == 10  # Matches both warranty patterns (6 + 4)
        assert len(labels) >= 1

    def test_one_year_warranty(self):
        """1-year warranty = 4 points"""
        score, _labels = get_warranty_score("", "1 year warranty")
        assert score == 4

    def test_official_store(self):
        """Official store = 5 points"""
        score, _labels = get_warranty_score("", "официальный магазин")
        assert score == 5

    def test_with_receipt(self):
        """With receipt = 3 points"""
        score, _labels = get_warranty_score("с чеком", "")
        assert score == 3

    def test_multiple_positive_signals(self):
        """Multiple positive signals can stack"""
        score, labels = get_warranty_score("", "официальный магазин, гарантия 2 года")
        assert score >= 10  # Both should apply, capped at 10
        assert len(labels) >= 2

    def test_for_parts_penalty(self):
        """'for parts' = -5 points penalty"""
        score, _labels = get_warranty_score("", "продаю на запчасти")
        assert score == -5

    def test_no_warranty_info(self):
        """No warranty info = 0 points"""
        score, labels = get_warranty_score("", "")
        assert score == 0
        assert labels == []


class TestHelperFunctions:
    """Test helper functions"""

    def test_normalize_text_lowercase(self):
        """Normalize text converts to lowercase"""
        assert normalize_text("Samsung S24 ULTRA") == "samsung s24 ultra"

    def test_normalize_text_strips_whitespace(self):
        """Normalize text strips leading/trailing whitespace"""
        assert normalize_text("  phone  ") == "phone"

    def test_normalize_text_multiple_spaces(self):
        """Normalize text collapses multiple spaces"""
        assert normalize_text("samsung   s24    ultra") == "samsung s24 ultra"

    def test_normalize_text_removes_excessive_punctuation(self):
        """Normalize text reduces excessive punctuation"""
        assert "!" in normalize_text("phone!!!")
        assert "?" in normalize_text("phone???")

    def test_normalize_text_empty_string(self):
        """Normalize text handles empty string"""
        assert normalize_text("") == ""


class TestValidationFunctions:
    """Test discount/price validation functions"""

    def test_validate_discount_realism_budget_high_discount(self):
        """Budget phone with 80%+ discount flagged as suspicious"""
        adjusted, warning = validate_discount_realism(35000, 85, tier="budget")
        assert adjusted < 85  # Discount should be reduced
        assert warning is not None
        assert "Suspicious" in warning

    def test_validate_discount_realism_extreme_discount(self):
        """85%+ discount flagged and capped"""
        adjusted, warning = validate_discount_realism(100000, 90, tier="flagship")
        assert adjusted <= 80  # Should be capped
        assert warning is not None
        assert "Unrealistic" in warning

    def test_validate_discount_realism_flagship_low_price(self):
        """Flagship with high discount and low price = caution"""
        _adjusted, warning = validate_discount_realism(80000, 85, tier="flagship-ultra")
        assert warning is not None
        assert "Caution" in warning

    def test_validate_discount_realism_normal_discount(self):
        """Normal discount passes without warning"""
        adjusted, warning = validate_discount_realism(100000, 50, tier="flagship")
        assert adjusted == 50
        assert warning is None

    def test_check_price_tier_consistency_too_low(self):
        """Price too low for tier = penalty"""
        adjustment, warning = check_price_tier_consistency(50000, "flagship-ultra")
        assert adjustment == -15
        assert warning is not None
        assert "too low" in warning

    def test_check_price_tier_consistency_too_high(self):
        """Price too high for tier = penalty"""
        adjustment, warning = check_price_tier_consistency(600000, "mid")
        assert adjustment == -10
        assert warning is not None
        assert "too high" in warning

    def test_check_price_tier_consistency_perfect_range(self):
        """Price in perfect range = bonus"""
        adjustment, warning = check_price_tier_consistency(200000, "flagship")
        assert adjustment == 3
        assert warning is None

    def test_detect_market_price_issues_5x_ratio(self):
        """Market price > 5x current price = suspicious"""
        is_suspicious, reason = detect_market_price_issues("phone", 320000, 35000)
        assert is_suspicious is True
        assert "5" in reason or "9" in reason  # Ratio should be mentioned

    def test_detect_market_price_issues_budget_flagship_price(self):
        """Budget model with flagship price = suspicious"""
        is_suspicious, reason = detect_market_price_issues("Redmi 13C", 200000, 40000)
        assert is_suspicious is True
        assert "Budget" in reason

    def test_detect_market_price_issues_normal(self):
        """Normal price ratio = not suspicious"""
        is_suspicious, reason = detect_market_price_issues("Samsung S24", 500000, 300000)
        assert is_suspicious is False
        assert reason is None
