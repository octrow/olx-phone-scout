"""Tests for AndroidAnalyzer workflow methods"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analysis.analyzer import AndroidAnalyzer


class TestAnalyzerWorkflows:
    """Test analyzer workflow methods"""

    def test_calculate_value_score_complete(self, sample_phone_listing, sample_phone_specs):
        """calculate_value_score with complete data"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phone = {
            **sample_phone_listing,
            **sample_phone_specs,
            "description": "Excellent condition, battery health 95%",
        }

        result = analyzer.calculate_value_score(phone)

        assert "value_score" in result
        assert isinstance(result["value_score"], (int, float))
        assert result["value_score"] >= 0

    def test_calculate_value_score_minimal_data(self):
        """calculate_value_score with minimal data (triggers None branches)"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        # Minimal phone data - will trigger many None score branches
        phone = {
            "title": "Generic Phone XYZ",
            "price": 100000,
            "link": "http://test.com/1",
            "status": "Б/у",
            "location": "Almaty",
        }

        result = analyzer.calculate_value_score(phone)

        # Should still calculate score even with missing fields
        assert "value_score" in result
        assert isinstance(result["value_score"], (int, float))
        # Some scores should be None due to missing data
        assert result.get("processor_score") is None
        assert result.get("battery_health_score") is None

    def test_calculate_value_score_no_display_match(self):
        """calculate_value_score when display score returns None"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phone = {
            "title": "Basic Phone",
            "price": 50000,
            "link": "http://test.com/1",
            "description": "No display specs mentioned",
        }

        result = analyzer.calculate_value_score(phone)

        # Display score should be None
        assert result.get("display_score") is None

    def test_calculate_value_score_no_warranty(self):
        """calculate_value_score when warranty score returns None"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phone = {
            "title": "Phone Without Warranty",
            "price": 150000,
            "link": "http://test.com/1",
            "description": "Good condition, no warranty info",
        }

        result = analyzer.calculate_value_score(phone)

        # Warranty score should be None
        assert result.get("warranty_score") is None

    def test_load_androids_from_session_success(self, temp_listings_file):
        """_load_androids_from_session loads from JSON file"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        with patch("src.core.config.get_output_files") as mock_get_files:
            mock_get_files.return_value = {
                "analyzed_androids": temp_listings_file,
                "androids": temp_listings_file,
                "iphones": Path("/nonexistent/iphones.json"),
            }

            result = analyzer._load_androids_from_session()

            assert len(result) == 3
            assert all("title" in phone for phone in result)

    def test_load_androids_from_session_file_not_found(self):
        """_load_androids_from_session handles missing file"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        with patch("src.core.config.get_output_files") as mock_get_files:
            from pathlib import Path

            mock_get_files.return_value = {
                "analyzed_androids": Path("/nonexistent/analyzed.json"),
                "androids": Path("/nonexistent/androids.json"),
                "iphones": Path("/nonexistent/iphones.json"),
            }

            with pytest.raises(FileNotFoundError):
                analyzer._load_androids_from_session()

    def test_load_androids_from_legacy(self):
        """_load_androids_from_legacy loads from legacy path"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"phones": [{"title": "Test Phone", "price": 100000}], "total": 1}, f)
            temp_path = f.name

        try:
            with patch("src.core.config.ANDROIDS_FILE", Path(temp_path)):
                result = analyzer._load_androids_from_legacy()

                assert len(result) == 1
                assert result[0]["title"] == "Test Phone"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_calculate_all_scores(self, sample_phone_listings):
        """_calculate_all_scores processes multiple phones"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phones = sample_phone_listings.copy()

        analyzer._calculate_all_scores(phones)

        assert all("value_score" in phone for phone in phones)
        assert all(isinstance(phone["value_score"], (int, float)) for phone in phones)

    def test_get_output_file_paths_session_dir(self):
        """_get_output_file_paths with session directory"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        with patch("src.core.config.get_output_files") as mock_get_files:
            mock_get_files.return_value = {
                "analyzed_androids": "/path/to/analyzed.json",
                "top_androids": "/path/to/top.json",
                "recommendations_report": "/path/to/report.txt",
            }

            result = analyzer._get_output_file_paths(use_session_dir=True)

            assert "analyzed" in result
            assert "top" in result
            assert "report" in result

    def test_get_output_file_paths_legacy(self):
        """_get_output_file_paths with legacy paths"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        result = analyzer._get_output_file_paths(use_session_dir=False)

        assert "analyzed" in result
        assert "top" in result
        assert "report" in result
        assert all(isinstance(path, str) for path in result.values())

    def test_save_full_analysis(self, temp_data_dir, sample_phone_listings):
        """_save_full_analysis saves JSON with metadata"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        output_path = temp_data_dir / "analyzed.json"

        analyzer._save_full_analysis(sample_phone_listings, str(output_path))

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert "phones" in data
        assert "total" in data
        assert len(data["phones"]) == 3

    def test_save_top_phones(self, temp_data_dir):
        """_save_top_phones saves top N phones"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phones = [
            {"title": "Phone 1", "value_score": 90},
            {"title": "Phone 2", "value_score": 80},
            {"title": "Phone 3", "value_score": 70},
        ]

        output_path = temp_data_dir / "top.json"

        analyzer._save_top_phones(phones, str(output_path))

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "count" in data
        assert "phones" in data
        assert data["count"] == 3


class TestAnalyzerReportGeneration:
    """Test report generation methods"""

    def test_write_report_header(self, temp_data_dir):
        """_write_report_header writes header"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        report_path = temp_data_dir / "report.txt"

        with open(report_path, "w") as f:
            analyzer._write_report_header(f, total_count=100, top_count=50)

        assert report_path.exists()

        with open(report_path) as f:
            content = f.read()

        assert "100" in content or "50" in content

    def test_write_phone_entry(self, temp_data_dir, sample_phone_listing):
        """_write_phone_entry writes phone details"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        phone = {
            **sample_phone_listing,
            "value_score": 85,
            "value_factors": ["Great price", "Excellent camera"],
        }

        report_path = temp_data_dir / "phone_entry.txt"

        with open(report_path, "w") as f:
            analyzer._write_phone_entry(f, phone, rank=1)

        assert report_path.exists()


class TestAnalyzerAIWorkflows:
    """Test AI analyzer workflow methods"""

    def test_run_gemini_analysis_disabled(self):
        """_run_gemini_analysis returns empty when gemini disabled"""
        analyzer = AndroidAnalyzer(use_gemini=False, enrich_with_kimovil=False)

        androids = [
            {"title": "Phone 1", "value_score": 90},
            {"title": "Phone 2", "value_score": 80},
        ]

        # Should return original list and empty failures when disabled
        result_androids, failures = analyzer._run_gemini_analysis(androids, gemini_count=2)

        assert result_androids == androids
        assert failures == []

    def test_run_gemini_analysis_count_zero(self):
        """_run_gemini_analysis returns empty when count is 0"""
        analyzer = AndroidAnalyzer(use_gemini=False, enrich_with_kimovil=False)

        androids = [{"title": "Phone 1", "value_score": 90}]

        # Should return original list when count is 0
        result_androids, failures = analyzer._run_gemini_analysis(androids, gemini_count=0)

        assert result_androids == androids
        assert failures == []

    def test_run_cloud_llm_fallback_disabled(self):
        """_run_cloud_llm_fallback returns original when disabled"""
        analyzer = AndroidAnalyzer(
            use_cerebras=False, use_openrouter=False, use_vercel=False, enrich_with_kimovil=False
        )

        androids = [
            {"title": "Phone 1", "value_score": 90},
            {"title": "Phone 2", "value_score": 80},
        ]
        gemini_failures = [0, 1]

        # Should return original list when cloud LLM disabled
        result = analyzer._run_cloud_llm_fallback(androids, gemini_failures)

        assert result == androids

    def test_run_cloud_llm_fallback_no_failures(self):
        """_run_cloud_llm_fallback returns original when no failures"""
        analyzer = AndroidAnalyzer(
            use_cerebras=False, use_openrouter=False, use_vercel=False, enrich_with_kimovil=False
        )

        androids = [{"title": "Phone 1", "value_score": 90}]
        gemini_failures = []  # No failures

        # Should return original list when no failures to retry
        result = analyzer._run_cloud_llm_fallback(androids, gemini_failures)

        assert result == androids


class TestAnalyzerInitialization:
    """Test analyzer initialization options"""

    def test_init_with_gemini(self):
        """Initialize with Gemini enabled"""
        with patch("src.analysis.analyzer.GeminiAnalyzer") as mock_gemini:
            AndroidAnalyzer(
                use_gemini=True, gemini_use_photos=True, gemini_top_n=10, enrich_with_kimovil=False
            )

            assert mock_gemini.called

    def test_init_with_cerebras(self):
        """Initialize with Cerebras enabled"""
        with patch("src.analysis.analyzer.CloudLLMAnalyzer") as mock_cloud:
            AndroidAnalyzer(
                use_cerebras=True, cerebras_model="llama3.1-8b", enrich_with_kimovil=False
            )

            assert mock_cloud.called

    def test_init_with_openrouter(self):
        """Initialize with OpenRouter enabled"""
        with patch("src.analysis.analyzer.CloudLLMAnalyzer") as mock_cloud:
            AndroidAnalyzer(
                use_openrouter=True, openrouter_model="llama-3.1-8b", enrich_with_kimovil=False
            )

            assert mock_cloud.called

    def test_init_with_vercel(self):
        """Initialize with Vercel enabled"""
        with patch("src.analysis.analyzer.CloudLLMAnalyzer") as mock_cloud:
            AndroidAnalyzer(use_vercel=True, vercel_model="llama-3.1-8b", enrich_with_kimovil=False)

            assert mock_cloud.called

    def test_init_with_kimovil_success(self):
        """Initialize with KiMoVil enrichment"""
        with patch("src.analysis.analyzer.SpecEnricher") as mock_enricher:
            AndroidAnalyzer(enrich_with_kimovil=True)

            assert mock_enricher.called

    def test_init_with_kimovil_failure(self):
        """Initialize with KiMoVil enrichment failure"""
        with patch("src.analysis.analyzer.SpecEnricher", side_effect=Exception("Init failed")):
            analyzer = AndroidAnalyzer(enrich_with_kimovil=True)

            # Should handle gracefully
            assert analyzer.spec_enricher is None


class TestAnalyzerEnrichment:
    """Test spec enrichment methods"""

    def test_enrich_with_kimovil_specs_disabled(self, sample_phone_listings):
        """_enrich_with_kimovil_specs when disabled"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)
        analyzer.spec_enricher = None

        result = analyzer._enrich_with_kimovil_specs(sample_phone_listings)

        # Should return unchanged
        assert result == sample_phone_listings

    def test_enrich_with_kimovil_specs_enabled(self, sample_phone_listings):
        """_enrich_with_kimovil_specs when enabled"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        # Mock enricher
        mock_enricher = MagicMock()
        analyzer.spec_enricher = mock_enricher

        # Skip async complexity - just check it calls enricher
        with patch("src.analysis.analyzer.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = sample_phone_listings

            result = analyzer._enrich_with_kimovil_specs(sample_phone_listings)

            assert isinstance(result, list)


class TestAnalyzerLogging:
    """Test logging methods"""

    def test_log_gemini_estimation(self):
        """_log_gemini_estimation logs without error"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        # Should not raise
        analyzer._log_gemini_estimation(gemini_count=10)

    def test_log_gemini_results(self):
        """_log_gemini_results logs results"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        androids = [
            {"title": "Phone 1", "gemini_analysis": "Good phone"},
            {"title": "Phone 2", "gemini_analysis": "Great phone"},
            {"title": "Phone 3"},
        ]

        # Should not raise
        analyzer._log_gemini_results(androids, gemini_count=3, analyzed_count=2)


class TestAnalyzerLoadingEdgeCases:
    """Test analyzer loading edge cases"""

    def test_load_androids_from_session_with_fallback_to_raw(self):
        """_load_androids_from_session falls back to raw androids when analyzed fails"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        # Create temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create an invalid analyzed file (triggers exception)
            analyzed_file = tmpdir_path / "analyzed.json"
            analyzed_file.write_text("invalid json{{{")

            # Create a valid raw androids file
            raw_file = tmpdir_path / "androids.json"
            raw_data = {
                "phones": [
                    {"title": "Phone 1", "link": "http://test.com/1"},
                    {"title": "Phone 2", "link": "http://test.com/2"},
                ]
            }
            raw_file.write_text(json.dumps(raw_data, ensure_ascii=False))

            with patch("src.core.config.get_output_files") as mock_get_files:
                with patch("src.core.config.get_results_dir") as mock_results_dir:
                    mock_results_dir.return_value = tmpdir_path
                    mock_get_files.return_value = {
                        "analyzed_androids": analyzed_file,
                        "androids": raw_file,
                        "iphones": Path("/nonexistent/iphones.json"),
                    }

                    # Should fall back to raw file
                    result = analyzer._load_androids_from_session()

                    assert len(result) == 2
                    assert result[0]["title"] == "Phone 1"

    def test_load_androids_from_session_no_files_falls_back_to_legacy(self):
        """_load_androids_from_session falls back to legacy when no session files"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create legacy file
            legacy_file = tmpdir_path / "legacy_androids.json"
            legacy_data = {"phones": [{"title": "Legacy Phone", "link": "http://test.com/1"}]}
            legacy_file.write_text(json.dumps(legacy_data, ensure_ascii=False))

            with patch("src.core.config.get_output_files") as mock_get_files:
                with patch("src.core.config.get_results_dir") as mock_results_dir:
                    with patch("src.core.config.ANDROIDS_FILE", legacy_file):
                        mock_results_dir.return_value = tmpdir_path
                        mock_get_files.return_value = {
                            "analyzed_androids": tmpdir_path / "nonexistent_analyzed.json",
                            "androids": tmpdir_path / "nonexistent_raw.json",
                            "iphones": Path("/nonexistent/iphones.json"),
                        }

                        # Should fall back to legacy
                        result = analyzer._load_androids_from_session()

                        assert len(result) == 1
                        assert result[0]["title"] == "Legacy Phone"

    def test_collect_gemini_failures_with_failures(self):
        """_collect_gemini_failures identifies failed analyses"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        androids = [
            {"title": "Phone 1", "gemini_analysis": {"analyzed": True}},
            {"title": "Phone 2", "gemini_analysis": {"analyzed": False}},
            {"title": "Phone 3"},  # No analysis
            {"title": "Phone 4", "gemini_analysis": {"analyzed": True}},
        ]

        failures = analyzer._collect_gemini_failures(androids, gemini_count=4)

        # Should identify indices 1 and 2 as failures
        assert 1 in failures
        assert 2 in failures
        assert len(failures) == 2

    def test_collect_gemini_failures_no_failures(self):
        """_collect_gemini_failures returns empty when all succeed"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)

        androids = [
            {"title": "Phone 1", "gemini_analysis": {"analyzed": True}},
            {"title": "Phone 2", "gemini_analysis": {"analyzed": True}},
        ]

        failures = analyzer._collect_gemini_failures(androids, gemini_count=2)

        assert failures == []


class TestAnalyzerCloudLLMWorkflows:
    """Test Cloud LLM analysis workflows"""

    def test_run_cloud_llm_primary_disabled(self):
        """_run_cloud_llm_primary when cloud_llm disabled"""
        analyzer = AndroidAnalyzer(use_cerebras=False, enrich_with_kimovil=False)

        androids = [{"title": "Phone 1", "value_score": 90}]

        # Should return original when disabled
        result, failures = analyzer._run_cloud_llm_primary(androids, analysis_count=1)

        assert result == androids
        assert failures == []

    def test_run_gemini_fallback_disabled(self):
        """_run_gemini_fallback when gemini disabled"""
        analyzer = AndroidAnalyzer(use_gemini=False, enrich_with_kimovil=False)

        androids = [
            {"title": "Phone 1", "value_score": 90},
            {"title": "Phone 2", "value_score": 80},
        ]
        cloud_failures = [0, 1]

        # Should return original when gemini not available
        result = analyzer._run_gemini_fallback(androids, cloud_failures)

        assert result == androids

    def test_run_gemini_fallback_no_failures(self):
        """_run_gemini_fallback when no failures"""
        analyzer = AndroidAnalyzer(use_gemini=False, enrich_with_kimovil=False)

        androids = [{"title": "Phone 1", "value_score": 90}]
        cloud_failures = []

        # Should return original when no failures
        result = analyzer._run_gemini_fallback(androids, cloud_failures)

        assert result == androids


class _FakeGemini:
    """Gemini stand-in: marks every analysed phone, no network."""

    enabled = True

    def __init__(self):
        self.calls = []

    def analyze_batch(self, phones, max_phones):
        self.calls.append(max_phones)
        for phone in phones[:max_phones]:
            phone["gemini_analysis"] = {"analyzed": True}
        return phones


class TestAnalyzerPipelineOrder:
    """Logic-map findings #1 and #2: which provider runs, and when scores are final"""

    def test_gemini_alone_runs_as_primary(self):
        """--gemini without a cloud LLM analyses the top phones with Gemini (#1)"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)
        analyzer.gemini = _FakeGemini()
        analyzer.cloud_llm = None
        androids = [
            {"title": "Phone 1", "value_score": 90},
            {"title": "Phone 2", "value_score": 80},
        ]

        result = analyzer._run_ai_analysis_pipeline(androids, top_count=2)

        assert analyzer.gemini.calls == [2]
        assert all(p["gemini_analysis"]["analyzed"] for p in result)

    def test_fetched_description_rescores_and_resorts(self):
        """A description fetched in step 6 changes the score and the order (#2)"""
        analyzer = AndroidAnalyzer(enrich_with_kimovil=False)
        androids = [
            {"title": "Samsung S22 8/128", "price": 200000, "link": "b"},
            {"title": "Samsung S23 Ultra 12/256", "price": 200000, "link": "a"},
        ]

        def fake_fetch(phones, top_count):
            for phone in phones[:top_count]:
                if phone["link"] == "a":
                    phone["description"] = "на запчасти, не включается"
            return phones

        with (
            patch.object(analyzer, "_load_androids_from_session", return_value=androids),
            patch.object(analyzer, "_fetch_top_phone_details", side_effect=fake_fetch),
        ):
            result = analyzer.analyze_all_androids()

        assert [p["link"] for p in result] == ["b", "a"]
        assert "🔧 For parts" in result[1]["value_factors"]
