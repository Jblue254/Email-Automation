import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
app = Flask(__name__)

try:
    client = MongoClient(MONGO_URI)
    db = client.email_automation_db 
    subscribers_collection = db.subscribers
    campaigns_collection = db.campaigns
    print("API Server connected to MongoDB.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit(1)

def format_campaign(campaign):
    """Converts MongoDB document to JSON serializable dict."""
    campaign['id'] = str(campaign.pop('_id'))
   
    campaign['schedule_time'] = campaign['schedule_time'].isoformat()
    campaign['created_at'] = campaign['created_at'].isoformat()
    return campaign



@app.route('/')
def index():
    """Renders the single page application (SPA) template."""
    return render_template('index.html')



@app.route('/api/subscribers', methods=['GET', 'POST'])
def handle_subscribers():
    if request.method == 'GET':
        subs = list(subscribers_collection.find().sort("joined_at", -1).limit(50))
        for sub in subs:
            sub['id'] = str(sub.pop('_id'))
            sub['joined_at'] = sub['joined_at'].isoformat()
        return jsonify(subs)

    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({"message": "Email is required"}), 400
        
        result = subscribers_collection.update_one(
            {"email": data['email']},
            {"$set": {
                "name": data.get('name', ''),
                "status": "active",
                "joined_at": datetime.utcnow()
            }},
            upsert=True
        )
        return jsonify({"message": "Subscriber added/updated", "id": str(result.upserted_id or result.modified_count)})

@app.route('/api/campaigns', methods=['GET', 'POST'])
def handle_campaigns():
    if request.method == 'GET':
        camps = list(campaigns_collection.find().sort("schedule_time", -1))
        camps = [format_campaign(c) for c in camps]
        return jsonify(camps)

    elif request.method == 'POST':
        data = request.get_json()
        
        if not all(k in data for k in ['name', 'subject', 'body_html']):
            return jsonify({"message": "Missing required fields"}), 400
        
        schedule_time_str = data.get('schedule_time')
        if schedule_time_str:
             try:
                 schedule_time = datetime.fromisoformat(schedule_time_str)
             except ValueError:
                 return jsonify({"message": "Invalid schedule_time format. Use ISO 8601."}), 400
        else:
             schedule_time = datetime.utcnow() + timedelta(minutes=5)
             
        
        campaign_doc = {
            "name": data['name'],
            "subject": data['subject'],
            "body_html": data['body_html'],
            "schedule_time": schedule_time,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "sent_count": 0
        }
        
        result = campaigns_collection.insert_one(campaign_doc)
        return jsonify({"message": "Campaign scheduled", "id": str(result.inserted_id)})


@app.route('/api/campaigns/<campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    """Deletes a campaign document from MongoDB by its ID."""
    try:
        
        result = campaigns_collection.delete_one({"_id": ObjectId(campaign_id), "status": "pending"})
        
        if result.deleted_count == 1:
            return jsonify({"message": f"Campaign {campaign_id} deleted successfully."}), 200
        else:

            return jsonify({"message": "Campaign not found, already completed, or ID is invalid."}), 404
            
    except Exception as e:
        
        return jsonify({"message": f"Error processing request: Invalid ID format."}), 400


if __name__ == '__main__':
    
    if subscribers_collection.count_documents({}) == 0:
        subscribers_collection.insert_one({
            "email": "test@example.com",
            "name": "Test User",
            "status": "active",
            "joined_at": datetime.utcnow()
        })
        print("API Server: Added a default subscriber for testing.")
        
    app.run(debug=True, port=5000, use_reloader=False) 