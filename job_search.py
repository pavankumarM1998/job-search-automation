import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from scrapfly import ScrapflyClient, ScrapeConfig

# === Load Secrets from GitHub Actions ===
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SCRAPFLY_KEY = os.environ.get("SCRAPFLY_KEY")
RECIPIENT_EMAIL = "pavankumar.m1432@gmail.com"

# === Job Keywords and Filters ===
KEYWORDS = ["SQL Developer", "SSIS Developer", "Power BI Developer", "Data Analyst"]
FILTER_SKILLS = ["SQL", "SSIS", "Power BI", "Data Analysis", "ETL"]

# === Scrapfly Client ===
client = ScrapflyClient(key=SCRAPFLY_KEY)

# === Scraping Functions ===
def extract_apollo_state(result):
    import json
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    data = json.loads(data)
    return data["props"]["pageProps"]["apolloState"]["data"]

async def scrape_wellfound(role: str):
    url = f"https://wellfound.com/role/l/{role.replace(' ', '-').lower()}"
    result = await client.async_scrape(ScrapeConfig(url=url, asp=True))
    return extract_apollo_state(result)

def parse_jobs(apollo_data):
    jobs = []
    for key, node in apollo_data.items():
        if key.startswith("StartupResult:") and "jobListingsConnection" in node:
            conn = node["jobListingsConnection({\"after\":\"\",\"first\":10})"]
            if "edges" in conn:
                for edge in conn["edges"]:
                    job_node = edge.get("node", {})
                    jobs.append({
                        "title": job_node.get("title", "No Title"),
                        "company": node.get("name", "Unknown"),
                        "snippet": job_node.get("descriptionSnippet", ""),
                        "url": f"https://wellfound.com/jobs/{job_node.get('slug','')}"
                    })
    return jobs

# === Email Function ===
def send_email(subject, body):
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

# === Main Logic ===
def main():
    loop = asyncio.get_event_loop()
    all_jobs = []

    for role in KEYWORDS:
        try:
            apollo = loop.run_until_complete(scrape_wellfound(role))
            jobs = parse_jobs(apollo)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"Error scraping {role}: {e}")

    # Filter jobs by resume skills
    filtered = [j for j in all_jobs if any(skill.lower() in (j["title"] + j["snippet"]).lower() for skill in FILTER_SKILLS)]

    if not filtered:
        print("No matching jobs found today.")
        return

    # Build email content
    content = "<h2>Today's Startup Job Matches</h2><ul>"
    for job in filtered:
        content += f"<li><a href='{job['url']}'>{job['title']} at {job['company']}</a><br>{job['snippet']}</li>"
    content += "</ul>"

    # Send email
    send_email("Daily Startup Job Matches", content)
    print(f"Sent {len(filtered)} job matches to {RECIPIENT_EMAIL}")

if __name__ == "__main__":
    main()
