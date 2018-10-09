from .querygenerator import *
from .correctionqueries import *

def read_query_notes(query_str, first_line=False):
    """
    Returns the Comments from a query string that are in the header
    """
    lines = query_str.split("\n")
    started = False
    parts = []
    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            parts.append(line)
            started = True
            if first_line:
                break
        if started and line and not line.startswith("#"):
            break
    return "\n".join(parts)
