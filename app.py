from flask import Flask, render_template, request, send_file
import csv
import sqlite3
import joblib
import re
import json
from datetime import datetime

app = Flask(__name__)

# ================= CSV EXPORT =================

@app.route("/export-csv")
def export_csv():

    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT
        message,
        prediction,
        spam,
        ham,
        risk,
        timestamp
    FROM history
    ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    filename = "history.csv"

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Message",
            "Prediction",
            "Spam %",
            "Ham %",
            "Risk Score",
            "Timestamp"
        ])

        writer.writerows(rows)

    return send_file(filename, as_attachment=True)


# ================= MODEL =================
model = joblib.load("model/spam_model.pkl")
vectorizer = joblib.load("model/vectorizer.pkl")


# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        prediction TEXT,
        spam REAL,
        ham REAL,
        risk REAL,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= HOME =================
@app.route("/", methods=["GET", "POST"])
def index():

    prediction = None
    spam = 0
    ham = 0
    risk_score = 0
    severity = "Low"

    category = "General"
    explanation = "No analysis yet"

    detected_keywords = []
    urls = []
    emails = []
    phones = []
    url_reputation = []

    if request.method == "POST":

        message = request.form.get("message", "").strip()

        if message:

            msg = message.lower()

            # ================= RULE ENGINE =================

            critical_patterns = [
                "bank account blocked",
                "account has been blocked",
                "verify immediately",
                "urgent verification",
                "otp",
                "click here",
                "claim prize",
                "you won",
                "lottery",
                "free gift",
                "cash reward",
                "suspended",
                "blocked",
                "free iphone",
                "free iphone 17",
                "claim now",
                "offer expires",
                "call immediately"
                "computer is infected",
                "infected with viruses",
                "contact support now",
                "your device is infected",
                "security warning"
            ]

            high_risk_keywords = [
                "bank",
                "upi",
                "otp",
                "verify",
                "urgent",
                "click",
                "claim",
                "reward",
                "winner",
                "lottery",
                "free",
                "gift",
                "iphone",
                "bonus",
                "limited",
                "offer",
                "expires",
                "immediately"
                "virus",
                "infected",
                "support",
                "malware",
                "hacked",
                "security alert",
                "technical support",
                "remote access"
            ]

            rule_score = 0

            for pattern in critical_patterns:
                if pattern in msg:
                    rule_score += 50
                    detected_keywords.append(pattern)

            for word in high_risk_keywords:
                if word in msg:
                    rule_score += 10
                    detected_keywords.append(word)

            # ================= ML MODEL =================

            X = vectorizer.transform([message])
            probs = model.predict_proba(X)[0]

            ham = round(probs[0] * 100, 2)
            spam = round(probs[1] * 100, 2)

            ml_pred = model.predict(X)[0]

            # ================= FINAL DECISION =================

            final_score = (spam * 0.6) + rule_score

            if final_score >= 60:
                prediction = "Spam"
            elif ml_pred == 1:
                prediction = "Spam"
            else:
                prediction = "Ham"

            # ================= DETECT INFO =================

            urls = re.findall(r'https?://\S+|www\.\S+', message)

            suspicious_domains = ["bit.ly", "tinyurl", ".xyz", ".tk", ".top", ".gq"]

            url_reputation = []

            for url in urls:
                
                status = "Unknown"
                for domain in suspicious_domains:
                    if domain in url.lower():
                        status = "Suspicious"
                        break
                if prediction == "Spam" and status == "Unknown":
                    status = "Potentially Dangerous"
                url_reputation.append((url, status))

            emails = re.findall(
                r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
                message
            )

            phones = re.findall(
                r'(\+91[\s\-]?\d{5}[\s\-]?\d{5}|\d{10})',
                message
                )

            # ================= RISK SCORE =================

            risk_score = 0

            risk_score += int(spam * 0.5)

            if urls:
                risk_score += 20

            if phones:
                risk_score += 10

            if emails:
                risk_score += 5

            risk_score += min(rule_score, 40)

            risk_score = min(risk_score, 100)

            # ================= SEVERITY =================

            if risk_score >= 85:
                severity = "Critical"
            elif risk_score >= 65:
                severity = "High"
            elif risk_score >= 40:
                severity = "Medium"
            else:
                severity = "Low"

            # ================= EXPLANATION =================

            if prediction == "Spam":

                reasons = []
                
                if urls:
                    reasons.append("Suspicious URL detected")
                    
                if phones:
                    reasons.append("Phone number detected")

                if emails:
                    reasons.append("Email address detected")

                if detected_keywords:
                    reasons.append(
                        "Keywords: " +
                        ", ".join(sorted(set(detected_keywords)))
                        )
                if reasons:
                    explanation = (
                        f"Spam detected. Risk Score: {risk_score}/100. "
                        + ". ".join(reasons)
                    )
                else:
                    explanation = "Spam detected by the AI model due to suspicious patterns."

            else:
                explanation = (
                    "This message appears safe. "
                    "No major spam indicators were detected."
                )

            # ================= SAVE =================

            conn = sqlite3.connect("history.db")
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO history
            (message, prediction, spam, ham, risk, timestamp)
            VALUES (?,?,?,?,?,?)
            """, (
                message,
                prediction,
                spam,
                ham,
                risk_score,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            conn.commit()
            conn.close()

    # ================= HISTORY =================

    conn = sqlite3.connect("history.db")
    cur = conn.cursor()

    cur.execute("""
    SELECT message, prediction, spam, ham, risk, timestamp
    FROM history
    ORDER BY id DESC
    LIMIT 10
    """)

    history = cur.fetchall()
    conn.close()

    # ================= ANALYTICS =================

    total_spam = sum(1 for row in history if row[1] == "Spam")
    total_ham = len(history) - total_spam

    if prediction == "Spam":
        chart_data = json.dumps([spam, ham])
        
    elif prediction == "Ham":
        chart_data = json.dumps([spam, ham])
        
    else:
        chart_data = json.dumps([0, 0])

    total_messages = len(history)
    threat_alerts = 0
    if urls:
        threat_alerts += 1
    if phones:
        threat_alerts += 1
    if emails:
        threat_alerts += 1
    if risk_score >= 65:
        threat_alerts += 1

    return render_template(
        "index.html",
        prediction=prediction,
        spam=spam,
        ham=ham,
        risk_score=risk_score,
        severity=severity,
        category=category,
        explanation=explanation,
        detected_keywords=detected_keywords,
        urls=urls,
        emails=emails,
        phones=phones,
        url_reputation=url_reputation,
        history=history,
        total_spam=total_spam,
        total_ham=total_ham,
        total_messages=total_messages,
        threat_alerts=threat_alerts,
        chart_data=chart_data
    )


# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)