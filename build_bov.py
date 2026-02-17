#!/usr/bin/env python3
"""
Build script for 11315 Tiara St BOV - North Hollywood, CA 91601
3+1 JADU residential | 3-agent layout (Logan Ward lead, Glen Scher, Filip Niculete)
"""
import base64, json, os, sys, io, math, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(SCRIPT_DIR, "images")
OUTPUT = os.path.join(SCRIPT_DIR, "index.html")
BOV_BASE_URL = "https://11315tiara.laaa.com"
PDF_WORKER_URL = "https://laaa-pdf-worker.laaa-team.workers.dev"
PDF_FILENAME = "BOV - 11315 Tiara St, North Hollywood.pdf"
PDF_LINK = (PDF_WORKER_URL + "/?url=" + urllib.parse.quote(BOV_BASE_URL + "/", safe="")
            + "&filename=" + urllib.parse.quote(PDF_FILENAME, safe=""))

ENABLE_CHATBOT = False

# ============================================================
# IMAGE LOADING
# ============================================================
def load_image_b64(filename):
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.exists(path):
        print(f"WARNING: Image not found: {path}")
        return ""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    print(f"  Loaded: {filename} ({len(data)//1024}KB)")
    return f"data:{mime};base64,{data}"

print("Loading images...")
IMG = {
    "logo": load_image_b64("LAAA_Team_White.png"),
    "logo_blue": load_image_b64("LAAA_Team_Blue.png"),
    "glen": load_image_b64("Glen_Scher.png"),
    "filip": load_image_b64("Filip_Niculete.png"),
    "logan": load_image_b64("Logan_Ward.png"),
    "hero": load_image_b64("hero_aerial.jpeg"),
    "grid1": load_image_b64("grid1_exterior_driveway.jpeg"),
    "buyer_photo": load_image_b64("buyer_street_view.jpeg"),
    "closings_map": load_image_b64("closings-map.png"),
    "team_aida": load_image_b64("Aida_Memary_Scher.png"),
    "team_morgan": load_image_b64("Morgan_Wetmore.png"),
    "team_luka": load_image_b64("Luka_Leader.png"),
    "team_jason": load_image_b64("Jason_Mandel.png"),
    "team_alexandro": load_image_b64("Alexandro_Tapia.png"),
    "team_blake": load_image_b64("Blake_Lewitt.png"),
    "team_mike": load_image_b64("Mike_Palade.png"),
    "team_tony": load_image_b64("Tony_Dang.png"),
}

# ============================================================
# GEOCODING - US Census Bureau Geocoder
# ============================================================
def geocode_census(addr):
    url = (f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
           f"?address={urllib.parse.quote(addr)}&benchmark=Public_AR_Current&format=json")
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=15).read())
        m = data["result"]["addressMatches"]
        if not m:
            print(f"  WARNING: No match for: {addr}")
            return None
        lat, lng = m[0]["coordinates"]["y"], m[0]["coordinates"]["x"]
        print(f"  Geocoded: {addr} -> ({lat:.6f}, {lng:.6f})")
        return (lat, lng)
    except Exception as e:
        print(f"  WARNING: Geocode failed for {addr}: {e}")
        return None

print("\nGeocoding addresses...")
SUBJECT_ADDR = "11315 Tiara St, North Hollywood, CA 91601"
SUBJECT_COORDS = geocode_census(SUBJECT_ADDR)
if not SUBJECT_COORDS:
    SUBJECT_COORDS = (34.1697, -118.3801)
    print(f"  Using fallback coords for subject: {SUBJECT_COORDS}")
SUBJECT_LAT, SUBJECT_LNG = SUBJECT_COORDS

COMP_ADDRESSES = {
    "11415 Miranda St, North Hollywood, CA 91601": None,
    "14932 Kittridge St, Van Nuys, CA 91405": None,
    "6827 Ranchito Ave, Van Nuys, CA 91405": None,
    "13508 Victory Blvd, Van Nuys, CA 91401": None,
    "5539 Camellia Ave, North Hollywood, CA 91601": None,
    "6940 Ben Ave, North Hollywood, CA 91605": None,
    "5841 Tujunga Ave, North Hollywood, CA 91601": None,
    "6763 Case Ave, North Hollywood, CA 91606": None,
    "6441 Satsuma Ave, North Hollywood, CA 91606": None,
    "6118 Ethel Ave, Van Nuys, CA 91401": None,
}
RENT_COMP_ADDRESSES = {
    "6047 Tujunga Ave, North Hollywood, CA 91601": None,
    "5200 Cartwright Ave, North Hollywood, CA 91601": None,
    "10652 Landale St, North Hollywood, CA 91601": None,
    "5303 Hermitage Ave, North Hollywood, CA 91601": None,
    "11456 Oxnard St, North Hollywood, CA 91601": None,
    "4901 Laurel Canyon Blvd, North Hollywood, CA 91601": None,
}
for addr in COMP_ADDRESSES:
    COMP_ADDRESSES[addr] = geocode_census(addr)
for addr in RENT_COMP_ADDRESSES:
    RENT_COMP_ADDRESSES[addr] = geocode_census(addr)

# ============================================================
# STATIC MAP GENERATION (Pillow + OSM Tiles)
# ============================================================
def lat_lng_to_tile(lat, lng, zoom):
    n = 2 ** zoom
    x = int((lng + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2 * n)
    return x, y

def lat_lng_to_pixel(lat, lng, zoom, origin_x, origin_y):
    n = 2 ** zoom
    px = (lng + 180) / 360 * n * 256 - origin_x * 256
    lat_rad = math.radians(lat)
    py = (1 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2 * n * 256 - origin_y * 256
    return int(px), int(py)

def generate_static_map(center_lat, center_lng, markers, width=800, height=400, zoom=14):
    cx, cy = lat_lng_to_tile(center_lat, center_lng, zoom)
    tiles_x = math.ceil(width / 256) + 2
    tiles_y = math.ceil(height / 256) + 2
    start_x = cx - tiles_x // 2
    start_y = cy - tiles_y // 2
    big = Image.new("RGB", (tiles_x * 256, tiles_y * 256), (220, 220, 220))
    for tx in range(tiles_x):
        for ty in range(tiles_y):
            tile_url = f"https://tile.openstreetmap.org/{zoom}/{start_x + tx}/{start_y + ty}.png"
            req = urllib.request.Request(tile_url, headers={"User-Agent": "LAAA-BOV-Builder/1.0"})
            try:
                tile_data = urllib.request.urlopen(req, timeout=10).read()
                tile_img = Image.open(io.BytesIO(tile_data))
                big.paste(tile_img, (tx * 256, ty * 256))
            except Exception:
                pass
    n = 2 ** zoom
    offset_px = (center_lng + 180) / 360 * n * 256 - width / 2
    lat_rad = math.radians(center_lat)
    offset_py = (1 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2 * n * 256 - height / 2
    crop_left = int(offset_px - start_x * 256)
    crop_top = int(offset_py - start_y * 256)
    cropped = big.crop((crop_left, crop_top, crop_left + width, crop_top + height))
    draw = ImageDraw.Draw(cropped)
    for m in markers:
        lat, lng, label, color = m["lat"], m["lng"], m.get("label", ""), m.get("color", "#1B3A5C")
        px = int((lng + 180) / 360 * n * 256 - offset_px)
        py = int((1 - math.log(math.tan(math.radians(lat)) + 1/math.cos(math.radians(lat))) / math.pi) / 2 * n * 256 - offset_py)
        r = 14 if label == "★" else 11
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color, outline="white", width=2)
        if label:
            try:
                font = ImageFont.truetype("arial.ttf", 12 if label == "★" else 10)
            except Exception:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((px - tw // 2, py - th // 2 - 1), label, fill="white", font=font)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    print(f"  Static map generated: {width}x{height}, {len(markers)} markers, {len(b64)//1024}KB")
    return f"data:image/png;base64,{b64}"

def build_markers_from_comps(comps, addr_dict, comp_color, subject_lat, subject_lng):
    markers = [{"lat": subject_lat, "lng": subject_lng, "label": "★", "color": "#C5A258"}]
    for i, c in enumerate(comps):
        for a, coords in addr_dict.items():
            if coords and c["addr"].lower() in a.lower():
                markers.append({"lat": coords[0], "lng": coords[1], "label": str(i + 1), "color": comp_color})
                break
    return markers

# ============================================================
# FINANCIAL CONSTANTS
# ============================================================
LIST_PRICE = 2_195_000
UNITS = 4
SF = 4_350
LOT_SF = 7_000
TAX_RATE = 0.0117
GSR = 184_800
PF_GSR = 184_800
VACANCY_PCT = 0.03
OTHER_INCOME = 0
NON_TAX_NON_MGMT = 26_554
MGMT_PCT = 0.04

INTEREST_RATE = 0.0675
AMORTIZATION_YEARS = 30
LTV = 0.75

def calc_loan_constant(rate, amort):
    r = rate / 12
    n = amort * 12
    monthly = r * (1 + r)**n / ((1 + r)**n - 1)
    return monthly * 12

LOAN_CONSTANT = calc_loan_constant(INTEREST_RATE, AMORTIZATION_YEARS)

def calc_principal_reduction_yr1(loan_amount, annual_rate, amort_years):
    r = annual_rate / 12
    n = amort_years * 12
    monthly_pmt = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
    balance = loan_amount
    total_principal = 0
    for _ in range(12):
        interest = balance * r
        principal = monthly_pmt - interest
        total_principal += principal
        balance -= principal
    return total_principal

def calc_metrics(price):
    taxes = price * TAX_RATE
    egi = GSR * (1 - VACANCY_PCT) + OTHER_INCOME
    pf_egi = PF_GSR * (1 - VACANCY_PCT) + OTHER_INCOME
    mgmt = MGMT_PCT * egi
    total_exp = NON_TAX_NON_MGMT + mgmt + taxes
    noi = egi - total_exp
    pf_noi = pf_egi - total_exp
    loan_amount = price * LTV
    down_payment = price * (1 - LTV)
    debt_service = loan_amount * LOAN_CONSTANT
    net_cf = noi - debt_service
    coc = net_cf / down_payment * 100 if down_payment > 0 else 0
    dscr = noi / debt_service if debt_service > 0 else 0
    prin_red = calc_principal_reduction_yr1(loan_amount, INTEREST_RATE, AMORTIZATION_YEARS)
    return {
        "price": price, "taxes": taxes, "noi": noi, "pf_noi": pf_noi,
        "egi": egi, "pf_egi": pf_egi, "total_exp": total_exp,
        "per_unit": price / UNITS, "per_sf": price / SF,
        "cap": noi / price * 100 if price > 0 else 0,
        "pf_cap": pf_noi / price * 100 if price > 0 else 0,
        "grm": price / GSR if GSR > 0 else 0,
        "pf_grm": price / PF_GSR if PF_GSR > 0 else 0,
        "loan_amount": loan_amount, "down_payment": down_payment,
        "debt_service": debt_service, "net_cf": net_cf,
        "coc": coc, "dscr": dscr, "prin_red": prin_red,
    }

# Pricing matrix: 5 above + list + 5 below = 11 rows, $75K increments
# gap = $2,195K - $1,850K = $345K; min_inc = $86K, max_inc = $115K; $75K covers: bottom = $1,820K
INCREMENT = 75_000
MATRIX_PRICES = list(range(LIST_PRICE + 5 * INCREMENT, LIST_PRICE - 5 * INCREMENT - 1, -INCREMENT))
MATRIX = [calc_metrics(p) for p in MATRIX_PRICES]
AT_LIST = calc_metrics(LIST_PRICE)

print(f"\nFinancials at list ${LIST_PRICE:,}: Cap {AT_LIST['cap']:.2f}%, GRM {AT_LIST['grm']:.2f}x, NOI ${AT_LIST['noi']:,.0f}")

# ============================================================
# RENT ROLL DATA
# ============================================================
RENT_ROLL = [
    ("1", "3BR/2BA", 1350, 4400, "Occupied", "Renovated 1926 structure"),
    ("2", "3BR/2BA", 1300, 4200, "Vacant", "Built 2005; market rent"),
    ("3", "3BR/2BA", 1150, 4300, "Occupied", "Built 2005; 2nd floor"),
    ("4 (JADU)", "1BR/1BA", 550, 2500, "Occupied", "Furnished midterm rental"),
]

# ============================================================
# SALE COMPS DATA
# ============================================================
SALE_COMPS = [
    {"num": 1, "addr": "11415 Miranda St", "units": 4, "yr": 1963, "sf": 4164, "price": 1550000, "ppu": 387500, "psf": 372, "grm": 16.5, "date": "03/2025", "dom": 72, "notes": "Renovated; quartz, mini-splits, W/D"},
    {"num": 2, "addr": "14932 Kittridge St", "units": 4, "yr": 1961, "sf": 4209, "price": 1734000, "ppu": 433500, "psf": 412, "grm": "--", "date": "01/2026", "dom": "--", "notes": "Van Nuys; similar vintage and size"},
    {"num": 3, "addr": "6827 Ranchito Ave", "units": 4, "yr": 1973, "sf": 4800, "price": 1950000, "ppu": 487500, "psf": 406, "grm": "--", "date": "09/2025", "dom": 119, "notes": "Duplex + 2 new ADUs; proj. $15K/mo"},
    {"num": 4, "addr": "13508 Victory Blvd", "units": 4, "yr": 1951, "sf": 2779, "price": 2055000, "ppu": 513750, "psf": 740, "grm": "--", "date": "04/2025", "dom": "--", "notes": "Valley Glen; 4 units"},
    {"num": 5, "addr": "5539 Camellia Ave", "units": 3, "yr": 1948, "sf": 2127, "price": 2090000, "ppu": 696667, "psf": 983, "grm": "--", "date": "10/2024", "dom": "--", "notes": "NoHo 91601; 3 units"},
    {"num": 6, "addr": "6940 Ben Ave", "units": 3, "yr": 1939, "sf": 2052, "price": 2250000, "ppu": 750000, "psf": 1096, "grm": "--", "date": "09/2025", "dom": "--", "notes": "NoHo 91605; ceiling comp"},
]

ON_MARKET_COMPS = [
    {"num": 1, "addr": "5841 Tujunga Ave", "units": 4, "yr": 1941, "sf": "--", "price": 1250000, "ppu": 312500, "psf": "--", "dom": 166, "notes": "NOD filed; AS-IS; 166 DOM"},
    {"num": 2, "addr": "6763 Case Ave", "units": 4, "yr": 1942, "sf": 2290, "price": 1799000, "ppu": 449750, "psf": 786, "dom": 3, "notes": "Renovated 3BR + three 1BR ADUs; new listing"},
    {"num": 3, "addr": "6441 Satsuma Ave", "units": 4, "yr": 1950, "sf": 3282, "price": 1889000, "ppu": 472250, "psf": 576, "dom": 11, "notes": "New construction ADUs; renovated duplex"},
    {"num": 4, "addr": "6118 Ethel Ave", "units": 3, "yr": 1940, "sf": 3672, "price": 2500000, "ppu": 833333, "psf": 681, "dom": 16, "notes": "Main house + 2 ADUs; Van Nuys; ceiling"},
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def fc(n):
    if n is None or n == "--":
        return "--"
    return f"${n:,.0f}"

def fp(n):
    if n is None:
        return "--"
    return f"{n:.2f}%"

def build_map_js(map_id, comps, comp_color, addr_dict, subject_lat, subject_lng, subject_label="11315 Tiara St"):
    js = f"var {map_id} = L.map('{map_id}').setView([{subject_lat}, {subject_lng}], 14);\n"
    js += f"L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution: '&copy; OpenStreetMap'}}).addTo({map_id});\n"
    js += f"""L.marker([{subject_lat}, {subject_lng}], {{icon: L.divIcon({{className: 'custom-marker', html: '<div style="background:#C5A258;color:#fff;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);">&#9733;</div>', iconSize: [32, 32], iconAnchor: [16, 16]}})}})\n.addTo({map_id}).bindPopup('<b>{subject_label}</b><br>Subject Property<br>{UNITS} Units | {SF:,} SF');\n"""
    for i, c in enumerate(comps):
        lat, lng = None, None
        for a, coords in addr_dict.items():
            if coords and c["addr"].lower() in a.lower():
                lat, lng = coords
                break
        if lat is None:
            continue
        label = str(i + 1)
        price_str = fc(c.get("price", 0))
        popup = f"<b>#{label}: {c['addr']}</b><br>{c.get('units', '')} Units | {price_str}"
        js += f"""L.marker([{lat}, {lng}], {{icon: L.divIcon({{className: 'custom-marker', html: '<div style="background:{comp_color};color:#fff;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,0.3);">{label}</div>', iconSize: [26, 26], iconAnchor: [13, 13]}})}})\n.addTo({map_id}).bindPopup('{popup}');\n"""
    return js

sale_map_js = build_map_js("saleMap", SALE_COMPS, "#1B3A5C", COMP_ADDRESSES, SUBJECT_LAT, SUBJECT_LNG)
active_map_js = build_map_js("activeMap", ON_MARKET_COMPS, "#2E7D32", COMP_ADDRESSES, SUBJECT_LAT, SUBJECT_LNG)
rent_comps_for_map = [
    {"addr": "6047 Tujunga Ave", "units": "", "price": 0},
    {"addr": "5200 Cartwright Ave", "units": "", "price": 0},
    {"addr": "10652 Landale St", "units": "", "price": 0},
    {"addr": "5303 Hermitage Ave", "units": "", "price": 0},
    {"addr": "11456 Oxnard St", "units": "", "price": 0},
    {"addr": "4901 Laurel Canyon Blvd", "units": "", "price": 0},
]
rent_map_js = build_map_js("rentMap", rent_comps_for_map, "#1B3A5C", RENT_COMP_ADDRESSES, SUBJECT_LAT, SUBJECT_LNG)

# Generate static maps for PDF
print("\nGenerating static maps...")
IMG["loc_map"] = generate_static_map(SUBJECT_LAT, SUBJECT_LNG,
    [{"lat": SUBJECT_LAT, "lng": SUBJECT_LNG, "label": "★", "color": "#C5A258"}],
    width=800, height=220, zoom=15)

sale_markers = build_markers_from_comps(SALE_COMPS, COMP_ADDRESSES, "#1B3A5C", SUBJECT_LAT, SUBJECT_LNG)
IMG["sale_map_static"] = generate_static_map(SUBJECT_LAT, SUBJECT_LNG, sale_markers, width=800, height=300, zoom=14)

active_markers = build_markers_from_comps(ON_MARKET_COMPS, COMP_ADDRESSES, "#2E7D32", SUBJECT_LAT, SUBJECT_LNG)
IMG["active_map_static"] = generate_static_map(SUBJECT_LAT, SUBJECT_LNG, active_markers, width=800, height=300, zoom=14)

rent_markers = build_markers_from_comps(rent_comps_for_map, RENT_COMP_ADDRESSES, "#1B3A5C", SUBJECT_LAT, SUBJECT_LNG)
IMG["rent_map_static"] = generate_static_map(SUBJECT_LAT, SUBJECT_LNG, rent_markers, width=800, height=300, zoom=13)

# ============================================================
# GENERATE DYNAMIC TABLE HTML
# ============================================================

# Rent Roll
rent_roll_html = ""
total_rent = 0
total_sf = 0
for unit, utype, sf, rent, status, notes in RENT_ROLL:
    total_rent += rent
    total_sf += sf
    status_cell = f'<strong>{status}</strong>' if status == "Vacant" else status
    rent_roll_html += f'<tr><td>{unit}</td><td>{utype}</td><td class="num">{sf:,}</td><td class="num">${rent:,}</td><td class="num">${rent/sf:.2f}</td><td>{status_cell}</td><td>{notes}</td></tr>\n'
rent_roll_html += f'<tr style="background:#1B3A5C;color:#fff;font-weight:700;"><td>Total</td><td></td><td class="num">{total_sf:,}</td><td class="num">${total_rent:,}</td><td class="num">${total_rent/total_sf:.2f}</td><td></td><td>${total_rent*12:,}/yr</td></tr>\n'

# Pricing Matrix
matrix_html = ""
for m in MATRIX:
    cls = ' class="highlight"' if m["price"] == LIST_PRICE else ""
    matrix_html += f'<tr{cls}><td class="num">{fc(m["price"])}</td>'
    matrix_html += f'<td class="num">{m["cap"]:.2f}%</td>'
    matrix_html += f'<td class="num">{m["coc"]:.2f}%</td>'
    matrix_html += f'<td class="num">{fc(m["per_unit"])}</td>'
    matrix_html += f'<td class="num">${m["per_sf"]:.0f}</td>'
    matrix_html += f'<td class="num">{m["grm"]:.2f}x</td>'
    matrix_html += f'<td class="num">{m["dscr"]:.2f}x</td></tr>\n'

# Operating Statement
TAXES_AT_LIST = AT_LIST["taxes"]
CUR_EGI = AT_LIST["egi"]
CUR_MGMT = 0.04 * CUR_EGI

expense_lines = [
    ("Property Taxes", TAXES_AT_LIST, 1),
    ("Insurance", 4000, 2),
    ("Water / Sewer", 4800, 3),
    ("Trash", 1600, 4),
    ("Gas", 2400, 5),
    ("Electric", 3600, 6),
    ("Common Area Electric", 1500, 7),
    ("Repairs &amp; Maintenance", 4400, 8),
    ("Contract Services", 1500, 9),
    ("Administrative", 1000, 10),
    ("Marketing", 500, 11),
    ("Management Fee (4%)", CUR_MGMT, 12),
    ("Reserves", 800, 13),
    ("Other / SCEP", 454, 14),
]
total_exp_calc = sum(v for _, v, _ in expense_lines)

os_expense_html = ""
for label, val, note_num in expense_lines:
    ref = f' <span class="note-ref">[{note_num}]</span>' if note_num else ""
    os_expense_html += f'<tr><td>{label}{ref}</td><td class="num">${val:,.0f}</td><td class="num">${val/UNITS:,.0f}</td><td class="num">${val/SF:.2f}</td><td class="num">{val/CUR_EGI*100:.1f}%</td></tr>\n'

NOI_AT_LIST = CUR_EGI - total_exp_calc

# Sale comp table
sale_comp_html = ""
for c in SALE_COMPS:
    grm_str = f'{c["grm"]:.1f}x' if c["grm"] != "--" else "--"
    psf_str = f'${c["psf"]:,}' if c["psf"] != "--" else "--"
    dom_str = f'{c["dom"]:,}' if c["dom"] != "--" else "--"
    sf_str = f'{c["sf"]:,}' if c["sf"] != "--" else "--"
    sale_comp_html += f'<tr><td>{c["num"]}</td><td>{c["addr"]}</td><td class="num">{c["units"]}</td>'
    sale_comp_html += f'<td>{c["yr"]}</td><td class="num">{sf_str}</td>'
    sale_comp_html += f'<td class="num">{fc(c["price"])}</td><td class="num">{fc(c["ppu"])}</td>'
    sale_comp_html += f'<td class="num">{psf_str}</td><td class="num">{grm_str}</td>'
    sale_comp_html += f'<td>{c["date"]}</td><td class="num">{dom_str}</td><td>{c["notes"]}</td></tr>\n'

# Average and median summary rows
import statistics
sc_prices = [c["price"] for c in SALE_COMPS]
sc_ppus = [c["ppu"] for c in SALE_COMPS]
sc_psfs = [c["psf"] for c in SALE_COMPS if c["psf"] != "--"]
sc_grms = [c["grm"] for c in SALE_COMPS if c["grm"] != "--"]
sc_doms = [c["dom"] for c in SALE_COMPS if c["dom"] != "--"]

avg_price = statistics.mean(sc_prices)
avg_ppu = statistics.mean(sc_ppus)
avg_psf = statistics.mean(sc_psfs) if sc_psfs else 0
avg_grm_str = f'{statistics.mean(sc_grms):.1f}x' if sc_grms else "--"
avg_dom_str = f'{statistics.mean(sc_doms):.0f}' if sc_doms else "--"

med_price = statistics.median(sc_prices)
med_ppu = statistics.median(sc_ppus)
med_psf = statistics.median(sc_psfs) if sc_psfs else 0
med_grm_str = f'{statistics.median(sc_grms):.1f}x' if sc_grms else "--"
med_dom_str = f'{statistics.median(sc_doms):.0f}' if sc_doms else "--"

summary_row_style = 'style="background:#FFF8E7;font-weight:600;"'
sale_comp_html += f'<tr {summary_row_style}><td></td><td>Average</td><td class="num"></td><td></td><td class="num"></td>'
sale_comp_html += f'<td class="num">{fc(avg_price)}</td><td class="num">{fc(avg_ppu)}</td>'
sale_comp_html += f'<td class="num">${avg_psf:,.0f}</td><td class="num">{avg_grm_str}</td>'
sale_comp_html += f'<td></td><td class="num">{avg_dom_str}</td><td></td></tr>\n'

sale_comp_html += f'<tr {summary_row_style}><td></td><td>Median</td><td class="num"></td><td></td><td class="num"></td>'
sale_comp_html += f'<td class="num">{fc(med_price)}</td><td class="num">{fc(med_ppu)}</td>'
sale_comp_html += f'<td class="num">${med_psf:,.0f}</td><td class="num">{med_grm_str}</td>'
sale_comp_html += f'<td></td><td class="num">{med_dom_str}</td><td></td></tr>\n'

# On-market comp table
on_market_html = ""
for c in ON_MARKET_COMPS:
    psf_str = f'${c["psf"]}' if c["psf"] != "--" else "--"
    sf_str = f'{c["sf"]:,}' if c["sf"] != "--" else "--"
    on_market_html += f'<tr><td>{c["num"]}</td><td>{c["addr"]}</td><td class="num">{c["units"]}</td>'
    on_market_html += f'<td>{c["yr"]}</td><td class="num">{sf_str}</td>'
    on_market_html += f'<td class="num">{fc(c["price"])}</td><td class="num">{fc(c["ppu"])}</td>'
    on_market_html += f'<td class="num">{psf_str}</td><td class="num">{c["dom"]}</td>'
    on_market_html += f'<td>{c["notes"]}</td></tr>\n'

# Summary page data
sum_expense_html = ""
for label, val, _ in expense_lines:
    label_clean = label.replace("&amp;", "&")
    sum_expense_html += f'<tr><td>{label_clean}</td><td class="num">${val:,.0f}</td></tr>\n'

print(f"NOI at list (reassessed): ${NOI_AT_LIST:,.0f}")
print(f"Total expenses: ${total_exp_calc:,.0f}")

# ============================================================
# HTML ASSEMBLY
# ============================================================
html_parts = []

# HEAD
html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="Broker Opinion of Value - 11315 Tiara St, North Hollywood">
<meta property="og:description" content="4-Unit Multifamily Investment - North Hollywood, CA 91601 | LAAA Team - Marcus & Millichap">
<meta property="og:image" content="{BOV_BASE_URL}/preview.png">
<meta property="og:url" content="{BOV_BASE_URL}/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Broker Opinion of Value - 11315 Tiara St, North Hollywood">
<meta name="twitter:description" content="4-Unit Multifamily Investment - North Hollywood, CA 91601 | LAAA Team - Marcus & Millichap">
<meta name="twitter:image" content="{BOV_BASE_URL}/preview.png">
<title>BOV - 11315 Tiara St, North Hollywood | LAAA Team</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
""")

# CSS
html_parts.append("""
*{margin:0;padding:0;box-sizing:border-box;}body{font-family:'Inter',sans-serif;color:#333;line-height:1.6;background:#fff;}html{scroll-padding-top:50px;}p{margin-bottom:16px;font-size:14px;line-height:1.7;}
.cover{position:relative;min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;color:#fff;overflow:hidden;}.cover-bg{position:absolute;inset:0;background-size:cover;background-position:center;filter:brightness(0.45);z-index:0;}.cover-content{position:relative;z-index:2;padding:60px 40px;max-width:860px;}.cover-logo{width:320px;margin:0 auto 30px;display:block;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.3));}.cover-label{font-size:13px;font-weight:500;letter-spacing:3px;text-transform:uppercase;color:#C5A258;margin-bottom:18px;}.cover-title{font-size:46px;font-weight:700;letter-spacing:1px;margin-bottom:8px;text-shadow:0 2px 12px rgba(0,0,0,0.3);}.cover-address{font-size:16px;font-weight:400;color:rgba(255,255,255,0.85);margin-bottom:16px;}.cover-stats{display:flex;gap:32px;justify-content:center;flex-wrap:wrap;margin-bottom:32px;}.cover-stat-value{display:block;font-size:26px;font-weight:600;color:#fff;}.cover-stat-label{display:block;font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:1.5px;color:#C5A258;margin-top:4px;}.cover-headshots{display:flex;justify-content:center;gap:40px;margin-top:24px;margin-bottom:16px;}.cover-headshot-wrap{text-align:center;}.cover-headshot{width:80px;height:80px;border-radius:50%;border:3px solid #C5A258;object-fit:cover;box-shadow:0 4px 16px rgba(0,0,0,0.4);}.cover-headshot-name{font-size:12px;font-weight:600;margin-top:6px;color:#fff;}.cover-headshot-title{font-size:10px;color:#C5A258;}.gold-line{height:3px;background:#C5A258;margin:20px 0;}
.pdf-float-btn{position:fixed;bottom:24px;right:24px;z-index:9999;padding:14px 28px;background:#C5A258;color:#1B3A5C;font-size:14px;font-weight:700;text-decoration:none;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.35);display:flex;align-items:center;gap:8px;}.pdf-float-btn:hover{background:#fff;transform:translateY(-2px);}.pdf-float-btn svg{width:18px;height:18px;fill:currentColor;}
.toc-nav{background:#1B3A5C;padding:0 12px;display:flex;flex-wrap:nowrap;justify-content:center;align-items:stretch;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.15);overflow-x:auto;scrollbar-width:none;}.toc-nav::-webkit-scrollbar{display:none;}.toc-nav a{color:rgba(255,255,255,0.85);text-decoration:none;font-size:11px;font-weight:500;letter-spacing:0.3px;text-transform:uppercase;padding:12px 8px;border-bottom:2px solid transparent;white-space:nowrap;display:flex;align-items:center;}.toc-nav a:hover{color:#fff;background:rgba(197,162,88,0.12);border-bottom-color:rgba(197,162,88,0.4);}.toc-nav a.toc-active{color:#C5A258;font-weight:600;border-bottom-color:#C5A258;}
.section{padding:50px 40px;max-width:1100px;margin:0 auto;}.section-alt{background:#f8f9fa;}.section-title{font-size:26px;font-weight:700;color:#1B3A5C;margin-bottom:6px;}.section-subtitle{font-size:13px;color:#C5A258;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px;font-weight:500;}.section-divider{width:60px;height:3px;background:#C5A258;margin-bottom:30px;}.sub-heading{font-size:18px;font-weight:600;color:#1B3A5C;margin:30px 0 16px;}
.metrics-grid,.metrics-grid-4{display:grid;gap:16px;margin-bottom:30px;}.metrics-grid{grid-template-columns:repeat(3,1fr);}.metrics-grid-4{grid-template-columns:repeat(4,1fr);}.metric-card{background:#1B3A5C;border-radius:12px;padding:24px;text-align:center;color:#fff;}.metric-value{display:block;font-size:28px;font-weight:700;}.metric-label{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.6);margin-top:6px;}.metric-sub{display:block;font-size:12px;color:#C5A258;margin-top:4px;}
table{width:100%;border-collapse:collapse;margin-bottom:24px;font-size:13px;}th{background:#1B3A5C;color:#fff;padding:10px 12px;text-align:left;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;}td{padding:8px 12px;border-bottom:1px solid #eee;}tr:nth-child(even){background:#f5f5f5;}tr.highlight{background:#FFF8E7 !important;border-left:3px solid #C5A258;}td.num,th.num{text-align:right;}.table-scroll{overflow-x:auto;margin-bottom:24px;}.table-scroll table{min-width:700px;margin-bottom:0;}.info-table td{padding:8px 12px;border-bottom:1px solid #eee;font-size:13px;}.info-table td:first-child{font-weight:600;color:#1B3A5C;width:40%;}
.tr-tagline{font-size:24px;font-weight:600;color:#1B3A5C;text-align:center;padding:16px 24px;margin-bottom:20px;border-left:4px solid #C5A258;background:#FFF8E7;border-radius:0 4px 4px 0;font-style:italic;}.tr-map-print{display:none;}.tr-service-quote{margin:24px 0;}.tr-service-quote h3{font-size:18px;font-weight:700;color:#1B3A5C;margin-bottom:8px;line-height:1.3;}.tr-service-quote p{font-size:14px;line-height:1.7;}.bio-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0;}.bio-card{display:flex;gap:16px;align-items:flex-start;}.bio-headshot{width:100px;height:100px;border-radius:50%;border:3px solid #C5A258;object-fit:cover;flex-shrink:0;}.bio-name{font-size:16px;font-weight:700;color:#1B3A5C;}.bio-title{font-size:11px;color:#C5A258;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}.bio-text{font-size:13px;line-height:1.6;color:#444;}.team-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0;}.team-card{text-align:center;padding:8px;}.team-headshot{width:60px;height:60px;border-radius:50%;border:2px solid #C5A258;object-fit:cover;margin:0 auto 4px;display:block;}.team-card-name{font-size:13px;font-weight:700;color:#1B3A5C;}.team-card-title{font-size:10px;color:#C5A258;text-transform:uppercase;letter-spacing:0.5px;margin-top:2px;}.costar-badge{text-align:center;background:#FFF8E7;border:2px solid #C5A258;border-radius:8px;padding:20px 24px;margin:30px auto 24px;max-width:600px;}.costar-badge-title{font-size:22px;font-weight:700;color:#1B3A5C;}.costar-badge-sub{font-size:12px;color:#C5A258;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin-top:6px;}.condition-note{background:#FFF8E7;border-left:4px solid #C5A258;padding:16px 20px;margin:24px 0;border-radius:0 4px 4px 0;font-size:13px;line-height:1.6;}.condition-note-label{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#C5A258;margin-bottom:8px;}.achievements-list{font-size:13px;line-height:1.8;}.note-ref{font-size:9px;color:#C5A258;font-weight:700;vertical-align:super;}
.mkt-quote{background:#FFF8E7;border-left:4px solid #C5A258;padding:16px 24px;margin:20px 0;border-radius:0 4px 4px 0;font-size:15px;font-style:italic;line-height:1.6;color:#1B3A5C;}.mkt-channels{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}.mkt-channel{background:#f0f4f8;border-radius:8px;padding:16px 20px;}.mkt-channel h4{color:#1B3A5C;font-size:14px;margin-bottom:8px;}.mkt-channel li{font-size:13px;line-height:1.5;margin-bottom:4px;}.perf-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;}.perf-card{background:#f0f4f8;border-radius:8px;padding:16px 20px;}.perf-card h4{color:#1B3A5C;font-size:14px;margin-bottom:8px;}.perf-card li{font-size:13px;line-height:1.5;margin-bottom:4px;}.platform-strip{display:flex;justify-content:center;align-items:center;gap:20px;flex-wrap:wrap;margin-top:24px;padding:14px 20px;background:#1B3A5C;border-radius:6px;}.platform-strip-label{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#C5A258;font-weight:600;}.platform-name{font-size:12px;font-weight:600;color:#fff;}
.press-strip{display:flex;justify-content:center;align-items:center;gap:28px;flex-wrap:wrap;margin:16px 0 0;padding:12px 20px;background:#f0f4f8;border-radius:6px;}.press-strip-label{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:#888;font-weight:600;}.press-logo{font-size:13px;font-weight:700;color:#1B3A5C;letter-spacing:0.5px;}
.inv-split{display:grid;grid-template-columns:50% 50%;gap:24px;}.inv-left .metrics-grid-4{grid-template-columns:repeat(2,1fr);}.inv-text p{font-size:13px;line-height:1.6;margin-bottom:10px;}.inv-logo{display:none;}.inv-right{display:flex;flex-direction:column;gap:16px;padding-top:70px;}.inv-photo{height:280px;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);}.inv-photo img{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}.inv-highlights{background:#f0f4f8;border:1px solid #dce3eb;border-radius:8px;padding:16px 20px;flex:1;}.inv-highlights h4{color:#1B3A5C;font-size:13px;margin-bottom:8px;}.inv-highlights ul{margin:0;padding-left:18px;}.inv-highlights li{font-size:12px;line-height:1.5;margin-bottom:5px;}
.loc-grid{display:grid;grid-template-columns:58% 42%;gap:28px;align-items:start;}.loc-left{max-height:480px;overflow:hidden;}.loc-left p{font-size:13.5px;line-height:1.7;margin-bottom:14px;}.loc-right{display:block;max-height:480px;overflow:hidden;}.loc-wide-map{width:100%;height:200px;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-top:20px;}.loc-wide-map img{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}
.prop-grid-4{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto;gap:20px;}
.os-two-col{display:grid;grid-template-columns:55% 45%;gap:24px;align-items:stretch;margin-bottom:24px;}.os-right{font-size:10.5px;line-height:1.45;color:#555;background:#f8f9fb;border:1px solid #e0e4ea;border-radius:6px;padding:16px 20px;}.os-right h3{font-size:13px;margin:0 0 8px;}.os-right p{margin-bottom:4px;}
.summary-page{margin-top:24px;border:1px solid #dce3eb;border-radius:8px;padding:20px;background:#fff;}.summary-banner{text-align:center;background:#1B3A5C;color:#fff;padding:10px 16px;font-size:14px;font-weight:700;letter-spacing:2px;text-transform:uppercase;border-radius:4px;margin-bottom:16px;}.summary-two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start;}.summary-table{width:100%;border-collapse:collapse;margin-bottom:12px;font-size:12px;border:1px solid #dce3eb;}.summary-table th,.summary-table td{padding:4px 8px;border-bottom:1px solid #e8ecf0;}.summary-header{background:#1B3A5C;color:#fff;padding:5px 8px !important;font-size:10px !important;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;}.summary-table tr.summary td{border-top:2px solid #1B3A5C;font-weight:700;background:#f0f4f8;}.summary-table tr:nth-child(even){background:#fafbfc;}.summary-trade-range{text-align:center;margin:24px auto;padding:16px 24px;border:2px solid #1B3A5C;border-radius:6px;max-width:480px;}.summary-trade-label{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#555;font-weight:600;margin-bottom:6px;}.summary-trade-prices{font-size:26px;font-weight:700;color:#1B3A5C;}
.buyer-split{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start;}.buyer-objections .obj-item{margin-bottom:14px;}.buyer-objections .obj-q{font-weight:700;color:#1B3A5C;margin-bottom:4px;font-size:14px;}.buyer-objections .obj-a{font-size:13px;color:#444;line-height:1.6;}.buyer-photo{width:100%;height:220px;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-top:24px;}.buyer-photo img{width:100%;height:100%;object-fit:cover;object-position:center;display:block;}
.leaflet-map{height:400px;border-radius:4px;border:1px solid #ddd;margin-bottom:30px;z-index:1;}.map-fallback{display:none;}.comp-map-print{display:none;}.embed-map-wrap{position:relative;width:100%;margin-bottom:20px;border-radius:8px;overflow:hidden;}.embed-map-wrap iframe{display:block;width:100%;height:420px;border:0;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:30px;}.page-break-marker{height:4px;background:repeating-linear-gradient(90deg,#ddd 0,#ddd 8px,transparent 8px,transparent 16px);}.photo-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:30px;overflow:hidden;}.photo-grid img{width:100%;height:180px;object-fit:cover;border-radius:4px;}.highlight-box{background:#f0f4f8;border:1px solid #dce3eb;border-radius:8px;padding:20px 24px;margin:24px 0;}.img-float-right{float:right;width:48%;margin:0 0 16px 20px;border-radius:8px;overflow:hidden;}.img-float-right img{width:100%;display:block;}.narrative{font-size:13px;line-height:1.7;}
.footer{background:#1B3A5C;color:#fff;padding:50px 40px;text-align:center;}.footer-logo{width:180px;margin-bottom:30px;}.footer-team{display:flex;justify-content:center;gap:40px;margin-bottom:30px;flex-wrap:wrap;}.footer-person{text-align:center;flex:1;min-width:280px;}.footer-headshot{width:70px;height:70px;border-radius:50%;border:2px solid #C5A258;object-fit:cover;}.footer-name{font-size:16px;font-weight:600;}.footer-title{font-size:12px;color:#C5A258;margin-bottom:8px;}.footer-contact{font-size:12px;color:rgba(255,255,255,0.7);line-height:1.8;}.footer-contact a{color:rgba(255,255,255,0.7);text-decoration:none;}.footer-office{font-size:12px;color:rgba(255,255,255,0.5);margin-bottom:8px;}.footer-disclaimer{font-size:10px;color:rgba(255,255,255,0.35);margin-top:20px;max-width:800px;margin-left:auto;margin-right:auto;}

@media (max-width:768px){.cover-content{padding:30px 20px;}.cover-title{font-size:32px;}.cover-logo{width:220px;}.cover-headshots{gap:24px;}.cover-headshot{width:60px;height:60px;}.section{padding:30px 16px;}.photo-grid{grid-template-columns:1fr;}.two-col,.buyer-split,.inv-split,.os-two-col,.loc-grid{grid-template-columns:1fr;}.metrics-grid,.metrics-grid-4{grid-template-columns:repeat(2,1fr);gap:12px;}.metric-card{padding:14px 10px;}.metric-value{font-size:22px;}.mkt-channels,.perf-grid{grid-template-columns:1fr;}.summary-two-col,.prop-grid-4{grid-template-columns:1fr;}.pdf-float-btn{padding:10px 18px;font-size:12px;bottom:16px;right:16px;}.toc-nav{padding:0 6px;}.toc-nav a{font-size:10px;padding:10px 6px;letter-spacing:0.2px;}.leaflet-map{height:300px;}.embed-map-wrap iframe{height:320px;}.loc-wide-map{height:180px;margin-top:16px;}.table-scroll table{min-width:560px;}.bio-grid{grid-template-columns:1fr;gap:16px;}.bio-headshot{width:60px;height:60px;}.footer-team{flex-direction:column;align-items:center;}.press-strip{gap:16px;}.press-logo{font-size:11px;}.costar-badge-title{font-size:18px;}.img-float-right{float:none;width:100%;margin:0 0 16px 0;}.inv-photo{height:240px;}}
@media (max-width:420px){.cover-title{font-size:26px;}.cover-stat-value{font-size:20px;}.cover-headshots{gap:16px;}.cover-headshot{width:50px;height:50px;}.metrics-grid-4{grid-template-columns:1fr 1fr;}.metric-value{font-size:18px;}.section{padding:20px 12px;}}

@media print{
@page{size:letter landscape;margin:0.4in 0.5in;}body{font-size:11px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}p{font-size:11px;line-height:1.5;margin-bottom:8px;}
.pdf-float-btn,.toc-nav,.leaflet-map,.embed-map-wrap,.page-break-marker,.map-fallback{display:none !important;}
.cover{min-height:7.5in;page-break-after:always;}.cover-bg{-webkit-print-color-adjust:exact;print-color-adjust:exact;}.cover-headshots{display:flex !important;}.cover-headshot{width:55px;height:55px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.cover-logo{width:240px;}
.section{padding:20px 0;page-break-before:always;}.section-title{font-size:20px;margin-bottom:4px;}.section-subtitle{font-size:11px;margin-bottom:10px;}.section-divider{margin-bottom:16px;}
.metric-card{padding:12px 8px;border-radius:6px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.metric-value{font-size:20px;}.metric-label{font-size:9px;}
table{font-size:11px;}th{padding:6px 8px;font-size:9px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}td{padding:5px 8px;}tr.highlight{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.tr-tagline{font-size:15px;padding:8px 14px;margin-bottom:8px;}.tr-map-print{display:block;width:100%;height:240px;border-radius:4px;overflow:hidden;margin-bottom:8px;}.tr-map-print img{width:100%;height:100%;object-fit:cover;object-position:center;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.tr-service-quote{margin:10px 0;}.tr-service-quote h3{font-size:13px;margin-bottom:4px;}.tr-service-quote p{font-size:11px;line-height:1.45;}
.bio-headshot{width:75px;height:75px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.bio-text{font-size:11px;}.team-headshot{width:45px;height:45px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.team-card-name{font-size:11px;}.team-card-title{font-size:9px;}.costar-badge{padding:12px 16px;margin:16px auto;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.costar-badge-title{font-size:16px;}.condition-note{padding:10px 14px;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.achievements-list{font-size:11px;}
.inv-text p{font-size:11px;line-height:1.5;margin-bottom:6px;}.inv-logo{display:none !important;}.inv-right{padding-top:30px;}.inv-photo{height:220px;}.inv-photo img{-webkit-print-color-adjust:exact;print-color-adjust:exact;}.inv-highlights{padding:10px 14px;}.inv-highlights h4{font-size:11px;margin-bottom:4px;}.inv-highlights li{font-size:10px;line-height:1.4;margin-bottom:2px;}
.loc-grid{display:grid;grid-template-columns:58% 42%;gap:14px;page-break-inside:avoid;}.loc-left{max-height:340px;overflow:hidden;}.loc-left p{font-size:10.5px;line-height:1.4;margin-bottom:5px;}.loc-wide-map{height:220px;margin-top:8px;}.loc-wide-map img{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.os-two-col{page-break-before:always;align-items:stretch;}.os-right{font-size:9.5px;line-height:1.3;}
.summary-page{page-break-before:always;}.summary-table{font-size:10px;}.summary-header{font-size:9px !important;}
.buyer-photo{height:180px;}.buyer-photo img{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.comp-map-print{display:block !important;height:280px;border-radius:4px;overflow:hidden;margin-bottom:10px;}.comp-map-print img{width:100%;height:100%;object-fit:cover;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.footer{page-break-before:always;-webkit-print-color-adjust:exact;print-color-adjust:exact;}.footer-headshot{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
.price-reveal{page-break-before:always;}
#property-info{page-break-before:always;}
}
</style>
</head>
<body>
""")

# PDF DOWNLOAD BUTTON
html_parts.append(f"""
<a href="{PDF_LINK}" class="pdf-float-btn" target="_blank">
<svg viewBox="0 0 24 24"><path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20M12,19L8,15H10.5V12H13.5V15H16L12,19Z"/></svg>
Download PDF
</a>
""")

# PAGE 1: COVER
html_parts.append(f"""
<div class="cover">
<div class="cover-bg" style="background-image:url('{IMG["hero"]}');"></div>
<div class="cover-content">
<img src="{IMG["logo"]}" class="cover-logo" alt="LAAA Team">
<div class="cover-label">Confidential Broker Opinion of Value</div>
<div class="cover-title">11315 Tiara Street</div>
<div class="cover-address">North Hollywood, California 91601</div>
<div class="gold-line" style="width:80px;margin:0 auto 24px;"></div>
<div class="cover-stats">
<div class="cover-stat"><span class="cover-stat-value">3+1</span><span class="cover-stat-label">Units</span></div>
<div class="cover-stat"><span class="cover-stat-value">4,350</span><span class="cover-stat-label">Square Feet</span></div>
<div class="cover-stat"><span class="cover-stat-value">1926/2005</span><span class="cover-stat-label">Year Built</span></div>
<div class="cover-stat"><span class="cover-stat-value">7,000 SF</span><span class="cover-stat-label">Lot Size</span></div>
</div>
<div class="cover-headshots">
<div class="cover-headshot-wrap"><img class="cover-headshot" src="{IMG["logan"]}" alt="Logan Ward"><div class="cover-headshot-name">Logan Ward</div><div class="cover-headshot-title">Associate</div></div>
<div class="cover-headshot-wrap"><img class="cover-headshot" src="{IMG["glen"]}" alt="Glen Scher"><div class="cover-headshot-name">Glen Scher</div><div class="cover-headshot-title">SMDI</div></div>
<div class="cover-headshot-wrap"><img class="cover-headshot" src="{IMG["filip"]}" alt="Filip Niculete"><div class="cover-headshot-name">Filip Niculete</div><div class="cover-headshot-title">SMDI</div></div>
</div>
<p class="client-greeting" id="client-greeting">Prepared Exclusively for Valued Client</p>
<p style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:8px;">February 2026</p>
</div>
</div>
""")

# TOC NAV
html_parts.append("""
<nav class="toc-nav" id="toc-nav">
<a href="#track-record">Track Record</a>
<a href="#marketing">Marketing</a>
<a href="#investment">Investment</a>
<a href="#location">Location</a>
<a href="#prop-details">Property</a>
<a href="#transactions">History</a>
<a href="#property-info">Buyer Profile</a>
<a href="#sale-comps">Sale Comps</a>
<a href="#on-market">On-Market</a>
<a href="#rent-comps">Rent Comps</a>
<a href="#financials">Financials</a>
<a href="#contact">Contact</a>
</nav>
""")

# PAGE 2: TRACK RECORD P1
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="track-record">
<div class="section-title">Team Track Record</div>
<div class="section-subtitle">LA Apartment Advisors at Marcus & Millichap</div>
<div class="section-divider"></div>
<div class="tr-tagline"><span style="display:block;font-size:1.2em;font-weight:700;margin-bottom:4px;">LAAA Team of Marcus &amp; Millichap</span>Expertise, Execution, Excellence.</div>
<div class="metrics-grid-4">
<div class="metric-card"><span class="metric-value">501</span><span class="metric-label">Closed Transactions</span></div>
<div class="metric-card"><span class="metric-value">$1.6B</span><span class="metric-label">Total Sales Volume</span></div>
<div class="metric-card"><span class="metric-value">5,000+</span><span class="metric-label">Units Sold</span></div>
<div class="metric-card"><span class="metric-value">34</span><span class="metric-label">Median DOM</span></div>
</div>
<div class="embed-map-wrap"><iframe src="https://www.google.com/maps/d/embed?mid=1ewCjzE3QX9p6m2MqK-md8b6fZitfIzU&ehbc=2E312F&noprof=1" loading="lazy" allowfullscreen></iframe></div>
<div class="tr-map-print"><img src="{IMG["closings_map"]}" alt="LAAA Closings Map"></div>
<div class="tr-service-quote">
<h3>"We Didn't Invent Great Service... We Just Set the Standard."</h3>
<p>The LAAA Team at Marcus & Millichap is one of Southern California's most active multifamily investment sales teams, ranked #1 in Los Angeles County and #4 in all of California by CoStar for multifamily transaction volume (2019-2021). With over 500 closed transactions totaling $1.6 billion in sales, the team brings institutional-grade market knowledge to every engagement.</p>
<p>The LAAA Team maintains a proprietary database of over 40,000 apartment investors and 10,000 cooperating brokers, enabling targeted buyer outreach that consistently produces competitive offers and above-market pricing. The team's integration of Marcus & Millichap's national platform provides sellers access to the firm's 1031 exchange network, institutional buyer relationships, and real-time market intelligence across 80+ offices nationwide.</p>
</div>
</div>
""")

# PAGE 3: TRACK RECORD P2 - OUR TEAM
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section" style="padding-top:30px;">
<div style="text-align:center;margin-bottom:8px;"><div class="section-title" style="margin-bottom:4px;">Our Team</div><div class="section-divider" style="margin:0 auto 12px;"></div></div>
<div class="costar-badge" style="margin-top:4px;margin-bottom:8px;">
<div class="costar-badge-title">#1 Most Active Multifamily Sales Team in LA County</div>
<div class="costar-badge-sub">CoStar &bull; 2019, 2020, 2021 &bull; #4 in California</div>
</div>
<div class="bio-grid">
<div class="bio-card"><img class="bio-headshot" src="{IMG["glen"]}" alt="Glen Scher"><div><div class="bio-name">Glen Scher</div><div class="bio-title">Senior Managing Director Investments</div><div class="bio-text">Glen Scher is a Senior Managing Director Investments and co-founder of the LAAA Team at Marcus & Millichap. With over 450 transactions and $1.4 billion in closed sales, Glen is one of the most active multifamily brokers in Los Angeles County. A former Division I golfer at UC Santa Barbara, Glen brings the same discipline and competitive focus to his brokerage practice, consistently closing 40+ deals per year.</div></div></div>
<div class="bio-card"><img class="bio-headshot" src="{IMG["filip"]}" alt="Filip Niculete"><div><div class="bio-name">Filip Niculete</div><div class="bio-title">Senior Managing Director Investments</div><div class="bio-text">Filip Niculete is a Senior Managing Director Investments and co-founder of the LAAA Team at Marcus & Millichap. A 15-year veteran of the firm, Filip has closed over $1.4 billion in multifamily transactions and is recognized as one of Southern California's top commercial real estate professionals. Born in Romania and raised in the San Fernando Valley, Filip studied Finance at San Diego State University.</div></div></div>
</div>
<div class="team-grid">
<div class="team-card"><img class="team-headshot" src="{IMG["logan"]}" alt="Logan Ward"><div class="team-card-name">Logan Ward</div><div class="team-card-title">Associate</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_aida"]}" alt="Aida Memary Scher"><div class="team-card-name">Aida Memary Scher</div><div class="team-card-title">Senior Associate</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_morgan"]}" alt="Morgan Wetmore"><div class="team-card-name">Morgan Wetmore</div><div class="team-card-title">Associate</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_luka"]}" alt="Luka Leader"><div class="team-card-name">Luka Leader</div><div class="team-card-title">Associate</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_jason"]}" alt="Jason Mandel"><div class="team-card-name">Jason Mandel</div><div class="team-card-title">Associate</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_alexandro"]}" alt="Alexandro Tapia"><div class="team-card-name">Alexandro Tapia</div><div class="team-card-title">Associate Investments</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_blake"]}" alt="Blake Lewitt"><div class="team-card-name">Blake Lewitt</div><div class="team-card-title">Associate Investments</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_mike"]}" alt="Mike Palade"><div class="team-card-name">Mike Palade</div><div class="team-card-title">Agent Assistant</div></div>
<div class="team-card"><img class="team-headshot" src="{IMG["team_tony"]}" alt="Tony Dang"><div class="team-card-name">Tony Dang</div><div class="team-card-title">Operations Manager</div></div>
</div>
<div class="condition-note" style="margin-top:20px;"><div class="condition-note-label">Key Achievements</div><p class="achievements-list">
&bull; <strong>#1 Most Active Multifamily Team in LA County</strong> (2019-2021, CoStar)<br>
&bull; <strong>#4 in California</strong> for multifamily transaction volume (2019-2021, CoStar)<br>
&bull; <strong>40,000+ Investor Database</strong> with targeted outreach capabilities<br>
&bull; <strong>34 Median Days on Market</strong> - consistently outperforming market averages<br>
&bull; <strong>Chairman's Club Recognition</strong> - Marcus & Millichap's a top-tier annual honor<br>
&bull; <strong>Record-Setting Sales</strong> - Highest price achieved for a 4-unit in North Hollywood 91605
</p></div>
<div class="press-strip"><span class="press-strip-label">As Featured In</span><span class="press-logo">BISNOW</span><span class="press-logo">YAHOO FINANCE</span><span class="press-logo">CONNECT CRE</span><span class="press-logo">SFVBJ</span><span class="press-logo">THE PINNACLE LIST</span></div>
</div>
""")

# PAGE 4: MARKETING (STANDARD)
html_parts.append("""
<div class="page-break-marker"></div>
<div class="section" id="marketing">
<div class="section-title">Our Marketing Approach &amp; Results</div>
<div class="section-subtitle">Data-Driven Marketing + Proven Performance</div>
<div class="section-divider"></div>
<div class="metrics-grid-4">
<div class="metric-card"><span class="metric-value">30K+</span><span class="metric-label">Email Recipients</span></div>
<div class="metric-card"><span class="metric-value">10K+</span><span class="metric-label">Listing Views</span></div>
<div class="metric-card"><span class="metric-value">3.7</span><span class="metric-label">Avg Offers Received</span></div>
<div class="metric-card"><span class="metric-value">18</span><span class="metric-label">Days to Escrow</span></div>
</div>
<div class="mkt-quote">"We are PROACTIVE marketers, not reactive. Every listing receives a custom marketing campaign targeting qualified buyers in our database of 40,000+ apartment investors."</div>
<div class="mkt-channels">
<div class="mkt-channel"><h4>Direct Phone Outreach</h4><ul><li>40,000+ investor database</li><li>10,000+ cooperating brokers</li><li>Targeted by geography, size, price</li></ul></div>
<div class="mkt-channel"><h4>Email Campaigns</h4><ul><li>30,000+ targeted recipients</li><li>Custom property brochure</li><li>Follow-up sequences</li></ul></div>
<div class="mkt-channel"><h4>Online Platforms</h4><ul><li>MarcusMillichap.com (2M+ monthly)</li><li>CoStar / LoopNet / Crexi</li><li>Custom property website</li></ul></div>
<div class="mkt-channel"><h4>Additional Channels</h4><ul><li>1031 exchange network</li><li>Institutional relationships</li><li>Local broker community</li></ul></div>
</div>
<div class="metrics-grid-4" style="margin-top:16px;">
<div class="metric-card"><span class="metric-value">97.6%</span><span class="metric-label">Sale/List Price Ratio</span></div>
<div class="metric-card"><span class="metric-value">21%</span><span class="metric-label">Sold Above Ask</span></div>
<div class="metric-card"><span class="metric-value">10-Day</span><span class="metric-label">Avg Contingency</span></div>
<div class="metric-card"><span class="metric-value">61%</span><span class="metric-label">1031 Exchange</span></div>
</div>
<div class="perf-grid">
<div class="perf-card"><h4>Pricing Accuracy</h4><ul><li>97.6% sale-to-list price ratio</li><li>21% of listings sold above asking</li><li>Data-driven pricing methodology</li></ul></div>
<div class="perf-card"><h4>Marketing Speed</h4><ul><li>18 days average to escrow</li><li>34 median days on market</li><li>Immediate buyer outreach upon listing</li></ul></div>
<div class="perf-card"><h4>Contract Strength</h4><ul><li>10-day average contingency period</li><li>Pre-qualified buyer pool</li><li>98% close rate on executed contracts</li></ul></div>
<div class="perf-card"><h4>Exchange Expertise</h4><ul><li>61% of transactions involve 1031</li><li>National exchange network</li><li>Coordinated timing and identification</li></ul></div>
</div>
<div class="platform-strip"><span class="platform-strip-label">Advertised On</span><span class="platform-name">CREXI</span><span class="platform-name">COSTAR</span><span class="platform-name">LOOPNET</span><span class="platform-name">REALTOR.COM</span><span class="platform-name">ZILLOW</span><span class="platform-name">APARTMENTS.COM</span><span class="platform-name">REDFIN</span><span class="platform-name">M&amp;M</span><span class="platform-name">MLS</span></div>
</div>
""")

# PAGE 5: INVESTMENT OVERVIEW
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="investment">
<div class="section-title">Investment Overview</div>
<div class="section-subtitle">Renovated Triplex + JADU - Transit-Oriented North Hollywood</div>
<div class="section-divider"></div>
<div class="inv-split">
<div class="inv-left">
<div class="metrics-grid-4">
<div class="metric-card"><span class="metric-value">3+1</span><span class="metric-label">Units</span></div>
<div class="metric-card"><span class="metric-value">4,350</span><span class="metric-label">Building SF</span></div>
<div class="metric-card"><span class="metric-value">7,000 SF</span><span class="metric-label">Lot Size</span></div>
<div class="metric-card"><span class="metric-value">1926/2005</span><span class="metric-label">Year Built</span></div>
</div>
<div class="inv-text">
<p>The LAAA Team is pleased to present 11315 Tiara Street, a fully renovated triplex with a junior accessory dwelling unit in the heart of Mid-Town North Hollywood. The property consists of three spacious 3-bedroom/2-bathroom units and one 1-bedroom/1-bathroom JADU, totaling approximately 4,350 square feet of living space on a 7,000-square-foot lot. Originally constructed in 1926 with additions in 2005, the property underwent a comprehensive renovation in 2024-2025 that included new electrical (400-amp panel with 3 meters), new plumbing, 13 mini-split HVAC units, and complete interior remodeling - effectively delivering new-construction systems in an established residential setting.</p>
<p>The property generates $184,800 in annual gross scheduled rent at full occupancy, with three-bedroom units commanding $4,200-$4,400 per month and the furnished JADU at $2,500 per month. At the offered price of $2,195,000, the property delivers a GRM of 11.9x and a price per unit of $548,750 - below the average of comparable vintage sales in the submarket, meaning a buyer acquires more income per dollar invested than recent comparable transactions.</p>
<p>North Hollywood's Mid-Town corridor is positioned for material appreciation driven by District NoHo, a $1 billion-plus Metro joint development delivering 1,500 residential units and 500,000 square feet of office space at the North Hollywood Metro B Line station, less than one mile from the property.</p>
</div>
</div>
<div class="inv-right">
<div class="inv-photo"><img src="{IMG["grid1"]}" alt="11315 Tiara St"></div>
<div class="inv-highlights"><h4>Investment Highlights</h4><ul>
<li><strong>$184,800 Annual Gross Rent</strong> - buyer-normalized GSR at full occupancy with all four units at current/market rents</li>
<li><strong>All New Systems</strong> - 400A electrical panel, 13 mini-splits, new plumbing, 3 separate meters; 6 finaled permits (2024-2025)</li>
<li><strong>GRM of 11.9x at List</strong> - $548,750/unit is below the comparable vintage sales average; buyer acquires more income per dollar than recent comps</li>
<li><strong>Transit Priority Area</strong> - 0.7 miles to Metro B Line North Hollywood Station; Walk Score 79; District NoHo $1B+ development catalyst</li>
<li><strong>TOC Tier 1 + LARD2 Zoning</strong> - density bonus eligible for future redevelopment</li>
<li><strong>Turnkey Operation</strong> - C2 condition rating; no soft-story requirement; 4 parking spaces; no deferred maintenance</li>
</ul></div>
</div>
</div>
</div>
""")

# PAGE 6: LOCATION OVERVIEW
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="location">
<div class="section-title">Location Overview</div>
<div class="section-subtitle">Mid-Town North Hollywood - 91601</div>
<div class="section-divider"></div>
<div class="loc-grid">
<div class="loc-left">
<p>Ideally positioned in Mid-Town North Hollywood, 11315 Tiara Street offers residents direct access to one of the San Fernando Valley's most dynamic and rapidly evolving submarkets. The property benefits from a Walk Score of 79 (Very Walkable) and a Transit Score of 59 (Good Transit), with the Metro B Line (Red) North Hollywood Station located approximately 0.7 miles away, providing direct subway service to Hollywood, Downtown Los Angeles, and beyond. The neighborhood is anchored by NoHo West, a premier retail destination featuring Trader Joe's, LA Fitness, and Regal Cinemas, while the celebrated NoHo Arts District sits less than one mile to the east.</p>
<p>North Hollywood is poised for transformative growth. District NoHo, a $1 billion-plus Metro joint development at the North Hollywood Station, will deliver 1,500 new residential units, 500,000 square feet of creative office space, and 100,000 square feet of neighborhood-serving retail. This is the largest residential transit-oriented development project in Metro's history, and its construction signals a powerful trajectory for property values across the submarket.</p>
<p>Proximity to major freeways (170, 101, 134) and employment centers in Burbank, Studio City, and greater Los Angeles solidifies the location's appeal to a broad renter demographic. The property sits within a Transit Priority Area and a State Enterprise Zone, dual designations that provide density bonus eligibility and potential tax incentives for qualified buyers.</p>
</div>
<div class="loc-right">
<table class="info-table">
<thead><tr><th colspan="2">Location Details</th></tr></thead>
<tbody>
<tr><td>Walk Score</td><td>79 (Very Walkable)</td></tr>
<tr><td>Transit Score</td><td>59 (Good Transit)</td></tr>
<tr><td>Bike Score</td><td>58 (Bikeable)</td></tr>
<tr><td>Nearest Metro</td><td>B Line - North Hollywood, ~0.7 mi</td></tr>
<tr><td>Nearest Freeways</td><td>170 (0.5 mi), 101 (1.5 mi)</td></tr>
<tr><td>Major Retail</td><td>NoHo West (Trader Joe's), 0.8 mi</td></tr>
<tr><td>Arts & Entertainment</td><td>NoHo Arts District, &lt;1 mi</td></tr>
<tr><td>Major Employers</td><td>Burbank Media (3 mi), Universal (4 mi)</td></tr>
<tr><td>Development</td><td>District NoHo - $1B+, 1,500 units</td></tr>
<tr><td>Community Plan</td><td>North Hollywood - Valley Village</td></tr>
</tbody>
</table>
</div>
</div>
<div class="loc-wide-map"><img src="{IMG["loc_map"]}" alt="Location Map"></div>
</div>
""")

# PAGE 7: PROPERTY DETAILS
html_parts.append("""
<div class="page-break-marker"></div>
<div class="section" id="prop-details">
<div class="section-title">Property Details</div>
<div class="section-subtitle">11315 Tiara St, North Hollywood, CA 91601</div>
<div class="section-divider"></div>
<div class="prop-grid-4">
<div><table class="info-table"><thead><tr><th colspan="2">Property Overview</th></tr></thead><tbody>
<tr><td>Address</td><td>11315 Tiara St, North Hollywood 91601</td></tr>
<tr><td>APN</td><td>2337-010-017</td></tr>
<tr><td>Year Built</td><td>1926 (Unit 1); 2005 (Units 2-4)</td></tr>
<tr><td>Building SF</td><td>4,350 (seller) / 4,243 (appraiser)</td></tr>
<tr><td>Lot Size</td><td>7,000 SF (50 x 140)</td></tr>
<tr><td>Stories</td><td>2</td></tr>
<tr><td>Construction</td><td>Wood frame, stucco, asphalt shingle</td></tr>
<tr><td>Condition</td><td>C2 (Good) - full renovation 2024-2025</td></tr>
</tbody></table></div>
<div><table class="info-table"><thead><tr><th colspan="2">Site &amp; Zoning</th></tr></thead><tbody>
<tr><td>Zoning</td><td>LARD2 (Low-Medium II Residential)</td></tr>
<tr><td>TOC Tier</td><td>Tier 1</td></tr>
<tr><td>Transit Priority Area</td><td>Yes</td></tr>
<tr><td>Community Plan</td><td>North Hollywood - Valley Village</td></tr>
<tr><td>Parking</td><td>4 spaces (concrete driveway)</td></tr>
<tr><td>FEMA Flood Zone</td><td>Zone C (minimal hazard)</td></tr>
</tbody></table></div>
<div><table class="info-table"><thead><tr><th colspan="2">Building Systems</th></tr></thead><tbody>
<tr><td>Electrical</td><td>400A panel, 3 meters (new 2025)</td></tr>
<tr><td>HVAC</td><td>13 ductless mini-splits (new 2024) + FAU/CAC</td></tr>
<tr><td>Plumbing</td><td>Full TI (finaled 2024)</td></tr>
<tr><td>Lighting</td><td>80 receptacles, 68 lights, 22 circuits</td></tr>
<tr><td>Ventilation</td><td>7 bath fans, 3 kitchen hoods, 4 dryer vents</td></tr>
<tr><td>Water Heaters</td><td>Individual units</td></tr>
<tr><td>Metering</td><td>3 electric, 3 gas (Units 3 &amp; 4 share elec)</td></tr>
</tbody></table></div>
<div><table class="info-table"><thead><tr><th colspan="2">Regulatory &amp; Compliance</th></tr></thead><tbody>
<tr><td>Rent Control (RSO)</td><td>Yes - 4% max annual increase</td></tr>
<tr><td>Soft-Story Retrofit</td><td>Not required</td></tr>
<tr><td>Permits</td><td>6 finaled (2024-2025)</td></tr>
<tr><td>Certificate of Occupancy</td><td>1 on file</td></tr>
</tbody></table></div>
</div>
</div>
""")

# TRANSACTION HISTORY
html_parts.append("""
<div class="page-break-marker"></div>
<div class="section section-alt" id="transactions">
<div class="section-title">Transaction History</div>
<div class="section-subtitle">Ownership &amp; Sale Record</div>
<div class="section-divider"></div>
<div class="table-scroll"><table>
<thead><tr><th>Date</th><th>Event</th><th>Price</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>04/2022</td><td>MLS Listing (Expired)</td><td>$1,200,000 list</td><td>Orig $1,299,000; 81 DOM; pre-renovation; Section 8 at $936-$958/mo</td></tr>
<tr><td>07/2022</td><td>MLS Listing (Canceled)</td><td>$1,050,000 list</td><td>Orig $1,150,000; 158 DOM; same condition</td></tr>
<tr><td>10/2023</td><td>Sale</td><td>$1,000,000</td><td>Acquired as unrenovated triplex by current owner</td></tr>
<tr><td>2024-2025</td><td>Renovation</td><td>Est. $300K-$500K</td><td>Full gut renovation: electrical, plumbing, HVAC, finishes; 6 permits</td></tr>
<tr><td>08/2025</td><td>Appraisal</td><td>$2,350,000</td><td>Chase appraisal; sales comparison approach</td></tr>
<tr><td>10/2025</td><td>Refinance</td><td>$1,400,000 loan</td><td>Rocket Mortgage; 30-yr conventional; ~60% LTV</td></tr>
</tbody>
</table></div>
<p style="font-size:13px;line-height:1.7;">The property's transaction history illustrates a clear value-creation story. The previous owners listed the property twice in 2022 without attracting a buyer. At that time, the building housed Section 8 tenants paying $936-$958 per month in a physically dated condition. The property sold to the current owner in October 2023 for $1,000,000. Following acquisition, the owner undertook a comprehensive renovation that effectively rebuilt the property from the studs out. The renovation transformed monthly rental income from approximately $2,900 (pre-renovation) to $15,400 at full occupancy - a 5.3x increase. In August 2025, Chase appraised the property at $2,350,000.</p>
</div>
""")

# PAGE 8: BUYER PROFILE & OBJECTIONS
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="property-info">
<div class="section-title">Buyer Profile &amp; Anticipated Objections</div>
<div class="section-subtitle">Target Investors &amp; Data-Backed Responses</div>
<div class="section-divider"></div>
<div class="buyer-split">
<div class="buyer-split-left">
<div class="buyer-profile">
<div style="font-size:14px;font-weight:700;color:#1B3A5C;margin-bottom:12px;">Target Buyer Profile</div>
<ul style="font-size:13px;line-height:1.6;padding-left:18px;">
<li><strong>Owner-users</strong> - occupy one unit and rent the remaining three, benefiting from favorable residential financing (80-85% LTV)</li>
<li><strong>Small-portfolio investors</strong> - building a Fannie/Freddie-eligible residential rental portfolio with 30-year fixed-rate financing</li>
<li><strong>Mid-term rental operators</strong> - leveraging the furnished JADU and utilities-included strategy for premium rents</li>
<li><strong>1031 exchange buyers</strong> - deploying capital into a stabilized, recently renovated asset with minimal near-term CapEx</li>
</ul>
<p style="font-style:italic;font-size:12px;color:#666;margin-top:12px;">Broad appeal across buyer segments supports competitive pricing and multiple offer scenarios.</p>
</div>
</div>
<div class="buyer-objections">
<h3 class="sub-heading" style="margin-top:0;">Anticipated Buyer Objections</h3>
<div class="obj-item"><p class="obj-q">"How does $2.195M compare to closed sales for vintage 3-4 unit properties?"</p><p class="obj-a">Six comparable vintage sales (1939-1973 construction) closed between $1.55M and $2.25M. Three sales exceeded $2M: Victory Blvd at $2.055M, 5539 Camellia at $2.09M, and Ben Ave at $2.25M. The subject at $548,750/unit is below the average $/unit of these comps, and its $15,400/mo income exceeds all but one comparable property.</p></div>
<div class="obj-item"><p class="obj-q">"The JADU is unpermitted. Why should I pay for a 4th unit?"</p><p class="obj-a">The JADU's $2,500 monthly rent is 16% of total gross income. Under AB 2533 (effective January 2025), California provides clear legalization pathways. Even excluding Unit 4 entirely, the three remaining units generate $12,900/mo ($154,800 annually), supporting a price above $1.9M.</p></div>
<div class="obj-item"><p class="obj-q">"All utilities are landlord-paid. What does that cost?"</p><p class="obj-a">Estimated annual utility burden is approximately $13,900. This is fully reflected in the underwriting. The utilities-included strategy supports premium rents: subject 3-bedrooms at $4,200-$4,400 vs. comparable units without utilities at $3,400-$3,900, an effective premium of $150-$200/month per unit.</p></div>
<div class="obj-item"><p class="obj-q">"Property taxes will be reassessed at purchase. How does that affect returns?"</p><p class="obj-a">At $2.195M, annual taxes increase from $12,714 to approximately $25,682 (+$12,968/yr). Even with reassessed taxes, the property generates NOI of approximately $119,850, representing a 5.46% cap rate - competitive for a fully renovated, transit-adjacent residential asset in Los Angeles.</p></div>
</div>
</div>
<div class="buyer-photo"><img src="{IMG["buyer_photo"]}" alt="11315 Tiara St"></div>
</div>
""")

# PAGE 9: SALE COMPS
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section" id="sale-comps">
<div class="section-title">Comparable Sales Analysis</div>
<div class="section-subtitle">Closed Sales - North Hollywood</div>
<div class="section-divider"></div>
<div class="leaflet-map" id="saleMap"></div>
<p class="map-fallback">Interactive map available at the live URL.</p>
<div class="comp-map-print"><img src="{IMG["sale_map_static"]}" alt="Sale Comps Map"></div>
<div class="table-scroll"><table>
<thead><tr><th>#</th><th>Address</th><th class="num">Units</th><th>Year</th><th class="num">SF</th><th class="num">Price</th><th class="num">$/Unit</th><th class="num">$/SF</th><th class="num">GRM</th><th>Sold</th><th class="num">DOM</th><th>Notes</th></tr></thead>
<tbody>{sale_comp_html}</tbody>
</table></div>
<h3 class="sub-heading">Individual Comp Analysis</h3>
<p style="font-size:13px;color:#666;margin-bottom:16px;"><em>Subject metrics at $2,195,000: $548,750/unit | $504/SF | 11.9x GRM</em></p>
<div class="narrative">
<p><strong>1. 11415 Miranda St ($1,550,000) - $387,500/unit | $372/SF | 16.5x GRM</strong><br>The most directly comparable MLS closed sale. Miranda is a renovated 4-unit property with modern finishes including quartz countertops, ductless split HVAC, and tankless water heaters. At 4,164 SF, it is similar in size to the subject. However, Miranda's actual monthly rent of $7,845 is roughly half the subject's $15,400. The subject's substantially higher income supports a meaningful premium. At $387,500/unit, Miranda establishes the floor for renovated properties in the submarket.</p>
<p><strong>2. 14932 Kittridge St ($1,734,000) - $433,500/unit | $412/SF</strong><br>A 4-unit property built in 1961 with 4,209 SF - nearly identical in vintage and building size to the subject. Sold in January 2026, making it the most recent sale in the comp set. Located in Van Nuys (91405), a slightly less desirable submarket than Mid-Town North Hollywood (91601). The subject's superior location, higher rental income ($15,400/mo), and fully renovated condition support a premium over Kittridge's $433,500/unit.</p>
<p><strong>3. 6827 Ranchito Ave ($1,950,000) - $487,500/unit | $406/SF</strong><br>The most structurally similar comp: an older duplex (built 1973) with two newly constructed ADUs, mirroring the subject's older-structure-plus-additions configuration. At 4,800 SF on a 10,343 SF lot, the property is larger than the subject. Projected rents of approximately $15,000/month closely match the subject's $15,400. Sold at $487,500/unit after 119 days on market (originally listed at $2,399,000). The subject's Mid-Town North Hollywood location and transit proximity support pricing above this comp.</p>
<p><strong>4. 13508 Victory Blvd ($2,055,000) - $513,750/unit | $740/SF</strong><br>A 4-unit property built in 1951, sold in April 2025 in Valley Glen. At 2,779 SF, the building is significantly smaller than the subject (4,350 SF), which accounts for the higher $/SF. On a per-unit basis at $513,750, this comp supports pricing in the $2M+ range for vintage 4-unit properties in the greater North Hollywood area.</p>
<p><strong>5. 5539 Camellia Ave ($2,090,000) - $696,667/unit | $983/SF</strong><br>A 3-unit property built in 1948, located in North Hollywood 91601 - the same zip code as the subject. At only 2,127 SF, the extremely high $/SF reflects the premium that smaller buildings command on a per-foot basis. The subject at $504/SF and $548,750/unit represents a meaningful discount on both metrics despite offering one additional unit and more than double the building square footage.</p>
<p><strong>6. 6940 Ben Ave ($2,250,000) - $750,000/unit | $1,096/SF</strong><br>A 3-unit property built in 1939 in North Hollywood 91605. At 2,052 SF, the small building size drives the high $/SF. This is the highest-priced comp in the set, establishing a ceiling for the submarket. The subject at $2,195,000 is priced 2.4% below this comp while offering one additional unit and substantially more building area, positioning it as the better value per unit and per square foot.</p>
</div>
</div>
""")

# PAGE 10: ON-MARKET COMPS
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="on-market">
<div class="section-title">On-Market Comparables</div>
<div class="section-subtitle">Currently Listed for Sale</div>
<div class="section-divider"></div>
<div class="leaflet-map" id="activeMap"></div>
<p class="map-fallback">Interactive map available at the live URL.</p>
<div class="comp-map-print"><img src="{IMG["active_map_static"]}" alt="On-Market Comps Map"></div>
<div class="table-scroll"><table>
<thead><tr><th>#</th><th>Address</th><th class="num">Units</th><th>Year</th><th class="num">SF</th><th class="num">List Price</th><th class="num">$/Unit</th><th class="num">$/SF</th><th class="num">DOM</th><th>Notes</th></tr></thead>
<tbody>{on_market_html}</tbody>
</table></div>
<div class="narrative">
<p>The active inventory for renovated 3-4 unit properties in North Hollywood and the surrounding area includes four listings spanning $1.25M to $2.5M. 5841 Tujunga Avenue ($1,250,000) carries a Notice of Default and 166 days on market - a distressed listing that does not represent competitive supply. 6763 Case Avenue ($1,799,000) is a freshly listed renovated 4-plex with a 3BR main unit and three 1BR ADUs - a comparable concept to the subject at a lower price point driven by smaller unit sizes and lower income. 6441 Satsuma Avenue ($1,889,000) is a renovated duplex with two new ADUs in North Hollywood 91606, listed at a 5.85% proforma cap rate.</p>
<p>6118 Ethel Avenue ($2,500,000) in Van Nuys represents the ceiling: a remodeled main house with two ADUs on a large lot generating $13,600/month in rent. The subject at $2,195,000 is positioned 16% below Ethel while generating higher monthly income ($15,400 vs. $13,600). Among the three competitive active listings (Case, Satsuma, Ethel), the subject offers the strongest income-to-price ratio, supporting its positioning in the market.</p>
</div>
</div>
""")

# PAGE 11: RENT COMPS
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section" id="rent-comps">
<div class="section-title">Rent Comparable Analysis</div>
<div class="section-subtitle">3-Bedroom / 2-Bathroom &amp; JADU Comparables</div>
<div class="section-divider"></div>
<div class="leaflet-map" id="rentMap"></div>
<p class="map-fallback">Interactive map available at the live URL.</p>
<div class="comp-map-print"><img src="{IMG["rent_map_static"]}" alt="Rent Comps Map"></div>
<h3 class="sub-heading">3-Bedroom / 2-Bathroom Comps (Subject Units 1-3)</h3>
<div class="table-scroll"><table>
<thead><tr><th>#</th><th>Address</th><th class="num">Rent</th><th class="num">SF</th><th class="num">$/SF</th><th>Source</th><th>Features</th></tr></thead>
<tbody>
<tr><td>1</td><td>6047 Tujunga Ave</td><td class="num">$4,100</td><td class="num">1,400</td><td class="num">$2.93</td><td>Zillow</td><td>Renovated, W/D, 2-car garage</td></tr>
<tr><td>2</td><td>5200 Cartwright Ave</td><td class="num">$4,600</td><td class="num">1,600</td><td class="num">$2.88</td><td>Zillow</td><td>Renovated 1923, central AC</td></tr>
<tr><td>3</td><td>10652 Landale St</td><td class="num">$4,200</td><td class="num">1,500</td><td class="num">$2.80</td><td>Zillow</td><td>Updated, W/D, garage</td></tr>
<tr><td>4</td><td>5303 Hermitage Ave</td><td class="num">$3,695</td><td class="num">--</td><td class="num">--</td><td>Apartments.com</td><td>Renovated, granite, W/D</td></tr>
<tr><td>5</td><td>11456 Oxnard St</td><td class="num">$3,395</td><td class="num">1,450</td><td class="num">$2.34</td><td>Apartments.com</td><td>Basic, no AC, no parking</td></tr>
<tr><td>6</td><td>4901 Laurel Canyon Blvd</td><td class="num">$3,200</td><td class="num">1,000</td><td class="num">$3.20</td><td>Apartments.com</td><td>Smaller unit, older building</td></tr>
<tr style="background:#FFF8E7;font-weight:600;"><td></td><td>Average</td><td class="num">$3,865</td><td class="num"></td><td class="num"></td><td></td><td></td></tr>
</tbody>
</table></div>
<h3 class="sub-heading">1-Bedroom / 1-Bathroom Comps (JADU)</h3>
<div class="table-scroll"><table>
<thead><tr><th>#</th><th>Address</th><th class="num">Rent</th><th class="num">SF</th><th class="num">$/SF</th><th>Source</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>J1</td><td>10744 Blix St</td><td class="num">$2,095</td><td class="num">600</td><td class="num">$3.49</td><td>Zillow</td><td>Basic, older building</td></tr>
<tr><td>J2</td><td>5309 Hermitage Ave</td><td class="num">$2,250</td><td class="num">750</td><td class="num">$3.00</td><td>Apartments.com</td><td>Updated, gated parking</td></tr>
<tr><td>J3</td><td>5303 Hermitage Ave</td><td class="num">$2,395</td><td class="num">--</td><td class="num">--</td><td>Apartments.com</td><td>Renovated, granite</td></tr>
<tr><td>J4</td><td>11100 Hartsook St</td><td class="num">$2,455</td><td class="num">--</td><td class="num">--</td><td>Apartments.com</td><td>Renovated, A/C, parking</td></tr>
<tr style="background:#FFF8E7;font-weight:600;"><td></td><td>Unfurnished Avg</td><td class="num">$2,299</td><td class="num"></td><td class="num"></td><td></td><td>Furnished range: $2,500-$3,000</td></tr>
</tbody>
</table></div>
<div class="narrative">
<p>The subject's current rents of $4,200-$4,400 for the 3-bedroom units are supported by comparable asking rents ranging from $3,200 to $4,600 with an average of $3,865. The subject's rents sit above average, justified by the fully renovated condition, all-new building systems, and the utilities-included strategy that adds an estimated $150-$200 per month in perceived value per unit. The JADU at $2,500/month operates as a furnished mid-term rental, capturing a meaningful premium over the unfurnished 1-bedroom average of $2,299.</p>
<p><strong>Important caveats:</strong> All rent comps reflect asking rents, not verified achieved rents. Actual rents may be 2-5% below asking. RSO limits annual increases to 4% for in-place tenants, but vacancy decontrol allows market reset at turnover.</p>
</div>
</div>
""")

# PAGE 12: FINANCIAL ANALYSIS - RENT ROLL
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="section section-alt" id="financials">
<div class="section-title">Financial Analysis</div>
<div class="section-subtitle">Investment Underwriting</div>
<div class="section-divider"></div>
<h3 class="sub-heading">Unit Mix &amp; Rent Roll</h3>
<div class="table-scroll"><table>
<thead><tr><th>Unit</th><th>Type</th><th class="num">SF</th><th class="num">Rent/Mo</th><th class="num">Rent/SF</th><th>Status</th><th>Notes</th></tr></thead>
<tbody>{rent_roll_html}</tbody>
</table></div>
""")

# PAGE 13: OPERATING STATEMENT + NOTES
html_parts.append(f"""
<div class="os-two-col">
<div class="os-left">
<h3 class="sub-heading" style="margin-top:0;">Operating Statement</h3>
<table>
<thead><tr><th>Income</th><th class="num">Annual</th><th class="num">Per Unit</th><th class="num">$/SF</th><th class="num">% EGI</th></tr></thead>
<tbody>
<tr><td>Gross Scheduled Rent (Market GSR)</td><td class="num">${GSR:,.0f}</td><td class="num">${GSR//UNITS:,.0f}</td><td class="num">${GSR/SF:.2f}</td><td class="num">--</td></tr>
<tr><td>Less: Vacancy &amp; Credit Loss (3%)</td><td class="num">-${GSR*VACANCY_PCT:,.0f}</td><td class="num">-${GSR*VACANCY_PCT//UNITS:,.0f}</td><td class="num">-${GSR*VACANCY_PCT/SF:.2f}</td><td class="num">--</td></tr>
<tr class="summary"><td><strong>Effective Gross Income</strong></td><td class="num"><strong>${CUR_EGI:,.0f}</strong></td><td class="num"><strong>${CUR_EGI//UNITS:,.0f}</strong></td><td class="num"><strong>${CUR_EGI/SF:.2f}</strong></td><td class="num"><strong>100%</strong></td></tr>
</tbody>
</table>
<table>
<thead><tr><th>Expenses</th><th class="num">Annual</th><th class="num">Per Unit</th><th class="num">$/SF</th><th class="num">% EGI</th></tr></thead>
<tbody>
{os_expense_html}
<tr class="summary"><td><strong>Total Expenses</strong></td><td class="num"><strong>${total_exp_calc:,.0f}</strong></td><td class="num"><strong>${total_exp_calc//UNITS:,.0f}</strong></td><td class="num"><strong>${total_exp_calc/SF:.2f}</strong></td><td class="num"><strong>{total_exp_calc/CUR_EGI*100:.1f}%</strong></td></tr>
<tr class="summary"><td><strong>Net Operating Income</strong></td><td class="num"><strong>${NOI_AT_LIST:,.0f}</strong></td><td class="num"><strong>${NOI_AT_LIST//UNITS:,.0f}</strong></td><td class="num"><strong>${NOI_AT_LIST/SF:.2f}</strong></td><td class="num"><strong>{NOI_AT_LIST/CUR_EGI*100:.1f}%</strong></td></tr>
</tbody>
</table>
<p style="font-size:11px;font-style:italic;color:#666;">Property taxes shown at reassessed basis ($2,195,000 &times; 1.17%). Current Prop 13 basis: $12,714. See note [1].</p>
</div>
<div class="os-right">
<h3 class="sub-heading" style="margin-top:0;">Notes to Operating Statement</h3>
<p><strong>[1] Property Taxes:</strong> Shown at current Prop 13 basis ($12,714). At $2.195M purchase, reassessed to ~$25,682 (1.17%). Buyer's actual NOI adjusts by -$12,968.</p>
<p><strong>[2] Insurance:</strong> $4,000/yr per seller estimate ($1,000/unit). Buyer should obtain independent quotes; wildfire and earthquake riders may add $1,000-$2,000.</p>
<p><strong>[3] Water / Sewer:</strong> $4,800/yr ($1,200/unit). Landlord-paid; all utilities included in rent.</p>
<p><strong>[4] Trash:</strong> $1,600/yr ($400/unit). LA Bureau of Sanitation service.</p>
<p><strong>[5] Gas:</strong> $2,400/yr ($600/unit). Landlord-paid; shared metering on 3 meters.</p>
<p><strong>[6] Electric:</strong> $3,600/yr ($900/unit). Landlord-paid; 3 meters (Units 3 & 4 share).</p>
<p><strong>[7] Common Area:</strong> $1,500/yr. Exterior lighting, common spaces.</p>
<p><strong>[8] Repairs &amp; Maintenance:</strong> $4,400/yr ($1,100/unit). Below benchmark due to full 2024-2025 renovation; all systems new.</p>
<p><strong>[9] Contract Services:</strong> $1,500/yr. Landscaping, pest control for a small residential lot.</p>
<p><strong>[10] Administrative:</strong> $1,000/yr. Accounting, legal, miscellaneous.</p>
<p><strong>[11] Marketing:</strong> $500/yr. Minimal in strong rental market with organic demand.</p>
<p><strong>[12] Management (4%):</strong> ${CUR_MGMT:,.0f}/yr. Included for normalization; many 3-4 unit buyers self-manage.</p>
<p><strong>[13] Reserves:</strong> $800/yr ($200/unit). Reduced from standard due to all-new systems.</p>
<p><strong>[14] Other / SCEP:</strong> $454/yr. Sewer Capacity Enhancement Program.</p>
</div>
</div>
""")

# PAGE 14: FINANCIAL SUMMARY
ds_at_list = AT_LIST["debt_service"]
loan_at_list = AT_LIST["loan_amount"]
dp_at_list = AT_LIST["down_payment"]
noi_reassessed = AT_LIST["noi"]
ncf = noi_reassessed - ds_at_list
coc_pct = ncf / dp_at_list * 100 if dp_at_list > 0 else 0
dscr = noi_reassessed / ds_at_list if ds_at_list > 0 else 0
prin_red = AT_LIST["prin_red"]

html_parts.append(f"""
<div class="summary-page">
<div class="summary-banner">Summary</div>
<div class="summary-two-col">
<div class="summary-left">
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Operating Data</th></tr></thead><tbody>
<tr><td>Price</td><td class="num">${LIST_PRICE:,}</td></tr>
<tr><td>Down Payment (25%)</td><td class="num">${dp_at_list:,.0f}</td></tr>
<tr><td>Number of Units</td><td class="num">{UNITS}</td></tr>
<tr><td>Price / Unit</td><td class="num">${LIST_PRICE//UNITS:,}</td></tr>
<tr><td>Price / SF</td><td class="num">${LIST_PRICE/SF:,.0f}</td></tr>
<tr><td>Gross Building SF</td><td class="num">{SF:,}</td></tr>
<tr><td>Lot Size</td><td class="num">{LOT_SF:,} SF</td></tr>
<tr><td>Year Built</td><td class="num">1926 / 2005</td></tr>
</tbody></table>
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Returns (Reassessed)</th></tr></thead><tbody>
<tr><td>Cap Rate</td><td class="num">{AT_LIST['cap']:.2f}%</td></tr>
<tr><td>GRM</td><td class="num">{AT_LIST['grm']:.2f}x</td></tr>
<tr><td>Cash-on-Cash</td><td class="num">{coc_pct:.2f}%</td></tr>
<tr><td>DSCR</td><td class="num">{dscr:.2f}x</td></tr>
</tbody></table>
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Financing</th></tr></thead><tbody>
<tr><td>Loan Amount</td><td class="num">${loan_at_list:,.0f}</td></tr>
<tr><td>Loan Type</td><td class="num">30-Yr Fixed (Fannie/Freddie)</td></tr>
<tr><td>Interest Rate</td><td class="num">{INTEREST_RATE*100:.2f}%</td></tr>
<tr><td>LTV</td><td class="num">{LTV*100:.0f}%</td></tr>
<tr><td>Annual Debt Service</td><td class="num">${ds_at_list:,.0f}</td></tr>
</tbody></table>
</div>
<div class="summary-right">
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Income</th></tr></thead><tbody>
<tr><td>Gross Scheduled Rent</td><td class="num">${GSR:,}</td></tr>
<tr><td>Less: Vacancy (3%)</td><td class="num">-${GSR*VACANCY_PCT:,.0f}</td></tr>
<tr class="summary"><td><strong>Effective Gross Income</strong></td><td class="num"><strong>${CUR_EGI:,.0f}</strong></td></tr>
</tbody></table>
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Cash Flow (Reassessed)</th></tr></thead><tbody>
<tr><td>Net Operating Income</td><td class="num">${noi_reassessed:,.0f}</td></tr>
<tr><td>Less: Debt Service</td><td class="num">-${ds_at_list:,.0f}</td></tr>
<tr class="summary"><td><strong>Net Cash Flow</strong></td><td class="num"><strong>${ncf:,.0f}</strong></td></tr>
<tr><td>Year 1 Principal Reduction</td><td class="num">${prin_red:,.0f}</td></tr>
</tbody></table>
<table class="summary-table"><thead><tr><th colspan="2" class="summary-header">Expenses (Reassessed)</th></tr></thead><tbody>
{sum_expense_html}
<tr class="summary"><td><strong>Total Expenses</strong></td><td class="num"><strong>${AT_LIST['total_exp']:,.0f}</strong></td></tr>
</tbody></table>
</div>
</div>
</div>
""")

# PAGE 15: PRICE REVEAL + PRICING MATRIX
html_parts.append(f"""
<div class="price-reveal">
<div style="text-align:center;margin-bottom:32px;">
<div style="font-size:13px;text-transform:uppercase;letter-spacing:2px;color:#C5A258;font-weight:600;margin-bottom:8px;">Suggested List Price</div>
<div style="font-size:56px;font-weight:700;color:#1B3A5C;line-height:1;">${LIST_PRICE:,}</div>
</div>
<div class="metrics-grid metrics-grid-4">
<div class="metric-card"><span class="metric-value">${LIST_PRICE//UNITS:,}</span><span class="metric-label">Price / Unit</span></div>
<div class="metric-card"><span class="metric-value">${LIST_PRICE/SF:,.0f}</span><span class="metric-label">Price / SF</span></div>
<div class="metric-card"><span class="metric-value">{AT_LIST['cap']:.2f}%</span><span class="metric-label">Cap Rate</span></div>
<div class="metric-card"><span class="metric-value">{AT_LIST['grm']:.2f}x</span><span class="metric-label">GRM</span></div>
</div>
<h3 class="sub-heading">Pricing Matrix</h3>
<div class="table-scroll"><table>
<thead><tr><th class="num">Purchase Price</th><th class="num">Cap Rate</th><th class="num">Cash-on-Cash</th><th class="num">$/Unit</th><th class="num">$/SF</th><th class="num">GRM</th><th class="num">DSCR</th></tr></thead>
<tbody>{matrix_html}</tbody>
</table></div>
<div class="summary-trade-range">
<div class="summary-trade-label">A TRADE PRICE IN THE CURRENT INVESTMENT ENVIRONMENT OF</div>
<div class="summary-trade-prices">$1,950,000 &mdash; $2,100,000</div>
</div>
<h3 class="sub-heading">Pricing Rationale</h3>
<div class="narrative">
<p>The offering price of $2,195,000 is supported by six comparable vintage sales ranging from $1,550,000 to $2,250,000. Three comps exceeded $2,000,000: Victory Blvd ($2,055,000), 5539 Camellia ($2,090,000), and Ben Ave ($2,250,000). The subject's price per unit of $548,750 is competitive within this comp set, and its $15,400/month income is the highest among all comparable properties. A Chase appraisal dated August 2025 valued the property at $2,350,000 using new-construction comps; the offered price represents a 6.6% discount to the appraised value.</p>
<p>The expected sale range of $1,950,000 - $2,100,000 reflects MLS market conditions for renovated vintage 3-4 unit properties. The subject's unpermitted JADU and all-landlord-paid utilities may lead some buyers to discount the fourth unit. Within this range, the property delivers cap rates of 5.5-6.3% on a reassessed basis and GRMs of 10.5-11.4x - attractive returns for a turnkey, transit-adjacent residential asset with all-new systems and no deferred maintenance.</p>
</div>
<div class="condition-note"><strong>Assumptions &amp; Conditions:</strong> All rents based on current/asking rates as of February 2026. Vacant Unit 2 shown at $4,200 market asking rent. Expenses estimated from benchmarks and seller-provided data. No T-12 operating statement available. Insurance at $4,000 per seller estimate. Management fee included at 4% of EGI for normalization. JADU (Unit 4) is unpermitted; income from this unit may not be recognized by all lenders. All utilities are landlord-paid. Financing terms are estimates and may vary by borrower profile and lender. Property taxes reassessed at purchase price per California Proposition 13. Sale comps include CoStar records with limited income data; GRM shown where available.</div>
</div>
""")

# CLOSE FINANCIALS SECTION
html_parts.append("</div>")

# PAGE 16: FOOTER
html_parts.append(f"""
<div class="page-break-marker"></div>
<div class="footer" id="contact">
<img src="{IMG["logo"]}" class="footer-logo" alt="LAAA Team">
<div class="footer-team">
<div class="footer-person">
<img src="{IMG["logan"]}" class="footer-headshot" alt="Logan Ward">
<div class="footer-name">Logan Ward</div>
<div class="footer-title">Associate</div>
<div class="footer-contact"><a href="tel:8182122675">(818) 212-2675</a><br><a href="mailto:Logan.Ward@marcusmillichap.com">Logan.Ward@marcusmillichap.com</a><br>CA License: 02200464</div>
</div>
<div class="footer-person">
<img src="{IMG["glen"]}" class="footer-headshot" alt="Glen Scher">
<div class="footer-name">Glen Scher</div>
<div class="footer-title">Senior Managing Director Investments</div>
<div class="footer-contact"><a href="tel:8182122808">(818) 212-2808</a><br><a href="mailto:Glen.Scher@marcusmillichap.com">Glen.Scher@marcusmillichap.com</a><br>CA License: 01962976</div>
</div>
<div class="footer-person">
<img src="{IMG["filip"]}" class="footer-headshot" alt="Filip Niculete">
<div class="footer-name">Filip Niculete</div>
<div class="footer-title">Senior Managing Director Investments</div>
<div class="footer-contact"><a href="tel:8182122748">(818) 212-2748</a><br><a href="mailto:Filip.Niculete@marcusmillichap.com">Filip.Niculete@marcusmillichap.com</a><br>CA License: 01905352</div>
</div>
</div>
<div class="footer-office">16830 Ventura Blvd, Ste. 100, Encino, CA 91436 | marcusmillichap.com/laaa-team</div>
<div class="footer-disclaimer">This information has been secured from sources we believe to be reliable, but we make no representations or warranties, expressed or implied, as to the accuracy of the information. Buyer must verify the information and bears all risk for any inaccuracies. Marcus &amp; Millichap Real Estate Investment Services, Inc. | License: CA 01930580.</div>
</div>
""")

# JAVASCRIPT
html_parts.append(f"""
<script>
var params = new URLSearchParams(window.location.search);
var client = params.get('client');
if (client) {{ var el = document.getElementById('client-greeting'); if (el) el.textContent = 'Prepared Exclusively for ' + client; }}

document.querySelectorAll('.toc-nav a').forEach(function(link) {{ link.addEventListener('click', function(e) {{ e.preventDefault(); var target = document.querySelector(this.getAttribute('href')); if (target) {{ var navHeight = document.getElementById('toc-nav').offsetHeight; var targetPos = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 4; window.scrollTo({{ top: targetPos, behavior: 'smooth' }}); }} }}); }});

var tocLinks = document.querySelectorAll('.toc-nav a'); var tocSections = []; tocLinks.forEach(function(link) {{ var id = link.getAttribute('href').substring(1); var section = document.getElementById(id); if (section) tocSections.push({{ link: link, section: section }}); }});
function updateActiveTocLink() {{ var navHeight = document.getElementById('toc-nav').offsetHeight + 20; var scrollPos = window.pageYOffset + navHeight; var current = null; tocSections.forEach(function(item) {{ if (item.section.offsetTop <= scrollPos) current = item.link; }}); tocLinks.forEach(function(link) {{ link.classList.remove('toc-active'); }}); if (current) current.classList.add('toc-active'); }}
window.addEventListener('scroll', updateActiveTocLink); updateActiveTocLink();

{sale_map_js}
{active_map_js}
{rent_map_js}
</script>
""")

html_parts.append("</body></html>")

# ============================================================
# WRITE OUTPUT
# ============================================================
html = "".join(html_parts)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nBOV generated: {OUTPUT}")
print(f"File size: {os.path.getsize(OUTPUT) / 1024 / 1024:.2f} MB")
print("Done!")
