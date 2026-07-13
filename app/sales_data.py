"""Fixed sample sales dataset: last 12 months, categories, regions."""

from __future__ import annotations

from typing import Any


SALES_DATA: dict[str, Any] = {
    "meta": {
        "company": "星辰零售演示公司",
        "currency": "CNY",
        "period": "2025-07 ~ 2026-06",
        "description": "近12个月销售样例数据（虚拟）",
    },
    "monthly_revenue": [
        {"month": "2025-07", "revenue": 1280000, "orders": 4120, "avg_order_value": 310.7},
        {"month": "2025-08", "revenue": 1355000, "orders": 4305, "avg_order_value": 314.7},
        {"month": "2025-09", "revenue": 1428000, "orders": 4512, "avg_order_value": 316.5},
        {"month": "2025-10", "revenue": 1512000, "orders": 4788, "avg_order_value": 315.8},
        {"month": "2025-11", "revenue": 1685000, "orders": 5320, "avg_order_value": 316.7},
        {"month": "2025-12", "revenue": 1920000, "orders": 6105, "avg_order_value": 314.5},
        {"month": "2026-01", "revenue": 1460000, "orders": 4650, "avg_order_value": 314.0},
        {"month": "2026-02", "revenue": 1395000, "orders": 4420, "avg_order_value": 315.6},
        {"month": "2026-03", "revenue": 1558000, "orders": 4890, "avg_order_value": 318.6},
        {"month": "2026-04", "revenue": 1624000, "orders": 5055, "avg_order_value": 321.3},
        {"month": "2026-05", "revenue": 1710000, "orders": 5280, "avg_order_value": 323.9},
        {"month": "2026-06", "revenue": 1785000, "orders": 5460, "avg_order_value": 326.9},
    ],
    "by_category": [
        {"category": "电子产品", "revenue": 6850000, "share": 0.365, "yoy_growth": 0.18},
        {"category": "家居用品", "revenue": 4120000, "share": 0.220, "yoy_growth": 0.09},
        {"category": "服饰鞋包", "revenue": 3580000, "share": 0.191, "yoy_growth": 0.05},
        {"category": "美妆个护", "revenue": 2460000, "share": 0.131, "yoy_growth": 0.22},
        {"category": "食品饮料", "revenue": 1747000, "share": 0.093, "yoy_growth": 0.12},
    ],
    "by_region": [
        {"region": "华东", "revenue": 7250000, "share": 0.387, "yoy_growth": 0.15},
        {"region": "华南", "revenue": 4980000, "share": 0.266, "yoy_growth": 0.11},
        {"region": "华北", "revenue": 3560000, "share": 0.190, "yoy_growth": 0.08},
        {"region": "西南", "revenue": 1890000, "share": 0.101, "yoy_growth": 0.19},
        {"region": "其他", "revenue": 1077000, "share": 0.057, "yoy_growth": 0.06},
    ],
    "highlights": [
        "2025年双十一与双十二带动 Q4 显著冲高，12 月收入峰值 192 万。",
        "电子产品贡献约 36.5% 收入，是第一大品类。",
        "美妆个护同比增速最高（约 22%），西南区域增速领先（约 19%）。",
        "客单价从约 311 元稳步升至约 327 元。",
    ],
}


def get_sales_dataset_text() -> str:
    """Return a compact textual snapshot for LLM tools / prompts."""
    lines: list[str] = [
        f"数据集：{SALES_DATA['meta']['description']}",
        f"公司：{SALES_DATA['meta']['company']}",
        f"币种：{SALES_DATA['meta']['currency']}",
        f"周期：{SALES_DATA['meta']['period']}",
        "",
        "【月度收入】",
    ]
    for row in SALES_DATA["monthly_revenue"]:
        lines.append(
            f"- {row['month']}: 收入 {row['revenue']:,}，订单 {row['orders']:,}，"
            f"客单价 {row['avg_order_value']}"
        )
    lines.append("")
    lines.append("【品类】")
    for row in SALES_DATA["by_category"]:
        lines.append(
            f"- {row['category']}: 收入 {row['revenue']:,}，占比 {row['share']:.1%}，"
            f"同比 {row['yoy_growth']:.0%}"
        )
    lines.append("")
    lines.append("【区域】")
    for row in SALES_DATA["by_region"]:
        lines.append(
            f"- {row['region']}: 收入 {row['revenue']:,}，占比 {row['share']:.1%}，"
            f"同比 {row['yoy_growth']:.0%}"
        )
    lines.append("")
    lines.append("【要点】")
    for tip in SALES_DATA["highlights"]:
        lines.append(f"- {tip}")
    return "\n".join(lines)
