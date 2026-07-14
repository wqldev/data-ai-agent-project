"""Multi-agent analysis pipeline: Planner → Builder → Verifier.

Compatible with OpenAI-compatible providers that do not support
native response_format / json_schema structured outputs.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, TypeVar

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from json_repair import repair_json
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from .sales_data import get_sales_dataset_text

set_tracing_disabled(True)

T = TypeVar("T", bound=BaseModel)

REJECT_MESSAGE = "请重新描述您的需求，只支持数据分析类问题。"

JSON_OUTPUT_RULES = (
    "输出必须是严格合法的 JSON 对象。\n"
    "- 不要输出 JSON 以外的任何文字\n"
    "- 字符串内的双引号必须转义为 \\\"\n"
    "- 换行写成 \\n，禁止在字符串值中直接换行\n"
    "- 不要尾随逗号\n"
    "- 字段值尽量简短，列表每项一句话\n"
)


class QuestionGate(BaseModel):
    is_data_analysis: bool = Field(
        description="是否为数据分析类问题（趋势/对比/归因/假设/经营指标等）"
    )
    reason: str = Field(description="简要判定理由")


class AcceptanceCriterion(BaseModel):
    id: str = Field(description="标准编号，如 A1")
    description: str = Field(description="可验证的接受标准描述")


class AnalysisPlan(BaseModel):
    goal: str = Field(description="分析目标一句话概括")
    subtasks: list[str] = Field(description="拆解后的子任务列表")
    analysis_type: str = Field(description="分析类型，如趋势/对比/归因/假设")
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        description="报告必须满足的接受标准"
    )
    data_needs: list[str] = Field(description="需要用到的数据维度")


class AnalysisReport(BaseModel):
    title: str
    executive_summary: str
    findings: list[str]
    evidence: list[str]
    recommendations: list[str]
    raw_markdown: str = Field(
        default="",
        description="可选；完整 Markdown。可留空，由服务端根据字段组装",
    )


class CriterionCheck(BaseModel):
    id: str
    description: str
    passed: bool
    comment: str


class VerificationResult(BaseModel):
    passed: bool = Field(description="是否整体通过验证")
    score: float = Field(description="0-100 的符合度评分")
    checks: list[CriterionCheck]
    summary: str
    final_report_markdown: str = Field(
        default="",
        description="可选；最终报告 Markdown。可留空，由服务端组装",
    )


@dataclass
class LLMConfig:
    api_base: str
    api_key: str
    model: str


def _normalize_base_url(api_base: str) -> str:
    base = api_base.strip().rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    return base


def _make_client(cfg: LLMConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=_normalize_base_url(cfg.api_base),
        api_key=cfg.api_key,
        timeout=90.0,
    )


def _make_model(cfg: LLMConfig) -> OpenAIChatCompletionsModel:
    return OpenAIChatCompletionsModel(model=cfg.model, openai_client=_make_client(cfg))


def _compact_schema(model: type[BaseModel]) -> str:
    """Short field list instead of full JSON Schema (reduces prompt noise)."""
    props = model.model_json_schema().get("properties", {})
    lines = [f"- {name}: {meta.get('description') or meta.get('type', 'any')}" for name, meta in props.items()]
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("模型返回为空")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()

    candidates = [raw]
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])

    errors: list[str] = []
    for candidate in candidates:
        for attempt in (candidate, repair_json(candidate)):
            try:
                data = attempt if isinstance(attempt, dict) else json.loads(attempt)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                errors.append(str(exc))

    raise ValueError(
        "无法从模型输出解析 JSON"
        + (f"（{errors[-1]}）" if errors else "")
        + f"：{text[:400]}"
    )


def _parse_output(text: str, model: type[T], stage: str = "") -> T:
    try:
        data = _extract_json_object(text)
        return model.model_validate(data)
    except (ValidationError, ValueError) as exc:
        prefix = f"[{stage}] " if stage else ""
        raise ValueError(f"{prefix}结构化解析失败：{exc}") from exc


def _assemble_report_markdown(report: AnalysisReport) -> str:
    if report.raw_markdown.strip():
        return report.raw_markdown.strip()
    lines = [
        f"# {report.title}",
        "",
        "## 摘要",
        report.executive_summary,
        "",
        "## 关键发现",
        *[f"- {item}" for item in report.findings],
        "",
        "## 数据证据",
        *[f"- {item}" for item in report.evidence],
        "",
        "## 建议",
        *[f"- {item}" for item in report.recommendations],
    ]
    return "\n".join(lines)


def _assemble_final_markdown(
    verification: VerificationResult, report: AnalysisReport
) -> str:
    if verification.final_report_markdown.strip():
        return verification.final_report_markdown.strip()
    status = "验证结果：通过" if verification.passed else "验证结果：未通过"
    checks = "\n".join(
        f"- {'✓' if c.passed else '✗'} {c.id} {c.description} — {c.comment}"
        for c in verification.checks
    )
    body = _assemble_report_markdown(report)
    return (
        f"**{status}**（{verification.score:.0f} 分）\n\n"
        f"{verification.summary}\n\n"
        f"### 验收明细\n{checks}\n\n"
        f"---\n\n{body}"
    )


@function_tool
def fetch_sales_data() -> str:
    """获取内置近12个月销售样例数据（月度、品类、区域）。"""
    return get_sales_dataset_text()


def _gate(cfg: LLMConfig) -> Agent:
    return Agent(
        name="GateAgent",
        instructions=(
            "你是问题分类器。判断用户输入是否属于「数据分析类问题」。\n"
            "数据分析类包括：销售/经营/指标的趋势、对比、归因、假设、结构拆解、"
            "品类/区域表现、异常诊断、预测建议等。\n"
            "非数据分析类包括：闲聊、写作、翻译、编程、百科、天气、笑话、"
            "与业务数据无关的通用问答等。\n"
            "边界情况：若只是含糊提到数据但无分析意图，判为 false。\n"
            f"{JSON_OUTPUT_RULES}"
            "字段：\n"
            f"{_compact_schema(QuestionGate)}"
        ),
        model=_make_model(cfg),
    )


def _planner(cfg: LLMConfig) -> Agent:
    return Agent(
        name="PlannerAgent",
        instructions=(
            "你是数据分析规划专家（Planner）。\n"
            "任务：把用户的分析问题拆解为可执行子任务，明确分析类型，"
            "并定义 3-5 条可客观验证的接受标准（Acceptance Criteria）。\n"
            "要求：\n"
            "1. 接受标准必须可检验。\n"
            "2. 只做规划，不要编造具体销售数字。\n"
            f"{JSON_OUTPUT_RULES}"
            "字段：\n"
            f"{_compact_schema(AnalysisPlan)}"
        ),
        model=_make_model(cfg),
    )


def _builder(cfg: LLMConfig) -> Agent:
    return Agent(
        name="BuilderAgent",
        instructions=(
            "你是数据分析执行专家（Builder）。\n"
            "你必须先调用工具 fetch_sales_data 获取销售数据，再输出结构化结论。\n"
            "要求：\n"
            "1. 严格依据工具返回的数据，不得捏造数据中不存在的数字。\n"
            "2. 覆盖 Planner 给出的子任务与数据需求。\n"
            "3. findings / evidence / recommendations 各给 3-5 条短句。\n"
            "4. raw_markdown 请留空字符串 \"\"，由系统组装正文。\n"
            f"{JSON_OUTPUT_RULES}"
            "字段：\n"
            f"{_compact_schema(AnalysisReport)}"
        ),
        model=_make_model(cfg),
        tools=[fetch_sales_data],
    )


def _verifier(cfg: LLMConfig) -> Agent:
    return Agent(
        name="VerifierAgent",
        instructions=(
            "你是质量验证专家（Verifier）。\n"
            "对照 Planner 的接受标准，逐条检查 Builder 报告是否达标。\n"
            "规则：\n"
            "1. 全部标准通过则 passed=true，否则 passed=false。\n"
            "2. score 按通过比例折算到 0-100。\n"
            "3. final_report_markdown 请留空字符串 \"\"，由系统组装。\n"
            f"{JSON_OUTPUT_RULES}"
            "字段：\n"
            f"{_compact_schema(VerificationResult)}"
        ),
        model=_make_model(cfg),
    )


ProgressEvent = dict[str, Any]


async def test_llm_connection(cfg: LLMConfig) -> dict[str, Any]:
    client = AsyncOpenAI(
        base_url=_normalize_base_url(cfg.api_base),
        api_key=cfg.api_key,
        timeout=20.0,
    )
    resp = await client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": "请只回复：OK"}],
        max_tokens=16,
        temperature=0,
    )
    content = (resp.choices[0].message.content or "").strip()
    return {"ok": True, "reply": content, "model": cfg.model}


def _as_text(final_output: Any) -> str:
    if final_output is None:
        return ""
    if isinstance(final_output, str):
        return final_output
    return str(final_output)


async def run_analysis_stream(
    question: str, cfg: LLMConfig
) -> AsyncIterator[ProgressEvent]:
    """Yield progress events, then a final result event."""
    yield {
        "type": "stage",
        "stage": "gate",
        "status": "running",
        "message": "正在判断问题是否属于数据分析类…",
    }

    gate_result = await Runner.run(
        _gate(cfg),
        f"用户输入：{question}",
    )
    gate = _parse_output(_as_text(gate_result.final_output), QuestionGate, "gate")

    if not gate.is_data_analysis:
        yield {
            "type": "stage",
            "stage": "gate",
            "status": "done",
            "message": "判定为非数据分析问题",
            "data": gate.model_dump(),
        }
        yield {
            "type": "rejected",
            "message": REJECT_MESSAGE,
            "reason": gate.reason,
        }
        return

    yield {
        "type": "stage",
        "stage": "gate",
        "status": "done",
        "message": "判定为数据分析问题，进入分析流水线",
        "data": gate.model_dump(),
    }

    yield {
        "type": "stage",
        "stage": "planner",
        "status": "running",
        "message": "Planner 正在拆解任务并定义接受标准…",
    }

    plan_result = await Runner.run(
        _planner(cfg),
        f"用户分析问题：{question}",
    )
    plan = _parse_output(_as_text(plan_result.final_output), AnalysisPlan, "planner")
    yield {
        "type": "stage",
        "stage": "planner",
        "status": "done",
        "message": "Planner 完成",
        "data": plan.model_dump(),
    }

    yield {
        "type": "stage",
        "stage": "builder",
        "status": "running",
        "message": "Builder 正在取数并生成分析报告…",
    }

    builder_input = (
        f"用户问题：{question}\n\n"
        f"分析计划（JSON）：\n{plan.model_dump_json()}\n\n"
        "请调用 fetch_sales_data 获取数据，然后只输出符合字段要求的 JSON。"
        "raw_markdown 填空字符串。"
    )
    report_result = await Runner.run(_builder(cfg), builder_input)
    report = _parse_output(_as_text(report_result.final_output), AnalysisReport, "builder")
    report = report.model_copy(update={"raw_markdown": _assemble_report_markdown(report)})
    yield {
        "type": "stage",
        "stage": "builder",
        "status": "done",
        "message": "Builder 完成",
        "data": report.model_dump(),
    }

    yield {
        "type": "stage",
        "stage": "verifier",
        "status": "running",
        "message": "Verifier 正在对照接受标准验证报告…",
    }

    # Keep verifier input compact — omit long markdown to reduce bad JSON risk.
    compact_report = {
        "title": report.title,
        "executive_summary": report.executive_summary,
        "findings": report.findings,
        "evidence": report.evidence,
        "recommendations": report.recommendations,
    }
    verify_input = (
        f"用户问题：{question}\n\n"
        f"接受标准：\n{json.dumps([c.model_dump() for c in plan.acceptance_criteria], ensure_ascii=False)}\n\n"
        f"待验证报告：\n{json.dumps(compact_report, ensure_ascii=False)}\n\n"
        "请只输出 JSON。final_report_markdown 填空字符串。"
    )
    verify_result = await Runner.run(_verifier(cfg), verify_input)
    verification = _parse_output(
        _as_text(verify_result.final_output), VerificationResult, "verifier"
    )
    final_md = _assemble_final_markdown(verification, report)
    verification = verification.model_copy(update={"final_report_markdown": final_md})
    yield {
        "type": "stage",
        "stage": "verifier",
        "status": "done",
        "message": "Verifier 完成",
        "data": verification.model_dump(),
    }

    yield {
        "type": "final",
        "passed": verification.passed,
        "score": verification.score,
        "plan": plan.model_dump(),
        "report": report.model_dump(),
        "verification": verification.model_dump(),
        "final_markdown": final_md,
    }


async def run_analysis(question: str, cfg: LLMConfig) -> dict[str, Any]:
    final: dict[str, Any] | None = None
    events: list[ProgressEvent] = []
    async for event in run_analysis_stream(question, cfg):
        events.append(event)
        if event.get("type") in {"final", "rejected"}:
            final = event
    if final is None:
        raise RuntimeError("分析流水线未产生最终结果")
    return {"events": events, "result": final}
