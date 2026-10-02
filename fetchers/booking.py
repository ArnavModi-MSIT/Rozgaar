"""booking public India listings with full descriptions."""
from . import jibe

def collect(deadline=None):
    return jibe.collect("booking", "jobs.booking.com", "/booking/jobs", deadline)
