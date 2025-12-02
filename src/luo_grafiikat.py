import json
import os
from PIL import Image, ImageDraw, ImageFont
from palkintolaskuri import get_all_prizes

# --- ASETUKSET ---
# --- ASETUKSET ---
TEMPLATE_FILE = os.path.join("assets", "tuloslistapohja.jpg")
OUTPUT_DIR = "kuvat"
JSON_FILE = "all_results.json"

# Värit
COLOR_PANEL_BG = (10, 20, 40, 200)   # Tummansininen/Musta, läpinäkyvä
COLOR_PANEL_BORDER = "#00FFFF"       # Neon Syaani
COLOR_HEADER_TEXT = "#FFFFFF"        # Valkoinen (UUSI)
COLOR_CAT_HEADER = "#FF4444"         # Neon Punainen (UUSI)
COLOR_TEXT = "#FFFFFF"               # Valkoinen
COLOR_TEXT_GRAY = "#AAAAAA"          # Vaaleanharmaa (Tiimi)
COLOR_PRIZE = "#FFD700"              # Kulta
COLOR_SUBTITLE = "#FFFFFF"           # Valkoinen (UUSI)
COLOR_ZEBRA = (255, 255, 255, 13)    # Valkoinen, 5% opacity (255 * 0.05 = 12.75)

# Fontit (Windows oletukset)
FONT_REGULAR = "arial.ttf"
FONT_BOLD = "arialbd.ttf"

# Sijainnit (Skaalattu 1080px leveydelle)
TARGET_WIDTH = 1080
START_Y = 380                        # Listan alkukohta (otsikon alla) - Säädä tarvittaessa skaalauksen jälkeen
MAX_Y = 1800                         # Alarajan turvamarginaali (logot) - Skaalattu ylöspäin
MARGIN_X = 20                        # Reunamarginaali
PANEL_RADIUS = 20
ROW_HEIGHT = 50                      # Kasvatettu rivikorkeus
CAT_HEADER_HEIGHT = 70               # Kasvatettu otsikkokorkeus

# Sarakkeet (X-koordinaatit)
COL_RANK_X = 40      # Vasen
COL_NAME_X = 140     # Vasen
COL_TIME_X_ALIGN = 620 # Oikea tasaus (loppupiste) - SIIRRETTY VASEMMALLE
COL_TEAM_X = 660     # Vasen - SIIRRETTY VASEMMALLE
COL_PRIZE_X_ALIGN = 1040 # Oikea tasaus (loppupiste) - LEVENNETTY

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

def create_images(json_file=JSON_FILE, race_name="", race_date="", is_final=False):
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

    # Lataa data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Suodata suomalaiset (ID 82)
    finnish_riders = [r for r in data if r.get('userCountryFlag') == 82]
    
    if not finnish_riders:
        print("Ei suomalaisia ajajia datassa.")
        return

    # Järjestä: Kategoria -> Sijoitus
    finnish_riders.sort(key=lambda x: (x.get('categoryId', 99), x.get('calculated_rank', 9999)))

    # Alusta kuva ja skaalaa se
    original_img = Image.open(TEMPLATE_FILE).convert("RGBA")
    aspect_ratio = original_img.height / original_img.width
    target_height = int(TARGET_WIDTH * aspect_ratio)
    img = original_img.resize((TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)
    
    # Päivitä Y-koordinaatit skaalauksen suhteessa
    scale_ratio = TARGET_WIDTH / 572.0
    start_y_scaled = int(380 * scale_ratio)
    max_y_scaled = int(img.height - (100 * scale_ratio)) # Jätä tilaa logoille alhaalla

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
    current_font_size_large = 28 # Nimi
    current_font_size_med = 24   # Aika, Palkinto
    current_font_size_small = 20 # Tiimi
    
    required_height = (num_riders * ROW_HEIGHT) + (num_cats * CAT_HEADER_HEIGHT) + 40
    
    print(f"Tarvittava tila: {required_height}px, Käytettävissä: {available_height}px")
    
    scale_factor = 1.0
    if required_height > available_height:
        scale_factor = available_height / required_height
        scale_factor *= 0.98 # Pieni marginaali
        
        print(f"Skaalataan sisältöä kertoimella: {scale_factor:.2f}")
        
        current_row_height = int(ROW_HEIGHT * scale_factor)
        current_cat_height = int(CAT_HEADER_HEIGHT * scale_factor)
        current_font_size_large = int(28 * scale_factor)
        current_font_size_med = int(24 * scale_factor)
        current_font_size_small = int(20 * scale_factor)

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

    # Piirrä alaotsikko (Kirkas Punainen, Iso)
    if race_name or race_date:
        # Yhdistä nimi ja pvm
        parts = []
        if race_name: parts.append(race_name.upper())
        if race_date: parts.append(race_date)
        subtitle_text = " | ".join(parts)
        
        # Dynaaminen fontin koon säätö
        max_subtitle_width = TARGET_WIDTH - 100 # Marginaalit
        current_subtitle_size = int(36 * scale_ratio)
        font_subtitle_dynamic = ImageFont.truetype(FONT_BOLD, current_subtitle_size)
        
        while True:
            bbox = draw.textbbox((0, 0), subtitle_text, font=font_subtitle_dynamic)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_subtitle_width or current_subtitle_size <= 20:
                break
                
            current_subtitle_size -= 2
            font_subtitle_dynamic = ImageFont.truetype(FONT_BOLD, current_subtitle_size)
        
        # Keskitä
        bbox = draw.textbbox((0, 0), subtitle_text, font=font_subtitle_dynamic)
        text_width = bbox[2] - bbox[0]
        subtitle_x = (img.width - text_width) / 2
        # Sijoita otsikon alle (arvioitu sijainti skaalauksen mukaan)
        subtitle_y = start_y_scaled - 140 
        
        # Piirrä teksti mustalla reunuksella (outline)
        draw.text((subtitle_x, subtitle_y), subtitle_text, font=font_subtitle_dynamic, fill=COLOR_SUBTITLE, stroke_width=3, stroke_fill="#000000")

    # Piirrä sarakeotsikot
    y = start_y_scaled
    draw.text((COL_RANK_X, y - 40), "SIJ.", font=font_header, fill=COLOR_HEADER_TEXT)
    draw.text((COL_NAME_X, y - 40), "NIMI", font=font_header, fill=COLOR_HEADER_TEXT)
    
    # Oikealle tasatut otsikot
    # Laske "AIKA" leveys ja sijoita oikein
    bbox = draw.textbbox((0, 0), "AIKA", font=font_header)
    w = bbox[2] - bbox[0]
    draw.text((COL_TIME_X_ALIGN - w, y - 40), "AIKA", font=font_header, fill=COLOR_HEADER_TEXT)
    
    draw.text((COL_TEAM_X, y - 40), "TIIMI", font=font_header, fill=COLOR_HEADER_TEXT)
    
    # Laske "$" leveys ja sijoita oikein
    bbox = draw.textbbox((0, 0), "$", font=font_header)
    w = bbox[2] - bbox[0]
    draw.text((COL_PRIZE_X_ALIGN - w, y - 40), "$", font=font_header, fill=COLOR_HEADER_TEXT)

    current_cat = None
    row_index = 0
    
    for rider in finnish_riders:
        # Tarkista kategoria
        rider_cat = rider.get('categoryId', 'Unknown')
        if rider_cat != current_cat:
            current_cat = rider_cat
            y += int(10 * scale_factor) # Padding
            
            # Kategoriaotsikko
            draw.text((MARGIN_X + 20, y), f"KATEGORIA {current_cat}", font=font_cat, fill=COLOR_CAT_HEADER)
            
            # Viiva
            line_y = y + int(40 * scale_factor)
            draw.line([(MARGIN_X + 20, line_y), (img.width - MARGIN_X - 20, line_y)], fill=COLOR_CAT_HEADER, width=2)
            
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
        if status == "ANL":
            rank = "ANL"
            time_str = "-"
            prize_str = "" # Ei palkintoa näkyviin vaikka olisi vahingossa laskettu

        # Piirrä tekstit
        # Sijoitus
        draw.text((COL_RANK_X, y), rank, font=font_med, fill=COLOR_TEXT)
        
        # Nimi (Iso)
        draw.text((COL_NAME_X, y), name, font=font_large, fill=COLOR_TEXT)
        
        # Aika (Oikea tasaus)
        bbox = draw.textbbox((0, 0), time_str, font=font_med)
        w = bbox[2] - bbox[0]
        draw.text((COL_TIME_X_ALIGN - w, y), time_str, font=font_med, fill=COLOR_TEXT)
        
        # Tiimi (Harmaa, pieni)
        draw.text((COL_TEAM_X, y + 5), team, font=font_small, fill=COLOR_TEXT_GRAY) # Hieman alempana
        
        # Palkinto (Kulta, Oikea tasaus)
        if prize_str:
            bbox = draw.textbbox((0, 0), prize_str, font=font_med_bold)
            w = bbox[2] - bbox[0]
            draw.text((COL_PRIZE_X_ALIGN - w, y), prize_str, font=font_med_bold, fill=COLOR_PRIZE)

        y += current_row_height
        row_index += 1

    # Tallenna
    base_filename = "tulokset_kooste"
    if race_name:
        safe_name = "".join([c if c.isalnum() else "_" for c in race_name]).strip("_")
        while "__" in safe_name:
            safe_name = safe_name.replace("__", "_")
        if safe_name:
            base_filename = f"{base_filename}_{safe_name}"

    if race_date:
        safe_date = race_date.replace(".", "_").replace("/", "_").replace("-", "_")
        safe_date = "".join([c if c.isalnum() or c == "_" else "" for c in safe_date]).strip("_")
        if safe_date:
            base_filename = f"{base_filename}_{safe_date}"

    filename = os.path.join(OUTPUT_DIR, f"{base_filename}.png")
    img.convert("RGB").save(filename)
    print(f"Tallennettu: {filename}")

if __name__ == "__main__":
    create_images()
