"""Career matching configuration. Restart the server after edits."""
import re

INCLUDE = re.compile(
    r"\b(intern|internship|trainee|apprentice|co-?op|"
    r"graduate program|campus hire|campus drive|entry.?level|"
    r"fresher|new ?grad)\b|"
    r"\b(20)?2[67]\b", re.I  # catches "batch 2027", "2027 grads", etc.
)


EXCLUDE = re.compile(
    r"\b(senior|staff|principal|lead|manager|director|head of|"
    r"internal|international|architect|\b[3-9]\+? ?years?\b|"
    r"[3-9]-\d+ ?years?)\b", re.I
)


LOCATION = re.compile(
    r"delhi|ncr|noida|gurugram|gurgaon|ghaziabad|faridabad|gautam buddha nagar", re.I
)


_FRESHER_SIGNAL = r"intern|internship|trainee|apprentice|co-?op|fresher|entry.?level|new ?grad|graduate|new college"


EXCLUDE_SENIOR = re.compile(
    r"\b(?:senior|sr|lead|manager|mgr|director|principal)\b\.?"
    rf"|^(?:(?!\b(?:{_FRESHER_SIGNAL})\b).)*\b(?:ii|iii|iv|v)\b\s*$"
    rf"|^(?:(?!\b(?:{_FRESHER_SIGNAL})\b).)*\b[2-9]\b\s*$",
    re.I,
)


TARGET_ROLE_RE = re.compile(
    r"\bdata (analyst|analytics|engineer|scientist)\b|"
    r"\bbusiness (analyst|intelligence)\b|"
    r"\banalytics engineer\b|"
    r"\bbi (analyst|developer|engineer)\b|"
    r"\breporting analyst\b|\binsights analyst\b|"
    r"\bmachine learning engineer\b|\bml engineer\b",
    re.I,
)


RELEVANCE_FILTERS = {}


STUDENT_TITLE_RE = re.compile(
    r"\b(intern(?:ship)?|apprentice(?:ship)?|student|summer analyst|"
    r"summer associate|industrial trainee|co[ -]?op)\b", re.I,
)
