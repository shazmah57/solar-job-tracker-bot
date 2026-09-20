import json
from datetime import datetime
from jobspy import scrape_jobs

# Countries we want to search for Solar jobs
COUNTRIES = [
    "USA", "Canada", "Australia", 
    "New Zealand", "United Arab Emirates", "Saudi Arabia"
]

# Strict search terms — only strong solar signals
SEARCH_TERMS = [
    "Solar PV Engineer",
    "Solar Energy Engineer",
    "Solar Project Engineer",
    "Photovoltaic Engineer",
    "Solar Design Engineer",
    "Solar Electrical Engineer",
]

# Title must contain ONE of these to be kept (case-insensitive)
TITLE_KEYWORDS = [
    "solar", "pv", "photovoltaic", "renewable energy", "renewables",
    "bess", "energy storage",
]

# Title must NOT contain any of these (junk filters)
TITLE_EXCLUDE = [
    "sales", "marketing", "recruiter", "accountant", "finance",
    "legal", "counsel", "intern", "graduate", "co-op", "coop",
    "apprentice", "technician",
]


def is_solar_role(title: str) -> bool:
    """Strict filter: title must contain a solar keyword AND not be junk."""
    if not title:
        return False
    lower = title.lower()
    has_keyword = any(kw in lower for kw in TITLE_KEYWORDS)
    has_exclude = any(ex in lower for ex in TITLE_EXCLUDE)
    return has_keyword and not has_exclude


def main():
    all_jobs = []
    seen_urls = set()  # dedupe across countries/terms

    for country in COUNTRIES:
        for term in SEARCH_TERMS:
            print(f"Scraping '{term}' in {country}...")

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
                    print("  No jobs found")
                    continue

                kept = 0
                for _, job in jobs.iterrows():
                    title = str(job.get("title", "")).strip()
                    url = str(job.get("job_url", "")).strip()

                    # Skip duplicates
                    if url in seen_urls:
                        continue

                    # Strict solar filter
                    if not is_solar_role(title):
                        continue

                    seen_urls.add(url)
                    all_jobs.append({
                        "title": title,
                        "company": str(job.get("company", "")),
                        "location": str(job.get("location", "")),
                        "posted_date": str(job.get("date_posted", "")),
                        "job_url": url,
                        "search_country": country,
                        "is_remote": bool(job.get("is_remote", False))
                    })
                    kept += 1

                print(f"  Kept {kept} of {len(jobs)} (solar-only filter)")

            except Exception as e:
                print(f"  Error: {e}")

    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_jobs": len(all_jobs),
        "jobs": all_jobs
    }

    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nTotal solar jobs saved: {len(all_jobs)}")


if __name__ == "__main__":
    main()
