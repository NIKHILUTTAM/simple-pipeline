import os
import random
from datetime import datetime

def get_weather():
    # Simulate a connection to a Weather API
    # 50% chance of failure (Simulating a crash)
    connection_stability = random.choice([True, False]) 

    if connection_stability:
        return "☀️ Sunny, 25°C (Source: Primary API)"
    else:
        # This raises an error, simulating a crash
        raise Exception("Connection to Primary API Failed!")

def update_website(status_text, css_class):
    # This is your HTML Template
    # We put {STATUS} and {TIME} placeholders where we want the data
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto-Healing Weather</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>🚀 Auto-Healing Pipeline</h1>
        <div class="card">
            <p><strong>Live Weather:</strong></p>
            <h2 class="{css_class}">{status_text}</h2>
            
            <p class="timestamp">Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p><strong>Host:</strong> Vercel + GitHub Actions</p>
        </div>
    </div>
</body>
</html>
    """
    
    # Write the new HTML to the file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    try:
        # Try the primary method
        weather = get_weather()
        print("Success! Got weather data.")
        # Update site with Green (success) style
        update_website(weather, "status success")
        
    except Exception as e:
        # --- AUTO-HEALING LOGIC ---
        print(f"⚠️ Primary failed: {e}")
        print("🚑 Activating Auto-Healing Protocol...")
        
        # The 'Fix': Switch to backup data
        backup_weather = "☁️ Data Unavailable (System Healed - Using Backup Mode)"
        
        # Update site with Orange (warning) style
        update_website(backup_weather, "status warning")
        print("✅ System healed and website updated.")