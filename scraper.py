import json
from datetime import datetime
from jobspy import scrape_jobs

# Countries we want to search for Solar jobs
COUNTRIES = [
    "USA", "Canada", "Australia", 
    "New Zealand", "United Arab Emirates", "Saudi Arabia"
]

# Search terms to find Solar PV jobs
SEARCH_TERMS = [
    "Solar PV Engineer", 
    "Solar Energy Engineer", 
    "Solar Engineer"
]

def main():
    all_jobs = []
    
    for country in COUNTRIES:
        for term in SEARCH_TERMS:
            print(f"Scraping {term} in {country}...")
            
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
                
                if jobs is not None and len(jobs) > 0:
                    for _, job in jobs.iterrows():
                        all_jobs.append({
                            "title": str(job.get("title", "")),
                            "company": str(job.get("company", "")),
                            "location": str(job.get("location", "")),
                            "posted_date": str(job.get("date_posted", "")),
                            "job_url": str(job.get("job_url", "")),
                            "search_country": country,
                            "is_remote": bool(job.get("is_remote", False))
                        })
                    print(f"  Found {len(jobs)} jobs")
                else:
                    print(f"  No jobs found")
                    
            except Exception as e:
                print(f"  Error scraping {term} in {country}: {e}")
    
    # Save results to JSON file
    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_jobs": len(all_jobs),
        "jobs": all_jobs
    }
    
    with open("jobs.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nTotal jobs saved: {len(all_jobs)}")

if __name__ == "__main__":
    main()
