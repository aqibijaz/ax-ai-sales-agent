def score_lead(budget_max: int | None, timeline_days: int | None, authority: str, clarity: int) -> int:
    b = 5 if not budget_max or budget_max < 3000 else 15 if budget_max < 5000 else 28 if budget_max < 10000 else 40
    t = 20 if timeline_days and timeline_days <= 28 else 16 if timeline_days and timeline_days <= 60 else 10 if timeline_days and timeline_days <= 120 else 5
    a = {"dm": 20, "influencer": 12, "unknown": 8, "no": 5}.get(authority or "unknown", 8)
    c = min(20, max(0, clarity))
    return min(100, b + t + a + c)

def status_from_score(s: int) -> str:
    return "hot" if s >= 80 else "warm" if s >= 50 else "cold"
