# prepare_data.py  -  MUPI-DSS Veri Hazirlama
# Calistirma: C:\Users\Flower\AppData\Local\Programs\Python\Python311\python.exe prepare_data.py

from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np

# --- Kaynak dosyalar (Paper 1) ---
P1_ROOT  = Path(r'C:\Users\Flower\PycharmProjects\Disaster Preparedness')
BOUNDARY = P1_ROOT / 'data' / 'raw' / 'admin' / 'istanbul_mahalle_clean.gpkg'
MUPI_CSV = P1_ROOT / 'data' / 'raw' / 'mupi' / 'mahalle_mupi.csv'
VULN_CSV = P1_ROOT / 'data' / 'raw' / 'tuik' / 'mahalle_vulnerability.csv'

# --- Cikti (DSS klasoru) ---
DSS_ROOT = Path(r'C:\Users\Flower\PycharmProjects\MUPI-DSS')
OUTPUT   = DSS_ROOT / 'data' / 'mahalle_mupi.geojson'

UNIT = 'unit_id'

def main():
    # 1. Sinir dosyasini yukle
    print('Sinir dosyasi yukleniyor...')
    if not BOUNDARY.exists():
        raise FileNotFoundError(f'Bulunamadi: {BOUNDARY}')
    gdf = gpd.read_file(BOUNDARY)
    gdf = gdf.to_crs('EPSG:4326')
    print(f'  {len(gdf)} mahalle, CRS: {gdf.crs}')
    print(f'  Sutunlar: {list(gdf.columns)}')

    # 2. MUPI skorlarini yukle
    print('MUPI skorlari yukleniyor...')
    if not MUPI_CSV.exists():
        raise FileNotFoundError(f'Bulunamadi: {MUPI_CSV}')
    mupi = pd.read_csv(MUPI_CSV)
    print(f'  {len(mupi)} satir, sutunlar: {list(mupi.columns)}')

    # 3. Ilce bilgisini ekle
    if VULN_CSV.exists():
        vuln = pd.read_csv(VULN_CSV)
        if 'district' in vuln.columns:
            dist = vuln[[UNIT, 'district']].drop_duplicates(UNIT)
            mupi = mupi.merge(dist, on=UNIT, how='left')
            print(f'  Ilce bilgisi eklendi')

    # 4. Boundary ile birlestir
    print('Birlestirme yapiliyor...')
    if UNIT not in gdf.columns:
        print(f'  UYARI: Boundary dosyasinda unit_id yok!')
        print(f'  Mevcut sutunlar: {list(gdf.columns)}')
        raise KeyError(f'unit_id bulunamadi. Mevcut: {list(gdf.columns)}')

    merged = gdf[['unit_id', 'geometry']].merge(mupi, on=UNIT, how='left')
    matched = merged['MUPI'].notna().sum()
    print(f'  {matched}/{len(merged)} mahalle eslesti')

    # 5. Sutun adlarini duzelt
    rename_map = {
        'MUPI':          'MUPI',
        'hazard':        'Hazard',
        'exposure':      'Exposure',
        'social_vuln':   'Social_Vuln',
        'physical_vuln': 'Physical_Vuln',
        'access_gap':    'Access_Gap',
        'rank':          'Rank',
        'district':      'District',
    }
    for name_col in ['name', 'mahalle_adi', 'mahalle_name', 'ad', 'ADI', 'NAME']:
        if name_col in merged.columns:
            rename_map[name_col] = 'Mahalle'
            break
    merged = merged.rename(columns=rename_map)

    # Mahalle sutunu yoksa unit_id'den turet
    if 'Mahalle' not in merged.columns:
        merged['Mahalle'] = merged[UNIT].str.rsplit('_', n=1).str[0]
        print("  'Mahalle' sutunu unit_id'den turetildi")

    # 6. Skorlari yuvarla
    for col in ['MUPI', 'Hazard', 'Exposure', 'Social_Vuln', 'Physical_Vuln', 'Access_Gap']:
        if col in merged.columns:
            merged[col] = merged[col].round(3)

    # 7. NaN doldur
    if merged['MUPI'].isna().any():
        med = merged['MUPI'].median()
        merged['MUPI'] = merged['MUPI'].fillna(med)
        print(f'  NaN MUPI degerleri medyan ({med:.3f}) ile dolduruldu')

    # 8. Gereksiz sutunlari duşur
    keep = ['geometry', UNIT, 'Mahalle', 'District',
            'MUPI', 'Hazard', 'Exposure', 'Social_Vuln',
            'Physical_Vuln', 'Access_Gap', 'Rank']
    final = [c for c in keep if c in merged.columns]
    merged = merged[final]

    # 9. GeoJSON kaydet
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    gdf_out = gpd.GeoDataFrame(merged, geometry='geometry', crs='EPSG:4326')
    gdf_out.to_file(OUTPUT, driver='GeoJSON')

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f'\n[Kaydedildi] {OUTPUT}')
    print(f'  Boyut: {size_mb:.1f} MB, {len(gdf_out)} mahalle')

    print('\nTop 5 en yuksek MUPI:')
    top5 = merged.nlargest(5, 'MUPI')[['Mahalle', 'MUPI']].reset_index(drop=True)
    top5.index += 1
    print(top5.to_string())

    if size_mb > 10:
        print(f'\nNOT: Dosya {size_mb:.1f} MB - Streamlit Cloud icin buyuk olabilir.')
        print('Kucultmek icin: gdf_out.geometry = gdf_out.geometry.simplify(0.0001)')

if __name__ == '__main__':
    main()
