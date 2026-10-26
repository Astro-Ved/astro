# Kundli Excel Tool

This tool integrates MS Excel 2021 with a Python backend to calculate Kundli (Vedic Astrology) details and populate an Excel sheet.

## Components

1. **Python Backend (`kundli_excel/kundli_backend.py`)**: A Flask web service that uses `pyswisseph`, `geopy`, and `timezonefinder` to calculate Panchang, Rashi, Lagna, etc.
2. **Excel VBA Module (`kundli_excel/Kundli.bas`)**: A VBA macro script that sends input data to the Python backend and writes the response into the Excel sheet.

## Setup

### Python Backend
1. Install dependencies:
   ```bash
   pip install flask pyswisseph geopy timezonefinder pytz
   ```
2. Run the server:
   ```bash
   python kundli_excel/kundli_backend.py
   ```
   This will start a local server on `http://127.0.0.1:5000`.

### Excel Module
1. Open your Excel workbook (e.g., your Kundli form).
2. Press `ALT + F11` to open the VBA Editor.
3. Go to `Tools > References` and ensure `Microsoft XML, v6.0` is checked.
4. Go to `File > Import File...` and select the `kundli_excel/Kundli.bas` file.
5. In your worksheet, place inputs in the following cells:
   - `B1`: Year (e.g., 2024)
   - `B2`: Month (e.g., 5)
   - `B3`: Day (e.g., 14)
   - `B4`: Hour (e.g., 12)
   - `B5`: Minute (e.g., 30)
   - `B6`: City (e.g., "Delhi")
6. Run the `CalculateKundli` macro (you can assign it to a button on the sheet). The calculated values will appear in cells `E1` to `E9`. (Modify the VBA script as needed to match the exact cell layout of your printed forms).
