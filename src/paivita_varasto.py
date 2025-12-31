import argparse
import os
import sys

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tietovarasto

def main():
    parser = argparse.ArgumentParser(description='Päivitä palkintoraha-tietovarasto (CSV).')
    parser.add_argument('--file', default='palkintodata.json', help='Lähdetiedosto (oletus: palkintodata.json)')
    parser.add_argument('--date', help='Kisan pvm (ylikirjoittaa JSON-datan)')
    parser.add_argument('--name', help='Kisan nimi (ylikirjoittaa JSON-datan)')
    
    args = parser.parse_args()
    
    input_file = args.file
    
    if not os.path.exists(input_file):
        print(f"Virhe: Tiedostoa '{input_file}' ei löydy.")
        print("Aja ensin 'hae_tulokset.py' luodaksesi palkintodatan.")
        return

    print(f"Luetaan palkintodata tiedostosta: {input_file}")
    print("Päivitetään tietovarastoa...")
    
    tietovarasto.tallenna_kisa_csv(
        race_date=args.date, 
        race_name=args.name, 
        palkinto_json=input_file
    )

if __name__ == "__main__":
    main()
