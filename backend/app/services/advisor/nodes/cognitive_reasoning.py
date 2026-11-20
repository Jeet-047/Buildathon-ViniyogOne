import time
from datetime import datetime
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from app.core.llm import get_llm
from app.services.advisor.prompts import COGNITIVE_REASONING_BASE_PROMPT
from app.services.advisor.tools import web_search, request_human_input
from app.core.logger import get_logger, SessionLoggerAdapter

logger = get_logger("advisor.node.cognitive_reasoning")


def format_inr(val: Any) -> str:
    """Formats numeric value into Indian Rupee style (e.g. ₹50,000)."""
    try:
        num = float(val)
        return f"₹{num:,.0f}" if num.is_integer() else f"₹{num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def format_demographics_md(profile: Dict[str, Any]) -> str:
    lines = ["#### 👤 User Demographics & Life Stage"]
    name = profile.get("name", "User")
    age = profile.get("age", "N/A")
    occ = profile.get("occupation", "N/A")
    loc = profile.get("location", "N/A")
    stage = profile.get("life_stage", "N/A")
    risk = profile.get("risk_profile", "N/A")
    income = profile.get("income_bracket", "N/A")
    tax = profile.get("tax_slab", "N/A")
    lines.append(f"- **Name & Age**: {name}, {age} years")
    lines.append(f"- **Occupation & Location**: {occ} | {loc}")
    lines.append(f"- **Life Stage & Risk Posture**: {stage} | Risk Profile: {risk.upper() if isinstance(risk, str) else risk}")
    lines.append(f"- **Income Bracket & Tax Bracket**: {income} | Tax Bracket: {tax}")
    return "\n".join(lines)


def format_behavioral_md(bi: Dict[str, Any]) -> str:
    lines = ["#### 🧠 Behavioral Intelligence & Living Cashflow Memory"]

    # 1. Cashflow Summary
    cf = bi.get("cash_flow_summary", {})
    if cf:
        inflow = format_inr(cf.get("avg_monthly_income_inr", 0))
        outflow = format_inr(cf.get("avg_monthly_expense_inr", 0))
        investment = format_inr(cf.get("avg_monthly_investment_inr", 0))
        surplus = format_inr(cf.get("net_monthly_surplus_inr", 0))
        savings_rate = cf.get("savings_rate_pct", 0)
        volatility = format_inr(cf.get("monthly_surplus_volatility_inr", 0))
        liquid_balance = format_inr(cf.get("latest_liquid_balance_inr", 0))

        lines.append(f"- **Monthly Cash Flow**: Income: {inflow} | Expenses: {outflow} | Investments: {investment} | Net Surplus: {surplus}")
        lines.append(f"- **Savings & Liquidity**: Savings Rate: {savings_rate:.1f}% | Liquid Bank Balance: {liquid_balance} | Surplus Volatility (σ): ±{volatility}")

    # 2. Behavioral Signals
    signals = bi.get("behavioral_signals", {})
    if signals:
        signal_bullets = []
        if signals.get("lifestyle_inflation_detected"):
            growth = signals.get("lifestyle_spend_growth_pct", 0)
            signal_bullets.append(f"Lifestyle Inflation Detected (+{growth:.1f}% increase in discretionary spending)")
        else:
            signal_bullets.append("Lifestyle Inflation: Not Detected (Spending stable)")

        sip = signals.get("sip_regularity", {})
        if sip and sip.get("total_sip_amount_inr", 0) > 0:
            signal_bullets.append(f"SIP Discipline: {format_inr(sip.get('monthly_sip_avg_inr', 0))}/month ({sip.get('detected_monthly_sips', 0)} months active, consistency score: {sip.get('consistency_score', 1.0)})")

        debt = signals.get("debt_metrics", {})
        if debt and debt.get("monthly_emi_inr", 0) > 0:
            signal_bullets.append(f"Debt Obligations: {format_inr(debt.get('monthly_emi_inr', 0))}/month (EMI Burden: {debt.get('emi_burden_ratio_pct', 0):.1f}% of income)")

        runway = signals.get("emergency_runway_months")
        if runway is not None:
            signal_bullets.append(f"Emergency Runway: {runway:.1f} months of living expenses covered")

        stability = signals.get("spending_stability")
        if stability:
            signal_bullets.append(f"Spending Stability Grade: {stability}")

        if signal_bullets:
            lines.append("- **Behavioral Signals & Financial Habits**:")
            for s in signal_bullets:
                lines.append(f"  • {s}")

    # 3. Category Breakdown Highlights
    breakdown = bi.get("category_breakdown", {})
    if breakdown:
        top_cats = []
        for cat_name, data in list(breakdown.items())[:6]:
            avg = format_inr(data.get("monthly_avg_inr", 0))
            pct = data.get("pct_of_total_outflow", 0)
            cat_type = data.get("category_type", "expense")
            top_cats.append(f"{cat_name} ({cat_type}): {avg}/mo ({pct:.1f}%)")
        lines.append(f"- **Key Category Allocations**: {'; '.join(top_cats)}")

    # 4. Key Behavioral Observations & Risk Alerts
    obs = bi.get("key_behavioral_observations", [])
    if obs:
        lines.append("- **Factual Behavioral Observations & Alerts**:")
        for o in obs:
            lines.append(f"  • {o}")

    return "\n".join(lines)


async def cognitive_reasoning_node(state: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Reasoning Task: Performs advanced cognitive reasoning using Vertex AI gemini-3.1-pro-preview
    with selectively hydrated user_profile, behavioral_insights, and ReAct tools.
    """
    session_id = config.get("configurable", {}).get("thread_id", "global") if config else "global"
    log = SessionLoggerAdapter(logger, session_id)
    log.info("── NODE: Cognitive_Reasoning (Reasoning Task - gemini-3.1-pro-preview ReAct Loop)")

    # Reasoning task model: gemini-3.1-pro-preview
    llm = get_llm(model_type="reasoning", temperature=0.0)
    tools = [web_search, request_human_input]

    user_profile = state.get("user_profile", {})
    behavioral_insights = state.get("behavioral_insights", {})

    messages = state.get("messages", [])
    recent_messages = messages[-5:]

    context_blocks = []
    profile_has_demographics = any(k not in ("user_id", "persona_id", "category") for k in user_profile.keys())
    if user_profile and profile_has_demographics:
        context_blocks.append(format_demographics_md(user_profile))

    if behavioral_insights:
        context_blocks.append(format_behavioral_md(behavioral_insights))

    log.info(f"   Structured context blocks: profile={bool(profile_has_demographics)}, behavioral_insights={bool(behavioral_insights)}")

    current_date_str = datetime.now().strftime("%B %d, %Y")
    system_prompt = f"Current Date: {current_date_str}\n\n" + COGNITIVE_REASONING_BASE_PROMPT
    if context_blocks:
        system_prompt += "\n\n### User Financial & Behavioral Context:\n" + "\n\n".join(context_blocks)
    else:
        system_prompt += "\n\nNote: No personal financial details are currently loaded for this request."

    agent = create_react_agent(llm, tools, prompt=system_prompt)

    start_time = time.time()
    agent_input = {"messages": recent_messages}
    agent_output = await agent.ainvoke(agent_input)
    duration = time.time() - start_time

    new_messages = agent_output["messages"][len(recent_messages):]
    log.info(f"   ReAct Agent completed: generated {len(new_messages)} message(s) ({duration:.2f}s)")

    return {"messages": new_messages}
