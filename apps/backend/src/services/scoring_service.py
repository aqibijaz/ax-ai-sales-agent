"""
Lead Scoring Algorithm

Scoring breakdown:
- Budget: 40% weight
- Timeline urgency: 20% weight
- Decision-making authority: 20% weight
- Project clarity: 20% weight

Score ranges:
- 80-100: Hot lead (immediate follow-up required)
- 50-79: Warm lead (follow up within 24 hours)
- 0-49: Cold lead (nurture via email campaign)
"""

def score_lead(
    budget_max: int,
    timeline_days: int,
    authority: str,
    clarity_score: int
) -> int:
    """
    Calculate lead quality score (0-100)
    
    Args:
        budget_max: Maximum budget in USD
        timeline_days: Project timeline in days
        authority: Decision-making authority ("dm", "influencer", "unknown", "no")
        clarity_score: Project clarity score 0-100 (from conversation analysis)
    
    Returns:
        int: Score between 0 and 100
    """
    # --- BUDGET SCORING (40% weight) ---
    # Normalize to 0-100 scale based on $0-$20,000 range
    budget_normalized = min(max(budget_max, 0), 20000)
    budget_score = round((budget_normalized / 20000) * 100)
    
    # --- TIMELINE SCORING (20% weight) ---
    # Shorter timeline = higher urgency = higher score
    if timeline_days <= 30:  # 1 month or less
        timeline_score = 100
    elif timeline_days <= 60:  # 2 months
        timeline_score = 85
    elif timeline_days <= 90:  # 3 months
        timeline_score = 70
    elif timeline_days <= 180:  # 6 months
        timeline_score = 50
    else:  # More than 6 months
        timeline_score = 30
    
    # --- AUTHORITY SCORING (20% weight) ---
    # Decision-maker has most weight
    authority_map = {
        "dm": 100,           # Decision maker
        "influencer": 70,    # Can influence decision
        "unknown": 40,       # Not sure yet
        "no": 10             # Not a decision maker
    }
    authority_score = authority_map.get(authority.lower() if authority else "unknown", 40)
    
    # --- CLARITY SCORING (20% weight) ---
    # How clear is the project scope (0-100)
    clarity_normalized = max(0, min(100, clarity_score))
    
    # --- WEIGHTED CALCULATION ---
    final_score = (
        0.40 * budget_score +
        0.20 * timeline_score +
        0.20 * authority_score +
        0.20 * clarity_normalized
    )
    
    return int(round(final_score))


def status_from_score(score: int) -> str:
    """
    Convert numeric score to lead status category
    
    Args:
        score: Lead score (0-100)
    
    Returns:
        str: "hot", "warm", or "cold"
    """
    if score >= 80:
        return "hot"
    elif score >= 50:
        return "warm"
    else:
        return "cold"


def calculate_clarity_score(conversation_messages: list) -> int:
    """
    Heuristic to calculate project clarity from conversation.
    This is a simple implementation - can be enhanced with ML.
    
    Args:
        conversation_messages: List of conversation messages
    
    Returns:
        int: Clarity score (0-100)
    """
    score = 50  # Start at baseline
    
    # Check for key indicators of clarity
    full_text = " ".join([msg.get("content", "").lower() for msg in conversation_messages])
    
    # Positive indicators (increase score)
    if "exactly" in full_text or "specifically" in full_text:
        score += 10
    if "feature" in full_text or "functionality" in full_text:
        score += 10
    if "example" in full_text or "like" in full_text:
        score += 5
    if any(word in full_text for word in ["user", "customer", "admin", "dashboard"]):
        score += 10
    if any(word in full_text for word in ["payment", "authentication", "database", "api"]):
        score += 10
    
    # Negative indicators (decrease score)
    if "not sure" in full_text or "maybe" in full_text or "probably" in full_text:
        score -= 15
    if "don't know" in full_text or "no idea" in full_text:
        score -= 20
    if full_text.count("?") > len(conversation_messages):  # Too many questions from user
        score -= 10
    
    # Message count factor (more messages usually means better clarity)
    if len(conversation_messages) >= 10:
        score += 10
    elif len(conversation_messages) <= 3:
        score -= 10
    
    # Normalize to 0-100 range
    return max(0, min(100, score))


def get_recommended_actions(score: int, status: str) -> list:
    """
    Get recommended actions based on lead score and status
    
    Args:
        score: Lead score (0-100)
        status: Lead status ("hot"/"warm"/"cold")
    
    Returns:
        list: Recommended actions for sales team
    """
    actions = []
    
    if status == "hot":
        actions = [
            "🔥 URGENT: Contact within 1 hour",
            "📞 Schedule call immediately",
            "💼 Prepare custom proposal",
            "🎯 Assign to senior sales rep",
            "📧 Send case studies and portfolio"
        ]
    elif status == "warm":
        actions = [
            "📅 Follow up within 24 hours",
            "📨 Send educational content",
            "🔄 Add to nurture sequence",
            "📊 Share pricing guide",
            "🤝 Offer free consultation"
        ]
    else:  # cold
        actions = [
            "📧 Add to email drip campaign",
            "📚 Send resources and guides",
            "🔔 Set reminder for 1 week follow-up",
            "💡 Offer free value (ebook, checklist)",
            "🎓 Invite to webinar or workshop"
        ]
    
    return actions