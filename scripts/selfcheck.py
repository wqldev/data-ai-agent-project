"""Offline self-checks (no live LLM required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sales_data import SALES_DATA, get_sales_dataset_text  # noqa: E402
from app.pipeline import (  # noqa: E402
    AnalysisPlan,
    AnalysisReport,
    LLMConfig,
    VerificationResult,
    _extract_json_object,
    _normalize_base_url,
    _parse_output,
)


def test_sales_data() -> None:
    assert len(SALES_DATA["monthly_revenue"]) == 12
    assert len(SALES_DATA["by_category"]) >= 3
    assert len(SALES_DATA["by_region"]) >= 3
    text = get_sales_dataset_text()
    assert "电子产品" in text
    assert "华东" in text
    print("[ok] sales_data")


def test_normalize_url() -> None:
    assert _normalize_base_url("https://api.openai.com/v1/") == "https://api.openai.com/v1"
    assert (
        _normalize_base_url("https://api.deepseek.com/v1/chat/completions")
        == "https://api.deepseek.com/v1"
    )
    print("[ok] normalize_base_url")


def test_schemas() -> None:
    plan = AnalysisPlan(
        goal="分析近半年销售趋势",
        subtasks=["汇总月度收入", "对比品类"],
        analysis_type="趋势",
        acceptance_criteria=[{"id": "A1", "description": "给出趋势结论"}],
        data_needs=["月度收入", "品类"],
    )
    report = AnalysisReport(
        title="趋势报告",
        executive_summary="整体上行",
        findings=["Q4 冲高"],
        evidence=["12月收入192万"],
        recommendations=["加大美妆投放"],
        raw_markdown="# 报告\n整体上行",
    )
    verify = VerificationResult(
        passed=True,
        score=100,
        checks=[{"id": "A1", "description": "给出趋势结论", "passed": True, "comment": "已覆盖"}],
        summary="全部通过",
        final_report_markdown="✅ 验证结果：通过\n\n# 报告",
    )
    assert plan.goal
    assert report.title
    assert verify.passed
    print("[ok] schemas")


def test_static_files() -> None:
    for name in ("index.html", "styles.css", "app.js"):
        path = ROOT / "static" / name
        assert path.exists(), f"missing {name}"
        assert path.stat().st_size > 100
    print("[ok] static_files")


def test_llm_config() -> None:
    cfg = LLMConfig(api_base="https://api.openai.com/v1", api_key="sk-test", model="gpt-4o-mini")
    assert cfg.model == "gpt-4o-mini"
    print("[ok] llm_config")


def test_json_extract() -> None:
    raw = '这里是说明\n```json\n{"title":"t","executive_summary":"s","findings":["a"],"evidence":["b"],"recommendations":["c"],"raw_markdown":"# r"}\n```'
    data = _extract_json_object(raw)
    report = _parse_output(raw, AnalysisReport)
    assert data["title"] == "t"
    assert report.title == "t"
    print("[ok] json_extract")


if __name__ == "__main__":
    test_sales_data()
    test_normalize_url()
    test_schemas()
    test_static_files()
    test_llm_config()
    test_json_extract()
    print("\nAll offline checks passed.")
