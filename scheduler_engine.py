import os
import time
from datetime import datetime, timedelta, timezone 
from pymongo import MongoClient
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

try:
    
    client = MongoClient(MONGO_URI)
    db = client.email_automation_db
    subscribers_collection = db.subscribers
    campaigns_collection = db.campaigns
    print("Scheduler Engine connected to MongoDB.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
   
    exit(1)

def send_email_via_esp(recipient_email, subject, body_html):
    """
    Simulates calling an Email Service Provider API (e.g., SendGrid, Mailgun).
    """
    print(f"  --> SENDING: '{subject}' to {recipient_email}")
    time.sleep(0.05) 
    return True 

def check_and_send_scheduled_emails():
    """
    The main scheduler job. Runs every 60 seconds to process due campaigns.
    """
    now = datetime.now(timezone.utc) 
    print(f"\n[{now.strftime('%H:%M:%S UTC')}] Scheduler checking for due campaigns...")
    
    due_campaigns = campaigns_collection.find({
        "status": "pending",
        "schedule_time": {"$lte": now} 
    })
    
    found_due = False
    for campaign in due_campaigns:
        found_due = True
        campaign_id = campaign["_id"]
        campaign_name = campaign.get('name', 'Untitled')
        print(f"--- Processing campaign: {campaign_name} (ID: {campaign_id}) ---")
        
        
        active_subscribers = subscribers_collection.find({"status": "active"})
        
        sent_count = 0

        for subscriber in active_subscribers:
            recipient = subscriber.get("email")
            subject = campaign.get("subject", "Automated Email")
            body = campaign.get("body_html", "Default Content")
            
            if send_email_via_esp(recipient, subject, body):
                sent_count += 1
                
        campaigns_collection.update_one(
            {"_id": campaign_id},
            {"$set": {
                "status": "completed",
                "sent_on": now,
                "sent_count": sent_count
            }}
        )
        print(f"Campaign '{campaign_name}' COMPLETED. Sent {sent_count} emails.")
    
    if not found_due:
        print("No campaigns found to send.")


if __name__ == '__main__':
    print("Starting Email Automation Engine (APScheduler)...")
    
    scheduler = BlockingScheduler()
    
   
    scheduler.add_job(
        func=check_and_send_scheduled_emails, 
        trigger="interval", 
        seconds=60,
        id='email_automation_job'
    )
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
        pass