"""Local, evidence-based requirement hints; unknown is never eligibility approval."""
import re
from backend.core.experience import experience_requirements
from backend.core.skills import extract_skills

def eligibility_evidence(description, resume_skills=(), title=""):
    text=description or ""
    chunks=[s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+",text) if s.strip()]
    education=[];graduation=[];mandatory=[];preferred=False
    for chunk in chunks:
        if re.search(r"\b(?:basic|required|minimum) qualifications\b",chunk,re.I):preferred=False
        if re.search(r"\bpreferred (?:qualifications|skills)\b",chunk,re.I):preferred=True
        if re.search(r"\b(?:bachelor|master|degree|diploma|B\.?Tech|B\.?E\.?|graduate)\b",chunk,re.I):education.append(chunk)
        if re.search(r"(?:graduat(?:e|ing|ion)|passing out|class of|batch)[^.!?]{0,70}\b20[2-4]\d\b",chunk,re.I):graduation.append(chunk)
        if not preferred and re.search(r"\b(?:required|must have|mandatory|essential|minimum qualifications)\b",chunk,re.I) and not re.search(r"\b(?:preferred|nice to have)\b",chunk,re.I):mandatory.append(chunk)
    skills=sorted(set().union(*(set(extract_skills(line)) for line in mandatory))) if mandatory else []
    years,_=experience_requirements(text,title)
    return {"minimum_years":years,"education_evidence":education[:6],"graduation_evidence":graduation[:6],"mandatory_skill_evidence":mandatory[:6],"mandatory_skills":skills,"missing_mandatory_skills":sorted(set(skills)-set(resume_skills)),"needs_review":True,"note":"Requirement hints, not an eligibility decision. Missing evidence means unknown; verify the original posting."}
