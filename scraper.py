import json
from datetime import datetime
import requests
from jobspy import scrape_jobs

# ==================== CONFIGURATION ====================
COUNTRIES = [
    "USA", "Canada", "Australia", 
    "New Zealand", "United Arab Emirates", "Saudi Arabia"
]

SEARCH_TERMS = [
    "Solar PV Engineer",
    "Solar Energy Engineer",
    "Solar Project Engineer",
    "Photovoltaic Engineer",
    "Solar Design Engineer",
    "Solar Electrical Engineer",
]

TITLE_KEYWORDS = [
    "solar", "pv", "photovoltaic", "renewable energy", "renewables",
    "bess", "energy storage",
]

TITLE_EXCLUDE = [
    "sales", "marketing", "recruiter", "accountant", "finance",
    "legal", "counsel", "intern", "graduate", "co-op", "coop",
    "apprentice", "technician",
]

# India exclusion — filters out India-based jobs
INDIA_KEYWORDS = ["india", "bangalore", "bengaluru", "mumbai", "delhi", 
                  "hyderabad", "pune", "chennai", "kolkata", "noida", "gurgaon"]

# Countries allowed for remote sources (to filter out India)
ALLOWED_COUNTRIES = ["usa", "united states", "canada", "australia", 
                     "new zealand", "uae", "united arab emirates", 
                     "saudi arabia", "saudi", "remote"]


# ==================== HELPERS ====================
def is_solar_role(title: str) -> bool:
    if not title:
        return False
    lower = title.lower()
    has_keyword = any(kw in lower for kw in TITLE_KEYWORDS)
    has_exclude = any(ex in lower for ex in TITLE_EXCLUDE)
    return has_keyword and not has_exclude


def is_india_job(location: str, title: str = "") -> bool:
    """Check if a job is India-based (to exclude)."""
    text = f"{location} {title}".lower()
    return any(kw in text for kw in INDIA_KEYWORDS)


def safe_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat"):
        return ""
    return s


def format_salary(row):
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    currency = safe_str(row.get("currency"))
    interval = safe_str(row.get("interval"))

    try:
        min_val = float(min_amt) if min_amt is not None else None
    except (ValueError, TypeError):
        min_val = None
    try:
        max_val = float(max_amt) if max_amt is not None else None
    except (ValueError, TypeError):
        max_val = None

    if min_val is None and max_val is None:
        return ""

    def fmt(v):
        if v is None:
            return ""
        if v >= 1000:
            return f"{int(v/1000)}k"
        return f"{int(v)}"

    curr = currency if currency else ""

    if min_val is not None and max_val is not None:
        return f"{curr} {fmt(min_val)}–{fmt(max_val)} {interval}".strip()
    if min_val is not None:
        return f"{curr} {fmt(min_val)}+ {interval}".strip()
    return f"{curr} up to {fmt(max_val)} {interval}".strip()


# ==================== SOURCE: LINKEDIN (via JobSpy) ====================
def scrape_linkedin():
    jobs_list = []
    print("=== LinkedIn ===")

    for country in COUNTRIES:
        for term in SEARCH_TERMS:
            print(f"  '{term}' in {country}...")
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=term,
                    location=country,
                    results_wanted=30,
                    hours_old=24,
                    country_indeed=country,
                    verbose=0
                )

                if jobs is None or len(jobs) == 0:
                    continue

                kept = 0
                for _, job in jobs.iterrows():
                    title = safe_str(job.get("title"))
                    url = safe_str(job.get("job_url"))
                    location = safe_str(job.get("location"))

                    if not is_solar_role(title):
                        continue
                    if is_india_job(location, title):
                        continue

                    jobs_list.append({
                        "title": title,
                        "company": safe_str(job.get("company")),
                        "location": location,
                        "posted_date": safe_str(job.get("date_posted")),
                        "salary": format_salary(job),
                        "job_url": url,
                        "search_country": country,
                        "is_remote": bool(job.get("is_remote", False)),
                        "source": "linkedin",
                    })
                    kept += 1

                if kept > 0:
                    print(f"    Kept {kept}")

            except Exception as e:
                print(f"    Error: {e}")

    return jobs_list


# ==================== SOURCE: HIMALAYAS (Free JSON API) ====================
def scrape_himalayas():
    """Himalayas free public API — no auth required [citation:5]."""
    jobs_list = []
    print("=== Himalayas ===")

    for term in SEARCH_TERMS:
        try:
            # Search endpoint with country filter for each target country
            for country in ["USA", "Canada", "Australia", "United Arab Emirates", "Saudi Arabia"]:
                url = "https://himalayas.app/jobs/api/search"
                params = {
                    "q": term,
                    "country": country,
                }
                resp = requests.get(url, params=params, timeout=20)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                jobs = data.get("jobs", [])

                kept = 0
                for job in jobs:
                    title = job.get("title", "")
                    location_restrictions = job.get("locationRestrictions", [])
                    location = ", ".join(location_restrictions) if location_restrictions else "Remote"

                    if not is_solar_role(title):
                        continue
                    if is_india_job(location, title):
                        continue

                    jobs_list.append({
                        "title": title,
                        "company": job.get("companyName", ""),
                        "location": location,
                        "posted_date": job.get("pubDate", ""),
                        "salary": _format_himalayas_salary(job),
                        "job_url": job.get("applicationLink") or job.get("guid", ""),
                        "search_country": country,
                        "is_remote": True,
                        "source": "himalayas",
                    })
                    kept += 1

                if kept > 0:
                    print(f"  '{term}' in {country}: {kept}")

        except Exception as e:
            print(f"  Error for '{term}': {e}")

    return jobs_list


def _format_himalayas_salary(job):
    min_s = job.get("minSalary")
    max_s = job.get("maxSalary")
    curr = job.get("currency", "")
    period = job.get("salaryPeriod", "")

    if not min_s and not max_s:
        return ""

    def fmt(v):
        if v is None:
            return ""
        if v >= 1000:
            return f"{int(v/1000)}k"
        return f"{int(v)}"

    if min_s and max_s:
        return f"{curr} {fmt(min_s)}–{fmt(max_s)} {period}".strip()
    if min_s:
        return f"{curr} {fmt(min_s)}+ {period}".strip()
    return f"{curr} up to {fmt(max_s)} {period}".strip()


# ==================== SOURCE: JOBICY (Free JSON API) ====================
def scrape_jobicy():
    """Jobicy free public API — no auth required [citation:2]."""
    jobs_list = []
    print("=== Jobicy ===")

    for term in SEARCH_TERMS:
        try:
            url = "https://jobicy.com/api/v2/remote-jobs"
            params = {
                "count": 50,
                "tag": term,
                "geo": "usa,canada,australia,new zealand,uae,saudi arabia",
            }
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                continue

            data = resp.json()
            jobs = data.get("jobs", [])

            kept = 0
            for job in jobs:
                title = job.get("jobTitle", "")
                location = job.get("jobGeo", "Remote")

                if not is_solar_role(title):
                    continue
                if is_india_job(location, title):
                    continue

                jobs_list.append({
                    "title": title,
                    "company": job.get("companyName", ""),
                    "location": location,
                    "posted_date": job.get("pubDate", ""),
                    "salary": _format_jobicy_salary(job),
                    "job_url": job.get("url", ""),
                    "search_country": "Remote",
                    "is_remote": True,
                    "source": "jobicy",
                })
                kept += 1

            if kept > 0:
                print(f"  '{term}': {kept}")

        except Exception as e:
            print(f"  Error for '{term}': {e}")

    return jobs_list


def _format_jobicy_salary(job):
    min_s = job.get("salaryMin")
    max_s = job.get("salaryMax")
    curr = job.get("salaryCurrency", "")
    period = job.get("salaryPeriod", "")

    if not min_s and not max_s:
        return ""

    def fmt(v):
        if v is None:
            return ""
        if v >= 1000:
            return f"{int(v/1000)}k"
        return f"{int(v)}"

    if min_s and max_s:
        return f"{curr} {fmt(min_s)}–{fmt(max_s)} {period}".strip()
    if min_s:
        return f"{curr} {fmt(min_s)}+ {period}".strip()
    return f"{curr} up to {fmt(max_s)} {period}".strip()


# ==================== SOURCE: REMOTEOK (Free JSON API) ====================
def scrape_remoteok():
    """RemoteOK free public API — no auth required [citation:1]."""
    jobs_list = []
    print("=== RemoteOK ===")

    try:
        url = "https://remoteok.com/api"
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}")
            return jobs_list

        data = resp.json()
        # First item is metadata, skip it
        jobs = [j for j in data if isinstance(j, dict) and "id" in j]

        kept = 0
        for job in jobs:
            title = job.get("position", "")
            location = job.get("location", "Remote")

            if not is_solar_role(title):
                continue
            if is_india_job(location, title):
                continue

            jobs_list.append({
                "title": title,
                "company": job.get("company", ""),
                "location": location,
                "posted_date": job.get("date", ""),
                "salary": _format_remoteok_salary(job),
                "job_url": job.get("url", "") or f"https://remoteok.com/remote-jobs/{job.get('id')}",
                "search_country": "Remote",
                "is_remote": True,
                "source": "remoteok",
            })
            kept += 1

        print(f"  Kept {kept} solar jobs")

    except Exception as e:
        print(f"  Error: {e}")

    return jobs_list


def _format_remoteok_salary(job):
    min_s = job.get("salary_min")
    max_s = job.get("salary_max")

    if not min_s and not max_s:
        return ""

    def fmt(v):
        if v is None:
            return ""
        if v >= 1000:
            return f"{int(v/1000)}k"
        return f"{int(v)}"

    if min_s and max_s:
        return f"USD {fmt(min_s)}–{fmt(max_s)} yearly".strip()
    if min_s:
        return f"USD {fmt(min_s)}+ yearly".strip()
    return f"USD up to {fmt(max_s)} yearly".strip()


# ==================== MAIN ====================
def main():
    all_jobs = []
    seen_urls = set()

    # Collect from all sources
    linkedin_jobs = scrape_linkedin()
    himalayas_jobs = scrape_himalayas()
    jobicy_jobs = scrape_jobicy()
    remoteok_jobs = scrape_remoteok()

    # Merge with deduplication
    for job in linkedin_jobs + himalayas_jobs + jobicy_jobs + remoteok_jobs:
        url = job.get("job_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_jobs.append(job)

    # Count by source
    source_counts = {}
    for job in all_jobs:
        src = job.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_jobs": len(all_jobs),
        "source_counts": source_counts,
        "jobs": all_jobs
    }

    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== Summary ===")
    for src, count in source_counts.items():
        print(f"{src}: {count}")
    print(f"Total: {len(all_jobs)}")


if __name__ == "__main__":
    main()
