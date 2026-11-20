import re
from app.services.advisor.prompts import COMPLIANCE_DISCLAIMER, DISCLAIMER_TRIGGER_KEYWORDS

# Regex to match direct advice on specific brand name funds/stocks
# Examples: "Buy HDFC Top 100 Fund", "invest in SBI Bluechip Mutual Fund", "Sell Tata Motors Stock"
DIRECT_RECOMMENDATION_REGEX = re.compile(
    r'\b(?:buy|sell|invest\s+in)\s+(?:hdfc|icici|sbi|axis|tata|bajaj|reliance|quantum|hdb|dsp|franklin|kotak|nippon|uti|mirae|aditya\s+birla|parag\s+parikh|motilal\s+oswal|canara\s+robeco|bandhan)\b[^.\n]*',
    re.IGNORECASE
)


def apply_output_guardrails(content: str) -> tuple[str, str | None]:
    """
    Scans the final assistant response and applies Layer 2 output compliance rules.
    
    Returns:
        (cleaned_content, disclaimer | None)
        
    - `cleaned_content` is the response text, sanitized if any direct buy/sell/invest
      recommendation of specific financial products is detected.
    - `disclaimer` is the SEBI compliance disclaimer string if investment keywords are detected,
      or None if this response has no investment advice.
      
    The disclaimer is intentionally NOT appended to the content string. It is returned
    separately so the caller can attach it to AIMessage.additional_kwargs["disclaimer"],
    enabling the frontend to render it with distinct styling (e.g. highlighted small text).
    """
    # 1. Apply Sub-function A: Filter direct buy/sell/invest recommendation of specific brand products
    def replace_match(match):
        matched_str = match.group(0).lower()
        if "sell" in matched_str:
            return "consider rebalancing your holdings based on your target asset allocation"
        else:
            return "consider a suitable category-level investment aligned with your risk profile"
            
    sanitized_content = DIRECT_RECOMMENDATION_REGEX.sub(replace_match, content)
    
    # 2. Apply Sub-function B: Check if any investment-related trigger keyword is present
    content_lower = sanitized_content.lower()
    disclaimer_needed = any(kw in content_lower for kw in DISCLAIMER_TRIGGER_KEYWORDS)
    
    disclaimer = COMPLIANCE_DISCLAIMER if disclaimer_needed else None
    return sanitized_content, disclaimer
