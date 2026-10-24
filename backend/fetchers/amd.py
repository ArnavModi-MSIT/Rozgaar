"""amd public India listings with full descriptions."""
from . import jibe

def collect(deadline=None):
    return jibe.collect("amd", "careers.amd.com", "/jobs", deadline)
