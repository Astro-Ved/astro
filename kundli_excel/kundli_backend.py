import datetime
import math
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import swisseph as swe

swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
              "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
              "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
              "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

RASHIS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
          "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]

TITHIS = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
          "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
          "Trayodashi", "Chaturdashi", "Purnima", "Pratipada", "Dwitiya", "Tritiya",
          "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami",
          "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"]

KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]

YOGAS = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
         "Sukarma", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva", "Vyaghata",
         "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
         "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"]

VARS = ["Ravivara", "Somavara", "Mangalavara", "Budhavara", "Guruvara", "Shukravara", "Shanivara"]

# Simple Gana/Yoni/Nadi tables based on Nakshatra index (0-26)
# Approximated mapping
GANAS = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva", "Rakshasa",
         "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva", "Rakshasa",
         "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva"]

NADIS = ["Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi", "Aadi", "Madhya", "Antya",
         "Antya", "Madhya", "Aadi", "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi",
         "Aadi", "Madhya", "Antya", "Antya", "Madhya", "Aadi", "Aadi", "Madhya", "Antya"]

def get_lat_lon_tz(city_name):
    geolocator = Nominatim(user_agent="kundli_app")
    location = geolocator.geocode(city_name)
    if not location:
        raise ValueError(f"City '{city_name}' not found.")
    lat, lon = location.latitude, location.longitude
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    if not tz_name:
        tz_name = 'UTC'
    return lat, lon, tz_name

def decimal_to_dms(dec):
    d = int(dec)
    m = int(abs((dec - d) * 60))
    s = int((abs((dec - d) * 60) - m) * 60)
    return f"{d}° {m}' {s}\""

def calc_panchang(year, month, day, hour, minute, city_name):
    lat, lon, tz_name = get_lat_lon_tz(city_name)
    tz = pytz.timezone(tz_name)

    local_time = datetime.datetime(year, month, day, hour, minute)
    local_time = tz.localize(local_time)
    utc_time = local_time.astimezone(pytz.utc)

    jd = swe.julday(utc_time.year, utc_time.month, utc_time.day, utc_time.hour + utc_time.minute/60.0 + utc_time.second/3600.0)

    sun_pos = swe.calc_ut(jd, swe.SUN, swe.FLG_SIDEREAL)[0][0]
    moon_pos = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)[0][0]
    asc_pos = swe.houses(jd, lat, lon, b'P')[1][0]

    # Tithi
    tithi_val = (moon_pos - sun_pos) % 360 / 12.0
    tithi_index = int(math.floor(tithi_val))
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_name = TITHIS[tithi_index]

    # Nakshatra
    nak_val = moon_pos / (360.0 / 27.0)
    nak_index = int(math.floor(nak_val))
    nak_pada = int(math.floor((nak_val - nak_index) * 4)) + 1
    nak_name = NAKSHATRAS[nak_index]

    # Yoga
    yoga_val = (moon_pos + sun_pos) % 360 / (360.0 / 27.0)
    yoga_index = int(math.floor(yoga_val))
    yoga_name = YOGAS[yoga_index]

    # Karana
    karana_val = (moon_pos - sun_pos) % 360 / 6.0
    karana_index = int(math.floor(karana_val))
    if karana_index == 0:
        karana_name = "Kintughna"
    elif karana_index >= 57:
        specials = ["Shakuni", "Chatushpada", "Naga"]
        karana_name = specials[karana_index - 57]
    else:
        karana_name = KARANAS[(karana_index - 1) % 7]

    # Vara
    vara_index = (int(math.floor(jd + 1.5)) + 1) % 7
    vara_name = VARS[vara_index]

    # Rashi & Ascendant
    rashi_index = int(math.floor(moon_pos / 30.0))
    rashi_name = RASHIS[rashi_index]

    asc_index = int(math.floor(asc_pos / 30.0))
    asc_name = RASHIS[asc_index]

    gana = GANAS[nak_index]
    nadi = NADIS[nak_index]

    result = {
        "City": city_name,
        "Lat": lat,
        "Lon": lon,
        "Timezone": tz_name,
        "Sun_Pos": decimal_to_dms(sun_pos),
        "Moon_Pos": decimal_to_dms(moon_pos),
        "Ascendant_Pos": decimal_to_dms(asc_pos),
        "Tithi": tithi_name,
        "Paksha": paksha,
        "Nakshatra": nak_name,
        "Nakshatra_Pada": nak_pada,
        "Yoga": yoga_name,
        "Karana": karana_name,
        "Vara": vara_name,
        "Rashi": rashi_name,
        "Lagna": asc_name,
        "Gana": gana,
        "Nadi": nadi
    }
    return result


from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        year = int(data.get('year'))
        month = int(data.get('month'))
        day = int(data.get('day'))
        hour = int(data.get('hour'))
        minute = int(data.get('minute'))
        city = data.get('city')

        result = calc_panchang(year, month, day, hour, minute, city)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(port=5000, debug=True, host='0.0.0.0')
