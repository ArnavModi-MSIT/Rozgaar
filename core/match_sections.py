"""Deterministic section parsing and explainable skill weighting, all local."""
import re
from core.skills import build_patterns, extract_skills
from core.experience import extract_min_experience

HEADINGS = {
    "required": r"(?:basic|minimum|required) qualifications|requirements|essential skills|what you bring|what you need",
    "preferred": r"preferred qualifications|preferred skills|nice to have|bonus skills",
    "responsibilities": r"responsibilities|job description|what you.ll do|your role|about the role",
    "projects": r"projects|personal projects|academic projects|selected projects",
    "experience": r"experience|work experience|professional experience|internships",
    "skills": r"skills|technical skills|technologies",
    "education": r"education|academic qualifications",
}

def sections(text):
    result = {key: [] for key in ["general", *HEADINGS]}
    active = "general"
    # Preserve heading boundaries from common HTML and plain-text formats.
    text = re.sub(r"</?(?:p|div|li|h[1-6]|br)\b[^>]*>", "\n", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    for line in text.splitlines():
        line = line.strip(" \t:*•-#")
        if not line:
            continue
        heading, sep, remainder = line.partition(":")
        found = next((key for key, pattern in HEADINGS.items()
                      if re.fullmatch(pattern, heading.strip(), re.I)), None)
        if found:
            active = found
            if sep and remainder.strip():
                result[active].append(remainder.strip())
        else:
            result[active].append(line)
    return {key: "\n".join(lines) for key, lines in result.items()}

def job_parts(title, description):
    parts = sections(description)
    required = parts["required"]
    responsibilities = parts["responsibilities"] or parts["general"]
    return [f"{title}\n{required or responsibilities}",
            f"{title}\n{responsibilities or required}"]

def resume_parts(text):
    parts = sections(text)
    evidence = "\n".join(filter(None, [parts["projects"], parts["experience"]]))
    relevant = "\n".join(filter(None, [parts["skills"], evidence]))
    return [relevant or text, evidence or relevant or text], bool(evidence)

def weighted_skills(description, stored_skills, resume_skills):
    parts = sections(description)
    patterns = build_patterns(set(stored_skills) | set(resume_skills))
    required = extract_skills(parts["required"], patterns)
    preferred = extract_skills(parts["preferred"], patterns) - required
    for line in re.split(r"\n+|(?<=[.!?])\s+", parts["general"] + "\n" + parts["responsibilities"]):
        if re.search(r"\b(preferred|nice to have|desirable|a plus)\b", line, re.I):
            preferred |= extract_skills(line, patterns)
        if re.search(r"\b(must have|required|mandatory|essential)\b", line, re.I) and not re.search(r"\b(preferred|nice to have)\b", line, re.I):
            required |= extract_skills(line, patterns)
    preferred -= required
    all_skills = set(stored_skills) | extract_skills(description, patterns) | required | preferred
    weights = {skill: 3 if skill in required else 1 if skill in preferred else 2 for skill in all_skills}
    denominator = sum(weights.values())
    pct = 100 * sum(weight for skill, weight in weights.items() if skill in resume_skills) / denominator if denominator else None
    return pct, required, preferred, all_skills

def eligibility_checks(description, location, resume_text, missing_required):
    """Do not infer employment years from project dates or assume student eligibility."""
    from core.location import parse_country
    years = extract_min_experience(description)
    explicit = re.search(r"\b(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:professional|work|industry)\s+experience\b", resume_text, re.I)
    candidate = int(explicit.group(1)) if explicit else None
    experience_status = "unknown" if years is None or candidate is None else "mismatch" if candidate < years else "meets stated requirement"
    if years == 0:
        experience_status = "meets stated requirement"
    checks = [{"label": "Experience", "status": experience_status,
               "evidence": f"Posting minimum: {years if years is not None else 'unknown'} years; resume work experience: {candidate if candidate is not None else 'unknown'} years."}]
    country = parse_country(location or "")
    checks.append({"label": "India location", "status": "unknown" if country == "Unknown" else "meets stated requirement" if country == "India" else "mismatch", "evidence": location or "No location supplied."})
    parts = sections(description)
    for label, pattern in [("Graduation / student status", r"[^\n.!?]*(?:graduat|enrolled|pursuing|student|class of|batch)[^\n.!?]*"),
                           ("Education", r"[^\n.!?]*(?:degree|bachelor|master|diploma)[^\n.!?]*")]:
        lines = re.findall(pattern, parts["required"] or description or "", re.I)
        status = "unknown"
        # Restrict year comparison to explicitly stated graduation years, not
        # education start dates, application deadlines or internship seasons.
        year_pattern = r"(?:graduat(?:ing|ion)(?:\s+(?:year|date))?|class of|batch)(?:\s*[:\-]?\s*(?:in|of|expected)?\s*)(20[2-4]\d)\b"
        candidate_years = set(re.findall(year_pattern, resume_text, re.I))
        required_years = set(re.findall(year_pattern, parts["required"], re.I))
        if label == "Graduation / student status" and len(candidate_years) == 1 and len(required_years) == 1:
            status = "meets stated requirement" if candidate_years == required_years else "mismatch"
            lines.append("Resume stated graduation year: " + next(iter(candidate_years)))
        checks.append({"label": label, "status": status, "evidence": " | ".join(lines[:3]) or "No explicit requirement identified; verify the posting."})
    checks.append({"label": "Required skills", "status": "mismatch" if missing_required else "unknown", "evidence": "Not found in resume skills: " + ", ".join(sorted(missing_required)) if missing_required else "No recognized required skill gap; this does not prove proficiency or eligibility."})
    return checks
