"""LangChain-based agent: RAG retrieval → Deepseek NL → structured steps."""
import json
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from knowledge import retrieve_context

DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
MAX_HISTORY = 6  # keep last 3 rounds (6 messages)


def _get_llm() -> ChatOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        openai_api_key=api_key,
        openai_api_base=DEEPSEEK_BASE,
        temperature=0.1,
        max_tokens=2048,
    )


def _build_messages(
    user_message: str,
    schema_info: str,
    rag_context: str,
    history: list[dict],
) -> list:
    """Build full message list: system + few-shot + history + current user input."""
    system_content = SYSTEM_PROMPT.replace(
        "{context}", rag_context or "（未检索到相关业务知识）"
    )

    messages = [SystemMessage(content=system_content)]

    # insert few-shot examples
    for ex in FEW_SHOT_EXAMPLES:
        messages.append(HumanMessage(content=ex["user"]))
        messages.append(AIMessage(content=ex["assistant"]))

    # insert conversation history (most recent rounds)
    for entry in history[-MAX_HISTORY:]:
        messages.append(HumanMessage(content=entry["user"]))
        messages.append(AIMessage(content=entry["assistant"]))

    # current user input with schema hint
    schema_hint = f"数据列信息: {schema_info}\n用户指令: {user_message}"
    messages.append(HumanMessage(content=schema_hint))

    return messages


def _parse_response(raw: str) -> list[dict]:
    """Parse LLM response text into step list JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]) if lines[0].startswith("```") else raw
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()
    return json.loads(raw)


def parse_instruction(
    user_message: str,
    schema_info: str,
    history: list[dict] | None = None,
) -> list[dict]:
    """Full pipeline: RAG retrieve → build prompt → LLM → parse JSON steps.

    Args:
        user_message: user's natural language instruction
        schema_info: string describing current data columns and types
        history: list of {"user": ..., "assistant": ...} dicts from prior turns

    Returns:
        list of step dicts with 'action' and 'params'
    """
    llm = _get_llm()

    # Step 1: RAG retrieval
    rag_context = retrieve_context(user_message)

    # Step 2: build messages
    messages = _build_messages(user_message, schema_info, rag_context, history or [])

    # Step 3: call LLM
    response = llm.invoke(messages)
    raw = response.content.strip()

    # Step 4: parse JSON, with retry on failure
    try:
        steps = _parse_response(raw)
    except json.JSONDecodeError:
        messages.append(HumanMessage(content="你返回的不是合法 JSON。请只返回纯 JSON 数组。"))
        response = llm.invoke(messages)
        steps = _parse_response(response.content.strip())

    return steps, raw
