import os
import random

def get_weather():
    # Simulate a connection to a Weather API
    # We purposefully make it fail 50% of the time to test our "Healing"
    connection_stability = random.choice([True, False]) 

    if connection_stability:
        return "☀️ Sunny, 25°C (Source: Primary API)"
    else:
        # This raises an error, simulating a crash
        raise Exception("Connection to Primary API Failed!")

def update_readme(weather_info):
    with open("README.md", "w") as f:
        f.write("# 🌦️ My Auto-Healing Weather Station\n\n")
        f.write(f"**Current Status:** {weather_info}\n")
        f.write("\n*Updated automatically by GitHub Actions*")

if __name__ == "__main__":
    try:
        # Try the primary method
        weather = get_weather()
        print("Success! Got weather data.")
        update_readme(weather)
        
    except Exception as e:
        # --- AUTO-HEALING LOGIC ---
        print(f"⚠️ Primary failed: {e}")
        print("🚑 Activating Auto-Healing Protocol...")
        
        # The 'Fix': Switch to cached/backup data instead of crashing
        backup_weather = "☁️ Data Unavailable (System Healed - Using Backup Mode)"
        update_readme(backup_weather)
        print("✅ System healed and saved state.")