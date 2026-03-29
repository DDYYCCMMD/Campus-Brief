"""
pipeline.py — 核心 AI 处理流水线
三步 workflow: Classify → Extract → Plan
支持 DEMO_MODE（本地 mock）和真实 API 两种模式
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

from src.prompts import CLASSIFICATION_PROMPT, EXTRACTION_PROMPT, ACTION_CARD_PROMPT, NAIVE_SUMMARY_PROMPT
from src.utils import (
    clean_json_response,
    ensure_action_card_structure,
    ensure_structured_data,
    get_demo_result,
    guess_demo_result,
    safe_get,
)

# Load .env from project root (one level up from src/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# 复用 client 实例，避免每次调用都重新创建
_client = None


def _get_client():
    """获取或创建 MiniMax API client（单例模式）"""
    global _client
    if _client is None:
        api_key = os.getenv("API_KEY", "")
        base_url = os.getenv("BASE_URL", "https://api.minimaxi.com/v1")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _get_model():
    """获取模型名称"""
    return os.getenv("MODEL_NAME", "MiniMax-M2.5")


def _call_llm(prompt: str) -> str:
    """调用 LLM，返回原始文本响应"""
    client = _get_client()
    model = _get_model()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
        timeout=60,
    )
    return response.choices[0].message.content or ""


def is_demo_mode() -> bool:
    """检查是否为演示模式"""
    return os.getenv("DEMO_MODE", "true").lower() == "true"


# 分类→提取策略描述映射，用于 workflow log 展示 AI 深度
_TYPE_FOCUS = {
    "assignment": "deliverables, grading criteria, submission format, and group requirements",
    "competition": "rules, team size, judging criteria, and competition phases",
    "event": "date/time/venue, registration, roles, and preparation items",
    "exam": "exam schedule, topics covered, allowed materials, and format",
    "application": "eligibility, required documents, selection process, and benefits",
    "notice": "what changed, who is affected, required actions, and effective dates",
}


# ============================================================
# Step 1: Task Classification — 识别文本类型
# ============================================================
def classify_task(text: str) -> tuple:
    """
    分类输入文本的任务类型
    返回: (task_type, confidence)
    task_type: assignment / competition / event / exam / application / notice
    confidence: high / medium / low
    """
    prompt = CLASSIFICATION_PROMPT.format(text=text[:3000])
    raw = _call_llm(prompt)
    result = clean_json_response(raw)
    task_type = safe_get(result, "task_type", "notice")
    confidence = safe_get(result, "confidence", "medium")

    valid_types = {"assignment", "competition", "event", "exam", "application", "notice"}
    if task_type not in valid_types:
        task_type = "notice"

    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    return task_type, confidence


# ============================================================
# Step 2: Structured Extraction — 结构化信息提取
# ============================================================
def extract_info(text: str, task_type: str) -> dict:
    """
    从文本中提取结构化信息
    返回包含 objective, requirements, deliverables, deadlines 等字段的字典
    """
    prompt = EXTRACTION_PROMPT.format(text=text[:3000], task_type=task_type)
    raw = _call_llm(prompt)
    result = clean_json_response(raw)
    return ensure_structured_data(result)


# ============================================================
# Step 3: Action Planning — 生成 Action Card
# ============================================================
def generate_action_card(text: str, structured_data: dict) -> dict:
    """
    基于结构化数据生成最终的 Action Card
    返回包含 5 个模块的 Action Card 字典
    """
    structured_str = json.dumps(structured_data, indent=2, ensure_ascii=False)
    prompt = ACTION_CARD_PROMPT.format(
        text=text[:3000],
        structured_data=structured_str,
    )
    raw = _call_llm(prompt)
    result = clean_json_response(raw)
    return ensure_action_card_structure(result)


# ============================================================
# Naive Summary — 用于对比展示
# ============================================================
def generate_naive_summary(text: str) -> str:
    """调用 LLM 生成一段普通摘要，用于和 Action Card 做对比"""
    prompt = NAIVE_SUMMARY_PROMPT.format(text=text[:3000])
    raw = _call_llm(prompt)
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw)
    return raw.strip()


# ============================================================
# 主流程入口
# ============================================================
def run_pipeline(text: str, sample_name: str = "") -> dict:
    """
    运行完整的三步 pipeline
    - DEMO_MODE=true: 使用本地预设数据，不调用 API
    - DEMO_MODE=false: 调用真实 API，走 classify → extract → plan

    返回:
    {
        "task_type": str,
        "structured_data": dict,
        "action_card": dict,
        "naive_summary": str,
        "workflow_log": list,
    }
    """

    # ---- DEMO MODE ----
    if is_demo_mode():
        if sample_name:
            demo_data = get_demo_result(sample_name)
        else:
            demo_data = guess_demo_result(text)

        task_type = demo_data["task_type"]
        demo_data["confidence"] = "high"
        structured = demo_data["structured_data"]
        type_display = task_type.replace("_", " ").title()

        n_req = len(structured.get("key_requirements", []))
        n_ddl = len(structured.get("deadlines", []))
        n_miss = len(structured.get("missing_info", []))

        focus = _TYPE_FOCUS.get(task_type, "general fields")
        demo_data["workflow_log"] = [
            f"Classified as <strong>{type_display}</strong> (confidence: <strong>high</strong>) → switched to <strong>{task_type}</strong> extraction strategy",
            f"Type-specific focus: extracted <strong>{focus}</strong>",
            f"Extracted {n_req} requirements and {n_ddl} deadlines → fed into action planner",
            f"Identified {n_miss} missing/unclear items → surfaced as risk flags in Action Card",
        ]
        return demo_data

    # ---- API MODE ----
    try:
        t0 = time.time()

        task_type, confidence = classify_task(text)
        type_display = task_type.replace("_", " ").title()

        structured_data = extract_info(text, task_type)
        n_req = len(structured_data.get("key_requirements", []))
        n_ddl = len(structured_data.get("deadlines", []))
        n_miss = len(structured_data.get("missing_info", []))

        action_card = generate_action_card(text, structured_data)

        try:
            naive_summary = generate_naive_summary(text)
        except Exception:
            naive_summary = "A generic summary could not be generated for this text. This comparison is unavailable."

        elapsed = round(time.time() - t0, 1)

        focus = _TYPE_FOCUS.get(task_type, "general fields")
        workflow_log = [
            f"Classified as <strong>{type_display}</strong> (confidence: <strong>{confidence}</strong>) → switched to <strong>{task_type}</strong> extraction strategy",
            f"Type-specific focus: extracted <strong>{focus}</strong>",
            f"Extracted {n_req} requirements and {n_ddl} deadlines → fed into action planner",
            f"Identified {n_miss} missing/unclear items → surfaced as risk flags in Action Card",
            f"Pipeline completed in <strong>{elapsed}s</strong> across 4 LLM calls",
        ]

        return {
            "task_type": task_type,
            "confidence": confidence,
            "structured_data": structured_data,
            "action_card": action_card,
            "naive_summary": naive_summary,
            "workflow_log": workflow_log,
        }

    except Exception as e:
        fallback = guess_demo_result(text)
        fallback["error"] = f"API Error: {str(e)}. Showing fallback results."
        fallback["workflow_log"] = []
        return fallback
