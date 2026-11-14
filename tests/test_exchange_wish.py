from src.analysis.analyzer import AndroidAnalyzer
from src.analysis.market_data import MARKET_PRICES
from src.detection.patterns import detect_phone_brand, strip_exchange_wish


def test_wanted_phone_in_exchange_is_ignored():
    assert detect_phone_brand("Oppo Reno7 4G 128 GB (обмен на iphone 13 pro)")[0] == "oppo"
    assert detect_phone_brand("Poco X5 айырбас на iphone 11")[0] == "poco"


def test_phone_being_sold_is_kept():
    assert "Iphone 12 pro" in strip_exchange_wish("Обмен Iphone 12 pro 6/256gb на что то")
    assert strip_exchange_wish("iPhone 13 128gb") == "iPhone 13 128gb"


def test_variants_get_their_own_market_price_not_the_base_models():

    analyzer = AndroidAnalyzer.__new__(AndroidAnalyzer)
    analyzer.market_prices = MARKET_PRICES
    assert analyzer.get_market_price_info("xiaomi 13 lite 256gb") is None  # not the flagship 13
    assert analyzer.get_market_price_info("samsung s20 plus") is MARKET_PRICES["samsung s20+"]
    assert analyzer.get_market_price_info("iphone 11 pro 256") is MARKET_PRICES["iphone 11 pro"]
    assert analyzer.get_market_price_info("xiaomi 13 256gb") is MARKET_PRICES["xiaomi 13"]


def test_iphone_x_family_and_samsung_s_are_not_confused():

    analyzer = AndroidAnalyzer.__new__(AndroidAnalyzer)
    assert analyzer.extract_model_from_title("iPhone XR 64") == "iphone xr"
    assert analyzer.extract_model_from_title("iPhone XS Max 256") == "iphone xs max"
    assert analyzer.extract_model_from_title("iPhone XS 64") == "iphone xs"  # not "samsung s64"
    assert analyzer.extract_model_from_title("iPhone X 64gb") == "iphone x"


def test_samsung_a_series_models_get_market_prices():
    analyzer = AndroidAnalyzer.__new__(AndroidAnalyzer)
    analyzer.market_prices = MARKET_PRICES

    for title, model in (
        ("Samsung Galaxy A35 5G 128GB", "samsung a35"),
        ("Samsung Galaxy A36 5G 128GB", "samsung a36"),
        ("Samsung Galaxy A54 5G 256GB", "samsung a54"),
        ("Samsung Galaxy A56 5G 256GB", "samsung a56"),
    ):
        assert analyzer.get_market_price_info(title) is MARKET_PRICES[model]
