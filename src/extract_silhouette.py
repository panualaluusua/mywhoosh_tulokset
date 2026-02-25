import cv2
import numpy as np
import sys
import os

def extract_silhouette(image_path, output_path):
    print(f"Ladataan kuva: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        print(f"VIRHE: Kuvaa ei voitu ladata: {image_path}")
        return False
        
    h, w = img.shape[:2]
    print(f"Kuvan mitat: {w}x{h}")
    
    # 1. Rajaus (Crop)
    # Poistetaan ylin kolmannes (otsikot) ja aivan alin osa (x-akseli)
    # 750x422 kuvassa: ylhäältä ~150px pois, alhaalta ~40px pois
    start_y = int(h * 0.35)
    end_y = int(h * 0.92)
    start_x = int(w * 0.05)
    end_x = int(w * 0.95)
    
    cropped = img[start_y:end_y, start_x:end_x]
    
    # 2. Parempaan erotteluun: tunnistetaan etäisyys puhtaasta valkoisesta
    # Rataprofiililla ja teksteillä on korkea kontrasti valkoiseen nähden.
    # KOM-segmenttien laatikot ovat erittäin haaleita pastellivärejä (RGB lähellä 230-250), 
    # joten voimme suodattaa ne pois laskemalla pikselin euklidisen etäisyyden valkoisesta.
    diff = 255 - cropped.astype(np.float32)
    dist = np.linalg.norm(diff, axis=2)
    
    # Kynnysarvo 80 jättää pois kevyet taustavärit, mutta poimii radan kovat värit.
    fg_mask = (dist > 80).astype(np.uint8) * 255
    
    # 3. Poistetaan ohuet pystyviivat (tekstit, sprinttiviivat, yms asiat jotka koskevat rataa)
    # Käytetään ensin leveää vaakasuuntaista avausta
    kernel_h = np.ones((1, 15), np.uint8)
    opened_h = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_h)
    
    # Suljetaan pienet raot
    kernel_sq = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(opened_h, cv2.MORPH_CLOSE, kernel_sq, iterations=2)
    
    # Avataan vielä varmuuden vuoksi pienet satunnaiset roskat pois
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_sq, iterations=1)
    
    # 4. Etsitään suuri yhtenäinen komponentti (itse mäkiprofiili)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(opened, connectivity=8)
    
    if num_labels <= 1:
        print("VIRHE: Profiilia ei löydetty.")
        return False
        
    # Etsitään suurin komponentti (poislukien tausta 0)
    largest_label = 1
    max_area = stats[1, cv2.CC_STAT_AREA]
    for i in range(2, num_labels):
        if stats[i, cv2.CC_STAT_AREA] > max_area:
            largest_label = i
            max_area = stats[i, cv2.CC_STAT_AREA]
            
    # Luodaan maski vain suurimmasta komponentista
    profile_mask = np.zeros_like(opened)
    profile_mask[labels == largest_label] = 255
    
    # Täytetään mahdolliset profiilin "alle" jäävät reiät, jotta se on yhtenäinen.
    # Muutetaan kaikki profiilin alimman pisteen alapuolella olevat pikselit valkoisiksi (255) sarakkeittain
    h_c, w_c = profile_mask.shape
    filled_mask = np.zeros_like(profile_mask)
    for x in range(w_c):
        col = profile_mask[:, x]
        indices = np.where(col == 255)[0]
        if len(indices) > 0:
            top_y = indices[0]
            # Täytetään huipusta pohjaan
            filled_mask[top_y:h_c, x] = 255
            
    # 5. Etsitään profiilin yläreuna viivan piirtämistä varten
    h_c, w_c = profile_mask.shape
    pts = []
    
    # Etsitään jokaisen sarakkeen ylin pikseli
    for x in range(w_c):
        col = profile_mask[:, x]
        indices = np.where(col == 255)[0]
        if len(indices) > 0:
            top_y = indices[0]
            pts.append([x, top_y])
            
    if not pts:
        print("VIRHE: Profiilin yläreunaa ei pystytty määrittämään.")
        return False
        
    pts = np.array([pts], dtype=np.int32)
    
    # Luodaan täyttöpolynesium viivan piirtämistä varten (ei enää lisätä alareunan kulmia)
    
    # 6. Luodaan tyylitelty output "Grand Tour" -estetiikalla: pelkkä kirkas viiva
    out_cropped = np.zeros((h_c, w_c, 4), dtype=np.uint8)
    
    # Reunaviivan väri: Tour de France keltainen / intensiivinen huomioväri
    # BGR muodossa esim kirkas keltainen: (0, 215, 255, 255) tai Giro-pinkki: (147, 20, 255, 255)
    # Valitaan tyylikäs kultainen/keltainen
    line_color = (0, 204, 255, 255) 
    cv2.polylines(out_cropped, pts, isClosed=False, color=line_color, thickness=4, lineType=cv2.LINE_AA)
    
    cv2.imwrite(output_path, out_cropped)
    print(f"Grand Tour -tyylinen silhuetti tallennettu onnistuneesti: {output_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Käyttö (yksittäinen tiedosto): python extract_silhouette.py <input.jpg> <output.png>")
        print("Käyttö (koko kansio): python extract_silhouette.py <kansion_polku>")
        sys.exit(1)
        
    arg = sys.argv[1]
    
    if os.path.isdir(arg):
        print(f"Käydään läpi kansio: {arg}")
        for file in os.listdir(arg):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')) and not file.endswith('_silhuetti.png'):
                inp_path = os.path.join(arg, file)
                base_name = os.path.splitext(file)[0]
                out_path = os.path.join(arg, f"{base_name}_silhuetti.png")
                extract_silhouette(inp_path, out_path)
    else:
        if len(sys.argv) >= 3:
            extract_silhouette(arg, sys.argv[2])
        else:
            base_name = os.path.splitext(arg)[0]
            extract_silhouette(arg, f"{base_name}_silhuetti.png")
