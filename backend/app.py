from flask import Flask, request, jsonify, render_template

from flask_cors import CORS
import requests
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)

# ---------- AMADEUS API ----------
AMADEUS_CLIENT_ID = "fpWYOXcCGewozi7G4CErelHzHA9fvIo0"
AMADEUS_CLIENT_SECRET = "PLg21oAcujKxzyGw"

def get_access_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET
    }
    r = requests.post(url, data=data)
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

# ---------- EMAIL SETTINGS ----------
GMAIL_EMAIL = "flyfairflights@gmail.com"
GMAIL_APP_PASSWORD = "ovkd omkz oggo lgoq"

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = GMAIL_EMAIL
    msg['To'] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

# ---------- FLIGHT PRICE CHECK ----------
@app.route('/check-price', methods=['GET'])
def check_price():
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    date = request.args.get('date')
    target_price = request.args.get('targetPrice')
    email = request.args.get('email')

    token = get_access_token()
    if not token:
        return jsonify({"error": "Failed to authenticate with Amadeus"}), 500

    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": date,
        "adults": 1,
        "currencyCode": "USD",
        "max": 5
    }

    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        return jsonify({"error": "Failed to fetch flight data"}), r.status_code

    data = r.json().get("data", [])
    simplified = []

    for offer in data:
        for itinerary in offer["itineraries"]:
            for segment in itinerary["segments"]:
                flight_info = {
                    "airline": r.json()["dictionaries"]["carriers"].get(segment["carrierCode"], segment["carrierCode"]),
                    "flight_number": segment["number"],
                    "departure": segment["departure"]["at"],
                    "arrival": segment["arrival"]["at"],
                    "origin": segment["departure"]["iataCode"],
                    "destination": segment["arrival"]["iataCode"],
                    "duration": itinerary["duration"],
                    "price": offer["price"]["total"],
                    "currency": offer["price"]["currency"]
                }
                simplified.append(flight_info)

                # Send email if price <= target
                if target_price and float(flight_info["price"]) <= float(target_price) and email:
                    subject = f"🎉 Flight Price Alert: {flight_info['airline']} {flight_info['flight_number']}"
                    body = f"""
Flight: {flight_info['airline']} {flight_info['flight_number']}
From: {flight_info['origin']} → To: {flight_info['destination']}
Departure: {flight_info['departure']}
Arrival: {flight_info['arrival']}
Duration: {flight_info['duration']}
Price: {flight_info['price']} {flight_info['currency']}
"""
                    send_email(email, subject, body)

    return jsonify(simplified)

if __name__ == "__main__":
    app.run(debug=True)
