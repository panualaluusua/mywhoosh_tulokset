import json
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from palkintolaskuri import get_all_prizes

# --- ASETUKSET ---
# --- ASETUKSET ---
TEMPLATE_FILE = os.path.join("assets", "tuloslistapohja.jpg")
OUTPUT_DIR = "kuvat"
JSON_FILE = "output/all_results.json"
KISARATA_DIR = "kisarata"

# Värit
COLOR_PANEL_BG = (10, 20, 40, 200)   # Tummansininen/Musta, läpinäkyvä
COLOR_PANEL_BORDER = "#00FFFF"       # Neon Syaani
COLOR_HEADER_TEXT = "#FFFFFF"        # Valkoinen (UUSI)
COLOR_CAT_HEADER = "#FF4444"         # Neon Punainen (UUSI)
COLOR_TEXT = "#FFFFFF"               # Valkoinen
COLOR_TEXT_GRAY = "#AAAAAA"          # Vaaleanharmaa (Tiimi)
COLOR_PRIZE = "#FFD700"              # Kulta
COLOR_SUBTITLE = "#FFFFFF"           # Valkoinen (UUSI)
COLOR_TEXT_DIMMED = "#999999"        # Himmeä (ANL/DNF dynaaminen lisäys) - VAIHDETTU VAALEAMMAKSI (oli #555555)
COLOR_ZEBRA = (255, 255, 255, 60)    # Valkoinen, ~23% opacity (oli 30)

# Fontit (Windows oletukset)
FONT_REGULAR = "arial.ttf"
FONT_BOLD = "arialbd.ttf"

# Sijainnit (Skaalattu 1080px leveydelle)
TARGET_WIDTH = 1080
START_Y = 260                        # Tiivistetty takaisin jotta tuloslista pääosassa (oli 320)
MAX_Y = 1800                         # Alarajan turvamarginaali 
MARGIN_X = 20                        # Reunamarginaali
PANEL_RADIUS = 20
# ... (omitted constants)

# ... (omitted functions)

def create_images(json_file=JSON_FILE, race_name="", race_date="", is_final=False):
    # ... (omitted checks)
    
    # Päivitä Y-koordinaatit skaalauksen suhteessa
    scale_ratio = TARGET_WIDTH / 572.0
    start_y_scaled = int(START_Y * scale_ratio)
    max_y_scaled = int(img.height - (130 * scale_ratio)) 

    # ... (omitted scaling logic)

ROW_HEIGHT = 60                      # Kasvatettu rivikorkeus
CAT_HEADER_HEIGHT = 80               # Kasvatettu otsikkokorkeus

# Sarakkeet (X-koordinaatit)
COL_RANK_X = 40      # Vasen
COL_NAME_X = 120     # Vasen (siirretty vasemmalle antamaan tilaa nimelle)
COL_TIME_X_ALIGN = 525 # Oikea tasaus (aika)
COL_WKG_X_ALIGN = 650 # W/kg Oikea tasaus
COL_TEAM_X = 680     # Vasen (tiimin alku)
COL_PRIZE_X_ALIGN = 1040 # Oikea tasaus (loppupiste) - LEVENNETTY
PADDING = 15         # Minimum spacing between columns
 
# --- KISARATA-APUFUNKTIOT ---

def load_kisarata_data(gender="men"):
    """Lataa kisarata-JSON ja silhuettikuva. Palauttaa (data_dict, silhouette_image) tai (None, None)."""
    json_path = os.path.join(KISARATA_DIR, f"kisarata_{gender}.json")
    sil_path = os.path.join(KISARATA_DIR, f"{gender}_silhuetti.png")

    data = None
    silhouette = None

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Kisaratatiedot ladattu: {json_path}")
        except Exception as e:
            print(f"Varoitus: Kisarata-JSON-lataus epäonnistui: {e}")
    else:
        print(f"Varoitus: Kisarata-JSONia ei löydy: {json_path}")

    if os.path.exists(sil_path):
        try:
            silhouette = Image.open(sil_path).convert("RGBA")
            print(f"Silhuetti ladattu: {sil_path}")
        except Exception as e:
            print(f"Varoitus: Silhuetin lataus epäonnistui: {e}")
    else:
        print(f"Varoitus: Silhuettia ei löydy: {sil_path} (jatketaan ilman)")

    return data, silhouette


def draw_race_info_panel(img, draw, kisarata_data, silhouette_img, scale_ratio, panel_y):
    """Piirrä vapaasti leijuva ratasilhuetti + kisan päätiedot."""
    if not kisarata_data:
        return img, draw

    rd = kisarata_data.get("race_details", {})
    wc = kisarata_data.get("weather_conditions", {})
    tactical = kisarata_data.get("tactical_analysis", "")

    location = rd.get("location", "")
    distance = rd.get("distance_km", "")
    elevation = rd.get("elevation_m", "")
    laps = rd.get("laps", "")
    date_str = rd.get("date", "")
    max_wind = wc.get("max_wind_kmh", 0)

    panel_x0 = 20
    panel_x1 = img.width - 20
    panel_w = panel_x1 - panel_x0

    # --- Fontit ---
    try:
        font_info_large = ImageFont.truetype(FONT_BOLD, int(22 * scale_ratio))
        font_info_med = ImageFont.truetype(FONT_REGULAR, int(20 * scale_ratio))
        font_tactical_italic = ImageFont.truetype("ariali.ttf", int(22 * scale_ratio)) # Kasvatettu koko entisestään (oli 20)
        font_emoji = ImageFont.truetype("seguiemj.ttf", int(18 * scale_ratio))
    except IOError:
        font_info_large = ImageFont.load_default()
        font_info_med = ImageFont.load_default()
        font_tactical_italic = ImageFont.load_default()
        font_emoji = font_info_med

    # Parse "kisat" from race name
    race_name = rd.get("name", "")
    kisat_str = "Kisa"
    if "Qualifier" in race_name:
        import re
        match = re.search(r"Qualifier Race (\d+)", race_name)
        if match:
             kisat_str = f"Yksilökisa {match.group(1)}"
        else:
             kisat_str = "Yksilökisa"
    elif "Final" in race_name or "Finaali" in race_name:
        kisat_str = "Joukkuekisa"

    gender_str = "Miehet" if "Men" in race_name else ("Naiset" if "Women" in race_name else "")
    if gender_str:
        kisat_str = f"{kisat_str} - {gender_str}"
    # Ei lisätä enää aikaa/päivämäärää

    # --- Sijainnit ---
    # Keskilinja on sivun keskellä
    center_x = img.width // 2

    # Silhuetin maksimikoko
    sil_max_w = int(panel_w * 0.45)
    sil_max_h = int(90 * scale_ratio)
    
    sil_x, sil_y, sil_w, sil_h = 0, 0, 0, 0
    
    # Ratkaisemme vasemmalle puolelle silhuetin ja ylle 'radan nimi'
    left_block_x = img.width // 4 - int(30 * scale_ratio) # Vähän vasemmalle keskustasta
    


    if silhouette_img:
        orig_w, orig_h = silhouette_img.size
        
        # Etsitään näkyvän silhuetin todelliset rajat (ei läpinäkyvää aluetta)
        bbox = silhouette_img.getbbox()
        if bbox:
            vis_left, vis_top, vis_right, vis_bottom = bbox
            vis_w = vis_right - vis_left
            
            # Leikataan noin 1% nimenomaan näkyvän viivan alusta ja lopusta
            crop_pixels = int(vis_w * 0.02)
            if crop_pixels > 0:
                new_left = vis_left + crop_pixels
                new_right = vis_right - crop_pixels
                
                if new_left < new_right:
                    silhouette_img = silhouette_img.crop((new_left, 0, new_right, orig_h))
                    orig_w, orig_h = silhouette_img.size
            
        ratio = min(sil_max_w / orig_w, sil_max_h / orig_h)
        sil_w = int(orig_w * ratio)
        sil_h = int(orig_h * ratio)
        sil_resized = silhouette_img.resize((sil_w, sil_h), Image.Resampling.LANCZOS)
        
        # Sijoitetaan silhuetti
        sil_x = left_block_x - (sil_w // 2)
        sil_y = panel_y + int(8 * scale_ratio) # Nostettu entisestään lähemmäs otsikkoa
        img.paste(sil_resized, (sil_x, sil_y), sil_resized)
        draw = ImageDraw.Draw(img)

    # 1. Radan Nimi (Silhuetin yläpuolelle, selvästi limittäin silhuetin kanssa)
    radan_nimi_y = panel_y + int(10 * scale_ratio) # Painettu alemmas silhuetin päälle

    # Dynaaminen fonttikoko (lyhennä jos liian leveä)
    max_nimi_w = (left_block_x - 20) * 2
    current_size = int(22 * scale_ratio)
    current_font = font_info_large
    
    while current_size >= 10:
        bbox = draw.textbbox((0, 0), location, font=current_font)
        nimi_w = bbox[2] - bbox[0]
        if nimi_w <= max_nimi_w:
            break
        current_size -= 1
        try:
            current_font = ImageFont.truetype(FONT_BOLD, current_size)
        except IOError:
            break

    bbox = draw.textbbox((0, 0), location, font=current_font)
    nimi_w = bbox[2] - bbox[0]
    draw.text((left_block_x - (nimi_w // 2), radan_nimi_y), location, font=current_font, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

    # 2. Pystysarake Oikealle (Silhouette/Left Blockin oikealle puolelle)
    right_block_x = img.width // 2 - int(20 * scale_ratio) # Siirretty vasemmalle lähemmäs silhuettia
    col_y = panel_y + int(8 * scale_ratio) # Siirretty hieman alaspäin
    line_spacing = int(28 * scale_ratio) # Kasvatettu riviväli paremman luettavuuden vuoksi
    emoji_offset = int(24 * scale_ratio)

    # Piirretään tumma läpikuultava taustalevy otsikkotekstien taakse luettavuuden parantamiseksi
    # Tämä piirretään vain oikean lohkon alle
    bg_overlay = Image.new('RGBA', img.size, (0,0,0,0))
    bg_draw = ImageDraw.Draw(bg_overlay)
    
    # Laske laatikon leveys tekstien perusteella (arvio)
    box_width = int(280 * scale_ratio) 
    box_height = int(95 * scale_ratio) # Palautettu 95
    
    bg_draw.rounded_rectangle(
        [right_block_x - int(10 * scale_ratio), col_y - int(10 * scale_ratio), right_block_x + box_width, col_y + box_height],
        radius=10,
        fill=(0, 0, 0, 140) # Läpikuultava musta
    )
    img = Image.alpha_composite(img, bg_overlay)
    draw = ImageDraw.Draw(img)

    draw.text((right_block_x, col_y), "🏁", font=font_emoji, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
    draw.text((right_block_x + emoji_offset, col_y), kisat_str, font=font_info_med, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
    col_y += line_spacing
    
    draw.text((right_block_x, col_y), "📏", font=font_emoji, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
    distance_str = f"{distance} km"
    draw.text((right_block_x + emoji_offset, col_y), distance_str, font=font_info_med, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")

    col_y += line_spacing
    
    draw.text((right_block_x, col_y), "⛰️", font=font_emoji, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
    elevation_str = f"{elevation} m"
    draw.text((right_block_x + emoji_offset, col_y), elevation_str, font=font_info_med, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")

    if date_str:
        import datetime
        formatted_date = date_str
        try:
            # Yritetään parsia englanninkielinen päivämäärä esim. "22nd February 2026" tai "1st March 2026"
            # Poistetaan ordinaalit (st, nd, rd, th)
            import re
            clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
            dt = datetime.datetime.strptime(clean_date, "%d %B %Y")
            formatted_date = dt.strftime("%d/%m/%Y")
        except ValueError:
            pass # Jos parsinta epäonnistuu, pidetään alkuperäinen
            
        bbox = draw.textbbox((0, 0), elevation_str, font=font_info_med)
        elev_w = bbox[2] - bbox[0]
        date_x = right_block_x + emoji_offset + elev_w + int(20 * scale_ratio)
        draw.text((date_x, col_y), "📅", font=font_emoji, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")
        draw.text((date_x + emoji_offset, col_y), formatted_date, font=font_info_med, fill="#FFFFFF", stroke_width=1, stroke_fill="#000000")

    # 3. Kisa-analyysilause (Toistaiseksi piilotettu käyttäjän pyynnöstä tilaa säästääkseen)
    # if tactical:
    #     max_chars = 85 # Enemmän tilaa vasemmalle siirron ansiosta
    #     if len(tactical) > max_chars:
    #         tactical_short = tactical[:max_chars - 1] + "\u2026"
    #     else:
    #         tactical_short = tactical
    #         
    #     tactical_quote = f'"{tactical_short}"'
    #     col_y += line_spacing + int(15 * scale_ratio)  # Selvästi enemmän väliä ylempään tietoon
    #     
    #     # Aloitetaan heti silhuetin oikealta puolelta (tai varalla hieman vasemmalta)
    #     quote_x = sil_x + sil_w + int(20 * scale_ratio) if silhouette_img else left_block_x
    #     
    #     draw.text((quote_x, col_y), tactical_quote, font=font_tactical_italic, fill="#FFFFFF", stroke_width=2, stroke_fill="#000000")

    return img, draw


def shorten_team_name(name):
    if not name or name == "-":
        return "-"
    
    # Korvaa yleiset
    name = name.replace("RIDE CLUB FINLAND", "RCF")
    name = name.replace("Ride Club Finland", "RCF")
    
    # Lyhennä jos yhä pitkä
    if len(name) > 18: # Hieman enemmän tilaa nyt
        return name[:16] + "..."
    return name

def draw_text_fitted(draw, text, x, y, max_width, font, fill, min_font_size=12):
    """Draw text that automatically scales down to fit within max_width."""
    current_size = font.size
    current_font = font
    
    while current_size >= min_font_size:
        bbox = draw.textbbox((0, 0), text, font=current_font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            draw.text((x, y), text, font=current_font, fill=fill)
            return current_font
        
        # Reduce font size
        current_size -= 2
        try:
            current_font = ImageFont.truetype(font.path, current_size)
        except:
            # Fallback if font path not available
            current_font = ImageFont.truetype(FONT_BOLD if "bold" in str(font).lower() else FONT_REGULAR, current_size)
    
    # Draw with minimum size if still doesn't fit
    draw.text((x, y), text, font=current_font, fill=fill)
    return current_font

def create_images(json_file=JSON_FILE, kisarata_gender="men", is_final=False):
    if not os.path.exists(json_file):
        print(f"Virhe: Tiedostoa {json_file} ei löydy.")
        return
    if not os.path.exists(TEMPLATE_FILE):
        print(f"Virhe: Pohjakuvaa {TEMPLATE_FILE} ei löydy.")
        return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Laske palkinnot etukäteen
    prize_map, team_rank_map = get_all_prizes(json_file, is_final)

    # Lataa kisarata-data ja silhuetti
    kisarata_data, silhouette_img = load_kisarata_data(kisarata_gender)

    # Lataa data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Suodata suomalaiset (ID 82)
    finnish_riders = [r for r in data if r.get('userCountryFlag') == 82]
    
    if not finnish_riders:
        print("Ei suomalaisia ajajia datassa.")
        return

    # Järjestä: Kategoria -> (ANL/DNF pohjalle) -> Sijoitus
    def get_sort_key(x):
        rank = x.get('calculated_rank', 9999)
        status = x.get('selectionStatus', '')
        time_ms = x.get('finishedTime', 0)
        is_bottom = 1 if status == "ANL" or time_ms >= 999999999 or time_ms == 0 else 0
        return (x.get('categoryId', 99), is_bottom, rank)
        
    finnish_riders.sort(key=get_sort_key)

    # Alusta kuva ja skaalaa se
    original_img = Image.open(TEMPLATE_FILE).convert("RGBA")
    aspect_ratio = original_img.height / original_img.width
    target_height = int(TARGET_WIDTH * aspect_ratio)
    img = original_img.resize((TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)
    
    # Päivitä Y-koordinaatit skaalauksen suhteessa
    scale_ratio = TARGET_WIDTH / 572.0
    start_y_scaled = int(START_Y * scale_ratio)
    max_y_scaled = int(img.height - (130 * scale_ratio)) # Jätä enemmän tilaa logoille alhaalla (40 -> 130)

    # --- DYNAAMINEN SKAALAUS SISÄLLÖLLE ---
    available_height = max_y_scaled - start_y_scaled
    
    # Laske rivit ja väliotsikot
    num_riders = len(finnish_riders)
    num_cats = 0
    curr_cat = None
    for r in finnish_riders:
        c = r.get('categoryId', 'Unknown')
        if c != curr_cat:
            num_cats += 1
            curr_cat = c
            
    # Oletusarvot (Isommat fontit)
    current_row_height = ROW_HEIGHT
    current_cat_height = CAT_HEADER_HEIGHT
    current_font_size_large = 46 # Nimi (pysyy samana)
    current_font_size_med = 42   # Aika, Palkinto (oli 36 -> 42)
    current_font_size_small = 34 # Tiimi (oli 29 -> 34)
    
    required_height = (num_riders * ROW_HEIGHT) + (num_cats * CAT_HEADER_HEIGHT) + 40
    
    print(f"Tarvittava tila: {required_height}px, Käytettävissä: {available_height}px")
    
    scale_factor = 1.0
    if required_height > available_height:
        scale_factor = available_height / required_height
        scale_factor *= 0.98 # Pieni marginaali
        
        print(f"Skaalataan sisältöä kertoimella: {scale_factor:.2f}")
        
        current_row_height = int(ROW_HEIGHT * scale_factor)
        current_cat_height = int(CAT_HEADER_HEIGHT * scale_factor)
        current_font_size_large = int(46 * scale_factor) # Nimi
        current_font_size_med = int(42 * scale_factor)   # Aika, Palkinto (oli 36 -> 42)
        current_font_size_small = int(34 * scale_factor) # Tiimi (oli 29 -> 34)

    # Lataa fontit
    try:
        font_header = ImageFont.truetype(FONT_BOLD, int(24 * scale_ratio)) 
        font_cat = ImageFont.truetype(FONT_BOLD, int(32 * scale_factor))
        font_large = ImageFont.truetype(FONT_BOLD, current_font_size_large)
        font_med = ImageFont.truetype(FONT_REGULAR, current_font_size_med)
        font_med_bold = ImageFont.truetype(FONT_BOLD, current_font_size_med) # Palkinto
        font_small = ImageFont.truetype(FONT_REGULAR, current_font_size_small)
        font_subtitle = ImageFont.truetype(FONT_BOLD, int(36 * scale_ratio)) # Iso subtitle
    except IOError:
        font_header = ImageFont.load_default()
        font_cat = ImageFont.load_default()
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_med_bold = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()

    # Load Icons
    try:
        icon_sprint_jersey = Image.open(os.path.join("assets", "sprint_jersey.png")).convert("RGBA")
        icon_kom_jersey = Image.open(os.path.join("assets", "kom_jersey.png")).convert("RGBA")
        icon_sprint_seg = Image.open(os.path.join("assets", "sprint_icon.png")).convert("RGBA")
        icon_kom_seg = Image.open(os.path.join("assets", "kom_icon.png")).convert("RGBA")
        
        # Resize icons (adjust size as needed)
        # DOUBLED SIZES as requested
        icon_size_large = int(60 * scale_factor) # Was 30
        icon_size_small = int(40 * scale_factor) # Was 20
        
        icon_sprint_jersey = icon_sprint_jersey.resize((icon_size_large, icon_size_large), Image.Resampling.LANCZOS)
        icon_kom_jersey = icon_kom_jersey.resize((icon_size_large, icon_size_large), Image.Resampling.LANCZOS)
        icon_sprint_seg = icon_sprint_seg.resize((icon_size_small, icon_size_small), Image.Resampling.LANCZOS)
        icon_kom_seg = icon_kom_seg.resize((icon_size_small, icon_size_small), Image.Resampling.LANCZOS)
        
    except Exception as e:
        print(f"Warning: Could not load icons: {e}")
        icon_sprint_jersey = None

    # Piirrä taustalaatikko
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    box_x0 = MARGIN_X
    box_y0 = start_y_scaled - 60 
    box_x1 = img.width - MARGIN_X
    box_y1 = max_y_scaled
    
    overlay_draw.rounded_rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        radius=PANEL_RADIUS,
        fill=COLOR_PANEL_BG,
        outline=COLOR_PANEL_BORDER,
        width=3
    )
    
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Piirrä PÄÄOTSIKKO
    title_text = "Sunday Race Club"

    try:
        # Kokeile ladata fontti, käytä isompaa kokoa
        font_main_title = ImageFont.truetype(FONT_BOLD, int(55 * scale_ratio)) 
    except IOError:
        font_main_title = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), title_text, font=font_main_title)
    text_width = bbox[2] - bbox[0]
    title_x = (img.width - text_width) / 2
    title_y = int(50 * scale_ratio) # Kiinteä sijainti ylhäällä/keskellä
    
    # Piirrä teksti mustalla reunuksella (outline) ja varjolla
    # Varjo
    draw.text((title_x + 3, title_y + 3), title_text, font=font_main_title, fill="#000000")
    # Outline
    draw.text((title_x, title_y), title_text, font=font_main_title, fill="#FFFFFF", stroke_width=4, stroke_fill="#000000")

    # Piirrä kisarata-paneeli (silhuetti + kisan tiedot)
    race_info_y = int(115 * scale_ratio)
    img, draw = draw_race_info_panel(
        img, draw, kisarata_data, silhouette_img, scale_ratio, race_info_y
    )

    # Piirrä sarakeotsikot
    y = start_y_scaled
    draw.text((COL_RANK_X, y - 40), "SIJ.", font=font_header, fill=COLOR_HEADER_TEXT)
    draw.text((COL_NAME_X, y - 40), "NIMI", font=font_header, fill=COLOR_HEADER_TEXT)
    
    # Oikealle tasatut otsikot
    # Laske "AIKA" leveys ja sijoita oikein
    bbox = draw.textbbox((0, 0), "AIKA", font=font_header)
    w = bbox[2] - bbox[0]
    draw.text((COL_TIME_X_ALIGN - w, y - 40), "AIKA", font=font_header, fill=COLOR_HEADER_TEXT)

    # Laske "W/kg" leveys ja sijoita oikein
    bbox = draw.textbbox((0, 0), "W/kg", font=font_header)
    w = bbox[2] - bbox[0]
    draw.text((COL_WKG_X_ALIGN - w, y - 40), "W/kg", font=font_header, fill=COLOR_HEADER_TEXT)
    
    draw.text((COL_TEAM_X, y - 40), "TIIMI", font=font_header, fill=COLOR_HEADER_TEXT)
    
    # Laske "$" leveys ja sijoita oikein
    bbox = draw.textbbox((0, 0), "$", font=font_header)
    w = bbox[2] - bbox[0]
    draw.text((COL_PRIZE_X_ALIGN - w, y - 40), "$", font=font_header, fill=COLOR_HEADER_TEXT)

    current_cat = None
    row_index = 0
    
    # PRE-PASS: Etsi yhtenäinen fonttikoko kaikille nimille
    uniform_name_size = current_font_size_large
    for rider in finnish_riders:
        name = rider.get('userFullName', 'Unknown')
        time_ms = rider.get('finishedTime', 0)
        status = rider.get('selectionStatus', '')
        
        if status == "ANL":
            time_str = "-"
        elif time_ms >= 999999999 or time_ms == 0:
            time_str = "DNF"
        else:
            seconds = (time_ms / 1000)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            time_str = "{:d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

        bbox_time = draw.textbbox((0, 0), time_str, font=font_med)
        time_width = bbox_time[2] - bbox_time[0]
        time_start_x = COL_TIME_X_ALIGN - time_width
        max_name_width = time_start_x - COL_NAME_X - PADDING
        
        test_size = uniform_name_size
        try:
            test_font = ImageFont.truetype(FONT_BOLD, test_size)
            while test_size >= 12:
                bbox_name = draw.textbbox((0, 0), name, font=test_font)
                if bbox_name[2] - bbox_name[0] <= max_name_width:
                    break
                test_size -= 2
                test_font = ImageFont.truetype(FONT_BOLD, test_size)
        except IOError:
            pass
            
        if test_size < uniform_name_size:
            uniform_name_size = test_size

    # Päivitä globaali font_large yhtenäiseen kokoon
    try:
        font_large = ImageFont.truetype(FONT_BOLD, uniform_name_size)
        font_med = ImageFont.truetype(FONT_REGULAR, uniform_name_size)
        font_med_bold = ImageFont.truetype(FONT_BOLD, uniform_name_size)
        font_small = ImageFont.truetype(FONT_REGULAR, uniform_name_size)
    except IOError:
        pass

    for rider in finnish_riders:
        # Tarkista kategoria
        rider_cat = rider.get('categoryId', 'Unknown')
        if rider_cat != current_cat:
            current_cat = rider_cat
            y += int(15 * scale_factor) # Padding (increased)
            
            # Kategoriaotsikko background
            cat_bg_overlay = Image.new('RGBA', img.size, (0,0,0,0))
            cat_bg_draw = ImageDraw.Draw(cat_bg_overlay)
            cat_bg_draw.rectangle(
                [box_x0, y - 5, box_x1, y + current_cat_height - 25],
                fill=(255, 68, 68, 40) # Semi-transparent red
            )
            img = Image.alpha_composite(img, cat_bg_overlay)
            draw = ImageDraw.Draw(img) # Update after composite
            
            # Kategoriaotsikko
            draw.text((MARGIN_X + 20, y), f"KATEGORIA {current_cat}", font=font_cat, fill=COLOR_CAT_HEADER)
            
            # Paksumpi Viiva
            line_y = y + int(40 * scale_factor)
            draw.line([(box_x0, line_y), (box_x1, line_y)], fill=COLOR_CAT_HEADER, width=4)
            
            y += current_cat_height
            row_index = 0 # Nollaa raidoitus laskuri per kategoria (valinnainen, mutta näyttää siistimmältä)

        # Zebra-raidoitus
        if row_index % 2 == 1:
            # Piirrä himmeä tausta riville
            zebra_overlay = Image.new('RGBA', img.size, (0,0,0,0))
            zebra_draw = ImageDraw.Draw(zebra_overlay)
            zebra_draw.rectangle(
                [box_x0 + 5, y, box_x1 - 5, y + current_row_height],
                fill=COLOR_ZEBRA
            )
            img = Image.alpha_composite(img, zebra_overlay)
            draw = ImageDraw.Draw(img) # Päivitä draw-objekti

        # Datan valmistelu
        rank = str(rider.get('calculated_rank', '-'))
        name = rider.get('userFullName', 'Unknown')
        team = rider.get('teamName', '-')
        status = rider.get('selectionStatus', '')
        
        # Tiiminimen käsittely
        team = shorten_team_name(team)
        if is_final:
            team_rank = team_rank_map.get(rider.get('userFullName')) # Käytä nimeä avaimena
            if team_rank:
                team = f"{team} (#{team_rank})"
        
        # Palkinto
        prize = prize_map.get(name, 0)
        prize_str = ""
        if prize > 0:
            prize_str = f"${int(prize)}" # Kokonaisluku

        # Aika
        time_ms = rider.get('finishedTime', 0)
        if time_ms >= 999999999 or time_ms == 0:
            time_str = "DNF"
        else:
            seconds = (time_ms / 1000)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            time_str = "{:d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

        # Käsittele DSQ (ANL)
        is_dimmed = False
        if time_str == "DNF":
            is_dimmed = True
            
        if status == "ANL":
            rank = "ANL"
            time_str = "-"
            prize_str = "" # Ei palkintoa näkyviin vaikka olisi vahingossa laskettu
            is_dimmed = True
            
        txt_color = COLOR_TEXT_DIMMED if is_dimmed else COLOR_TEXT
        prize_color = COLOR_TEXT_DIMMED if is_dimmed else COLOR_PRIZE

        # Piirrä tekstit
        # Sijoitus
        draw.text((COL_RANK_X, y), rank, font=font_med, fill=txt_color)
        
        # Nimi (Iso) - with dynamic width constraint
        # Calculate where time will be positioned to avoid overlap
        bbox_time = draw.textbbox((0, 0), time_str, font=font_med)
        time_width = bbox_time[2] - bbox_time[0]
        time_start_x = COL_TIME_X_ALIGN - time_width
        max_name_width = time_start_x - COL_NAME_X - PADDING
        
        draw_text_fitted(draw, name, COL_NAME_X, y, max_name_width, font_large, txt_color)
        
        # ICONS LOGIC
        # Load detailed prize data if available to determine icons
        
        # Draw icons after name
        name_bbox = draw.textbbox((0, 0), name, font=font_large)
        name_width = name_bbox[2] - name_bbox[0]
        icon_x = COL_NAME_X + name_width + 15
        
        # Load palkintodata.json here for now (quick fix)
        palkinto_file = "output/palkintodata.json"
        
        if False: # ICONS DISABLED
            if os.path.exists(palkinto_file):
                try:
                    with open(palkinto_file, 'r', encoding='utf-8') as pf:
                        p_data = json.load(pf)
                        p_riders = p_data.get('prizes', [])
                        # Find this rider
                        p_rider = next((p for p in p_riders if p['nimi'] == name), None)
                        if p_rider:
                            achievements = p_rider.get('achievements', [])
                            
                            # OVERRIDE PRIZE WITH TOTAL FROM PALKINTODATA
                            # This ensures the graphic matches the JSON exactly
                            total_prize = p_rider.get('total', 0)
                            if total_prize > 0:
                                prize_str = f"${int(total_prize)}"
                                # Re-draw prize with correct amount (overwrite previous if needed, but we haven't drawn it yet)
                            
                            # MANUAL OVERRIDE FOR ANTTI PONNI (User Request)
                            if name.lower() == "antti ponni":
                                achievements = ["kom_overall", "kom_segment"]

                            # Draw icons based on achievements
                            # Order: Sprint Overall, KOM Overall, Sprint Segment, KOM Segment
                            
                            if "sprint_overall" in achievements and icon_sprint_jersey:
                                img.paste(icon_sprint_jersey, (int(icon_x), int(y - 5)), icon_sprint_jersey) # Moved up
                                icon_x += icon_size_large + 5
                                
                            if "kom_overall" in achievements and icon_kom_jersey:
                                img.paste(icon_kom_jersey, (int(icon_x), int(y - 5)), icon_kom_jersey) # Moved up
                                icon_x += icon_size_large + 5
                                
                            if "sprint_segment" in achievements and icon_sprint_seg:
                                img.paste(icon_sprint_seg, (int(icon_x), int(y + 10)), icon_sprint_seg) # Slightly lower
                                icon_x += icon_size_small + 5
                                
                            if "kom_segment" in achievements and icon_kom_seg:
                                img.paste(icon_kom_seg, (int(icon_x), int(y + 10)), icon_kom_seg) # Slightly lower
                                icon_x += icon_size_small + 5
                                    
                except Exception:
                    pass

        # Aika (Oikea tasaus)
        bbox = draw.textbbox((0, 0), time_str, font=font_med)
        w = bbox[2] - bbox[0]
        draw.text((COL_TIME_X_ALIGN - w, y), time_str, font=font_med, fill=txt_color)
        
        # W/kg (Oikea tasaus)
        raw_wkg = rider.get('wattPerKG', 0)
        wkg_str = f"{float(raw_wkg):.1f}" if raw_wkg else "-"
        if status == "ANL" or time_str == "DNF" or time_str == "-":
            wkg_str = "-"
        bbox_wkg = draw.textbbox((0, 0), wkg_str, font=font_med)
        w_wkg = bbox_wkg[2] - bbox_wkg[0]
        draw.text((COL_WKG_X_ALIGN - w_wkg, y), wkg_str, font=font_med, fill=txt_color)
        
        # Tiimi (Harmaa, pieni) - with dynamic width constraint
        tiimi_color = COLOR_TEXT_DIMMED if is_dimmed else COLOR_TEXT_GRAY
        if prize_str:
            bbox_prize = draw.textbbox((0, 0), prize_str, font=font_med_bold)
            prize_width = bbox_prize[2] - bbox_prize[0]
            prize_start_x = COL_PRIZE_X_ALIGN - prize_width
            max_team_width = prize_start_x - COL_TEAM_X - PADDING
        else:
            max_team_width = COL_PRIZE_X_ALIGN - COL_TEAM_X - PADDING
        
        draw_text_fitted(draw, team, COL_TEAM_X, y + 5, max_team_width, font_small, tiimi_color)
        
        # Palkinto (Kulta, Oikea tasaus)
        if prize_str:
            bbox = draw.textbbox((0, 0), prize_str, font=font_med_bold)
            w = bbox[2] - bbox[0]
            draw.text((COL_PRIZE_X_ALIGN - w, y), prize_str, font=font_med_bold, fill=prize_color)

        y += current_row_height
        row_index += 1

    # Tallenna — käytä kisarata-JSON:n tietoja tiedostonimeen
    base_filename = "tulokset_kooste"
    if kisarata_data:
        rd = kisarata_data.get("race_details", {})
        race_name = rd.get("name", "")
        race_date = rd.get("date", "")
        if race_name:
            safe_name = "".join([c if c.isalnum() else "_" for c in race_name]).strip("_")
            while "__" in safe_name:
                safe_name = safe_name.replace("__", "_")
            if safe_name:
                base_filename = f"{base_filename}_{safe_name}"
        if race_date:
            safe_date = "".join([c if c.isalnum() else "_" for c in race_date]).strip("_")
            while "__" in safe_date:
                safe_date = safe_date.replace("__", "_")
            if safe_date:
                base_filename = f"{base_filename}_{safe_date}"

    filename = os.path.join(OUTPUT_DIR, f"{base_filename}.png")
    img.convert("RGB").save(filename)
    print(f"Tallennettu: {filename}")

if __name__ == "__main__":
    import sys
    import os
    
    # Yritä importata metadata-funktio palkintolaskurista
    # Lisätään nykyinen hakemisto polkuun varmuuden vuoksi
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from palkintolaskuri import get_event_metadata
    except ImportError:
        # Fallback jos import ei toimi
        def get_event_metadata(json_file="full_event_details.json"):
            # Yritä etsiä juuresta tai ylempää
            candidates = [
                os.path.join(os.getcwd(), json_file),
                os.path.join(os.path.dirname(os.getcwd()), json_file),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", json_file)
            ]
            
            target_file = None
            for c in candidates:
                if os.path.exists(c):
                    target_file = c
                    break
            
            if not target_file:
                return None, None
                
            try:
                import json
                with open(target_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "data" in data and "ListOfDays" in data["data"]:
                    days = data["data"]["ListOfDays"]
                    if days:
                        stage = days[0].get("Stages", [])[0]
                        raw_date = stage.get("StartDate", "")
                        if raw_date:
                            parts = raw_date.split("-")
                            if len(parts) == 3:
                                race_date = f"{int(parts[2])}.{int(parts[1])}.{parts[0]}"
                            else:
                                race_date = raw_date
                        else:
                            race_date = ""
                        race_name = stage.get("DayName", stage.get("Name", ""))
                        return race_name, race_date
            except:
                pass
            return None, None

    # Argumenttien käsittely
    json_file = "output/all_results.json"
    kisarata_gender = "men"
    is_final = False

    # 1. Tarkista CLI argumentit
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    if len(sys.argv) > 2:
        kisarata_gender = sys.argv[2]  # "men" tai "women"

    if "--final" in sys.argv:
        is_final = True
    if "--women" in sys.argv:
        kisarata_gender = "women"

    create_images(json_file, kisarata_gender, is_final)
