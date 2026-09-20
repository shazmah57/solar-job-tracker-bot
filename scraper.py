import json
from datetime import datetime
from jobspy import scrape_jobs

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

# Which job sites to scrape. LinkedIn is confirmed working.
# Bayt and Glassdoor are being tested — if they return nothing, remove them.
SITES = ["linkedin", "bayt", "glassdoor"]


def is_solar_role(title: str) -> bool:
    if not title:
        return False
    lower = title.lower()
    has_keyword = any(kw in lower for kw in TITLE_KEYWORDS)
    has_exclude = any(ex in lower for ex in TITLE_EXCLUDE)
    return has_keyword and not has_exclude


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


def format_date(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat", ""):
        return ""
    return s


def main():
    all_jobs = []
    seen_urls = set()
    source_counts = {}

    for site in SITES:
        print(f"\n=== Scraping from {site} ===")
        source_counts[site] = 0

        for country in COUNTRIES:
            for term in SEARCH_TERMS:
                print(f"  '{term}' in {country}...")
                try:
                    jobs = scrape_jobs(
                        site_name=[site],
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

                        if url in seen_urls:
                            continue
                        if not is_solar_role(title):
                            continue

                        seen_urls.add(url)
                        all_jobs.append({
                            "title": title,
                            "company": safe_str(job.get("company")),
                            "location": safe_str(job.get("location")),
                            "posted_date": format_date(job.get("date_posted")),
                            "salary": format_salary(job),
                            "job_url": url,
                            "search_country": country,
                            "is_remote": bool(job.get("is_remote", False)),
                            "source": site,
                        })
                        kept += 1
                        source_counts[site] += 1

                    if kept > 0:
                        print(f"    Kept {kept}")

                except Exception as e:
                    print(f"    Error: {e}")

    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_jobs": len(all_jobs),
        "source_counts": source_counts,
        "jobs": all_jobs
    }

    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n=== Summary ===")
    for site, count in source_counts.items():
        print(f"{site}: {count} jobs")
    print(f"Total: {len(all_jobs)} jobs")


if __name__ == "__main__":
    main()
