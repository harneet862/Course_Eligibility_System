import re
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

def normalize_course_code(s: str) -> str:
    # Strip whitespace and normalize spaces. We keep letters + numbers + optional suffix.
    return re.sub(r'\s+', ' ', s.strip()).upper()

def split_top_level_and_groups(text: str) -> List[str]:
    """
    Heuristic: split top-level by ' and ' (as the main conjunction). 
    Each piece may contain alternatives separated by ' or ', commas, 'one of', or '/'.
    """
    # unify separators
    t = text.strip()
    # remove trailing notes like "or consent of instructor." by splitting on 'consent of'
    t = re.split(r'\bconsent of\b', t, flags=re.I)[0]
    # Replace common phrases to simplify parsing
    t = t.replace('one of:', 'one of').replace('one of', 'one of')
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)
    # Split by ' and ' as main separator (case-insensitive)
    parts = re.split(r'\s+\band\b\s+', t, flags=re.I)
    return [p.strip(' .;') for p in parts if p.strip()]

def extract_alternatives(piece: str) -> List[str]:
    """
    Given a piece that may contain alternatives, return list of course codes/names that satisfy this piece.
    Heuristics handle:
      - "A or B"
      - "A, B, or C" or "A, B" (commas)
      - "one of A, B, C"
      - slashes "A/B"
    Returns normalized course codes (strings).
    """
    p = piece
    # If phrase starts with "one of", strip it
    p = re.sub(r'^\s*one of\s*[:\-]?\s*', '', p, flags=re.I)
    # split on ' or ' first
    alt = re.split(r'\s+\bor\b\s+', p, flags=re.I)
    # if there's still commas in entries, break those up
    candidates = []
    for a in alt:
        # replace '/' with comma to split as alternatives as well
        a = a.replace('/', ',')
        # split by commas and semicolons
        subparts = re.split(r'\s*,\s*|\s*;\s*', a)
        for s in subparts:
            s = s.strip()
            if not s:
                continue
            # Try to capture course codes using regex: e.g., "BIOCH 200", "CHEM 102", "3 units in BIOCH" => ignore the '3 units' bits
            # We'll capture patterns like AAAAA 000 (letters+space+digits+optional suffix)
            m = re.search(r'([A-Z]{2,5}\s*\d{2,4}[A-Z]?)', s.upper())
            if m:
                candidates.append(normalize_course_code(m.group(1)))
            else:
                # fallback: if the token looks like "BIOCH" or contains letters+digits glue, take token
                token = re.sub(r'[^A-Z0-9 ]', '', s.upper())
                token = token.strip()
                if re.match(r'^[A-Z]{2,5}\s*\d{2,4}[A-Z]?$', token):
                    candidates.append(normalize_course_code(token))
                # else ignore text like "consent of instructor" or "60 units"
    # Remove duplicates while preserving order
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out

def parse_prereq_line(line: str) -> Tuple[str, List[List[str]]]:
    """
    Parse a single line like:
      'BIOCH 310 : BIOCH 200, CHEM 102 (or SCI 100) and CHEM 263 with a minimum GPA...'
    Return:
      course_code, requirements
      where requirements is a list of requirement-groups (each group is a list of alternatives)
      e.g. [['BIOCH 200'], ['CHEM 102','SCI 100'], ['CHEM 263']]
    """
    if ':' not in line:
        return None, []
    left, right = line.split(':', 1)
    course = normalize_course_code(left)
    req_text = right.strip()
    # If right side is like 'consent of instructor' or empty, return empty requirements
    if re.search(r'\bconsent of\b', req_text, flags=re.I) or req_text.strip()=='':
        return course, []
    # heuristics: split by top-level 'and'
    parts = split_top_level_and_groups(req_text)
    requirements = []
    for p in parts:
        alts = extract_alternatives(p)
        if alts:
            requirements.append(alts)
        # else: could be "60 units" or "90 units" or "third year standing" — ignore for code-based prereq graph
    return course, requirements

def load_and_parse(file_path: str) -> Dict[str, List[List[str]]]:
    """
    Reads the prereq file, returns dict:
      course_code -> list of requirement groups (each group is list of alternatives)
    """
    parsed = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            # ignore lines that don't look like "CODE : ..." ?
            if ':' not in line:
                # try to join with previous? For simplicity, skip
                continue
            course, reqs = parse_prereq_line(line)
            if course:
                # if duplicate lines appear, combine requirements (extend)
                if course in parsed and reqs:
                    parsed[course].extend(reqs)
                else:
                    parsed.setdefault(course, []).extend(reqs)
    return parsed


def build_graph(parsed_reqs: Dict[str, List[List[str]]]) -> Tuple[Dict[str, Set[str]], Dict[str,int]]:
    """
    Build directed graph edges: prereq_course -> course
    Returns adjacency dict and indegree map for all encountered courses.
    """
    adj = defaultdict(set)
    indeg = defaultdict(int)
    all_courses = set(parsed_reqs.keys())
    # include all prerequisites nodes too
    for course, req_groups in parsed_reqs.items():
        all_courses.add(course)
        for group in req_groups:
            for prereq in group:
                all_courses.add(prereq)
                if course not in adj[prereq]:
                    adj[prereq].add(course)
    # compute indegrees
    for node in all_courses:
        indeg[node] = 0
    for u, neighbors in adj.items():
        for v in neighbors:
            indeg[v] += 1
    return adj, indeg

def kahn_topological_sort(adj: Dict[str, Set[str]], indeg: Dict[str,int]) -> Tuple[List[str], bool]:
    """
    Returns (ordering, is_cycle)
    ordering is a list of nodes in topological order if no cycle; if cycle present ordering contains processed nodes.
    is_cycle True if cycle detected.
    """
    q = deque([n for n,d in indeg.items() if d==0])
    order = []
    indeg_copy = indeg.copy()
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj.get(u, []):
            indeg_copy[v] -= 1
            if indeg_copy[v]==0:
                q.append(v)
    is_cycle = len(order) != len(indeg)
    return order, is_cycle

def is_requirement_satisfied(group: List[str], completed: Set[str]) -> bool:
    """
    A requirement group is satisfied if any alternative in the group is in completed.
    """
    return any(alt in completed for alt in group)

def course_is_eligible(course: str, req_groups: List[List[str]], completed: Set[str]) -> bool:
    """
    Course is eligible if every requirement group is satisfied (AND across groups; OR inside group).
    Courses with zero req_groups are considered eligible (unless other constraints like '60 units' present — ignored).
    """
    if not req_groups:
        return True
    return all(is_requirement_satisfied(g, completed) for g in req_groups)

def eligible_courses(parsed_reqs: Dict[str, List[List[str]]], completed_courses: Set[str]) -> Set[str]:
    """
    Return set of courses from parsed_reqs that student is eligible to take (i.e., prereqs satisfied).
    Excludes courses already completed.
    """
    eligible = set()
    for course, req_groups in parsed_reqs.items():
        if course in completed_courses:
            continue
        if course_is_eligible(course, req_groups, completed_courses):
            eligible.add(course)
    return eligible

def scrape_course_prereqs_example(page_html: str) -> List[Tuple[str,str]]:
    """
    Template: given the HTML of a course catalog page or list, use BeautifulSoup to extract (course_code, prereq_text).
    You will likely need to adapt selectors based on the site structure.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_html, 'html.parser')
    results = []
    # Example heuristics (customize):
    # - Course entries might be in <div class="course"> <h3>COURSE CODE</h3> <p class="prereq">Prerequisite: ...</p>
    for block in soup.select('.course, .course-entry'):
        code_tag = block.select_one('.course-code, h3, .title')
        prereq_tag = block.select_one('.prereq, .prerequisites, p:contains("Prerequisite")')
        if code_tag:
            code = normalize_course_code(code_tag.get_text())
            prereq_text = prereq_tag.get_text() if prereq_tag else ''
            # strip label "Prerequisite:" if present
            prereq_text = re.sub(r'(?i)Prerequisites?:\s*', '', prereq_text).strip()
            results.append((code, prereq_text))
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Course prereq engine demo")
    parser.add_argument('--file', default='prereq.txt', help='path to prereq.txt')
    parser.add_argument('--completed', default='', help='comma-separated completed courses, e.g. "CHEM 102,BIOCH 200"')
    args = parser.parse_args()

    parsed = load_and_parse(args.file)
    print(f"Parsed {len(parsed)} courses with explicit prereq patterns (file: {args.file})")

    adj, indeg = build_graph(parsed)
    order, is_cycle = kahn_topological_sort(adj, indeg)
    if is_cycle:
        print("Cycle detected in prereq graph (cannot fully topologically sort). Partial order printed.")
    else:
        print("Topological ordering computed (one possible valid ordering).")
    # show first 30 of ordering
    print("Sample ordering (first 30):", order[:30])

    completed = set([normalize_course_code(x) for x in args.completed.split(',') if x.strip()])
    elig = eligible_courses(parsed, completed)
    print(f"Based on completed={completed}, you are eligible for {len(elig)} courses. Sample:", list(sorted(elig))[:20])
