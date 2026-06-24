# app.py  -  MUPI-DSS v4 (Bilingual TR/EN)
# Calistirma:
#   cd C:\Users\Flower\PycharmProjects\MUPI-DSS
#   C:\Users\Flower\AppData\Local\Programs\Python\Python311\python.exe -m streamlit run app.py

import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='MUPI-DSS | Istanbul',
    page_icon='🔴',
    layout='wide',
    initial_sidebar_state='expanded',
)

DATA_PATH = (
    Path('mahalle_mupi.geojson') if Path('mahalle_mupi.geojson').exists()
    else Path('data/mahalle_mupi.geojson')
)

SCORE_COLS = ['MUPI','Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']

COLORS = {
    'MUPI':'YlOrRd','Hazard':'OrRd','Exposure':'YlOrBr',
    'Social_Vuln':'BuPu','Physical_Vuln':'Reds','Access_Gap':'RdPu',
}

# ── Translations ──────────────────────────────────────────────────────────────
T = {
    'TR': {
        'lang_label':    'Dil / Language',
        'page_title':    'Çok Tehlikeli Kentsel Hazırlık Endeksi — Karar Destek Sistemi',
        'subtitle':      'mahalle',
        'all_districts': 'Tüm İlçeler',
        'dim_label':     'Görüntülenecek Boyut',
        'dist_label':    'İlçe Filtresi',
        'score_label':   'Skor Aralığı',
        'topn_label':    'En Yüksek N Mahalle',
        'tab_map':       '🗺️ Harita',
        'tab_compare':   '⚖️ Karşılaştır',
        'tab_analytics': '📊 Analitik',
        'tab_scenario':  '🎯 Senaryo Filtresi',
        'tab_report':    '📋 Rapor',
        'top_label':     'Top',
        'export_csv':    '⬇️ CSV İndir',
        'profile_label': 'Mahalle Profili',
        'compare_title': 'Mahalle Karşılaştırması',
        'compare_sub':   'İki mahalleyi seçin ve risk profillerini karşılaştırın.',
        'nb_a':          'Mahalle A',
        'nb_b':          'Mahalle B',
        'dim_scores':    'Boyut Skorları',
        'diff_col':      'Fark (A-B)',
        'analytics_title':'İstatistiksel Analitik',
        'analytics_sub': 'Filtrelenmiş veri setinde dağılım ve boyutlar arası korelasyonları inceleyin.',
        'corr_title':    'Boyut Korelasyon Matrisi',
        'corr_sub':      'Spearman sıra korelasyonu — Sosyal Kırılganlık ile Fiziksel Kırılganlık arasındaki negatif ilişkiye dikkat edin.',
        'scatter_title': 'Skor Dağılımı',
        'x_axis':        'X ekseni',
        'y_axis':        'Y ekseni',
        'hist_title':    'Boyutlara Göre Skor Dağılımları',
        'scenario_title':'Çok Boyutlu Senaryo Filtresi',
        'scenario_sub':  'Birden fazla boyut için eşik değerleri ayarlayarak öncelikli mahalleleri belirleyin.',
        'thresh_title':  'Eşik Değerlerini Ayarlayın',
        'scen_name':     'Senaryo adı',
        'scen_default':  'Yüksek Risk Önceliği',
        'results_match': 'mahalle eşleşiyor',
        'active_filter': 'Aktif filtreler:',
        'no_match':      'Mevcut eşiklerle eşleşen mahalle yok. Değerleri düşürmeyi deneyin.',
        'export_scen':   '⬇️ Senaryoyu CSV Olarak İndir',
        'report_title':  'Mahalle Risk Raporu',
        'report_sub':    'Paydaş brifingleri için özet rapor oluşturmak üzere bir mahalle seçin.',
        'select_nb':     'Mahalle seçin',
        'risk_report':   'MUPI Risk Raporu',
        'mupi_score':    'MUPI Skoru',
        'risk_level':    'Risk Seviyesi',
        'city_rank':     'Şehir Sırası',
        'percentile':    'Yüzdelik',
        'top_pct':       'İlk',
        'dim_scores2':   'Boyut Skorları',
        'planning_rec':  'Planlama Önerileri',
        'city_context':  'Şehir Bağlamı (MUPI Dağılımı)',
        'HIGH':          'YÜKSEK',
        'MEDIUM':        'ORTA',
        'LOW':           'DÜŞÜK',
        'rec_phys':      '🏗️ <strong>Yapısal öncelik:</strong> Yüksek 2000 öncesi ve/veya orta katlı bina oranı — sismik güçlendirme ve bina denetim programlarına öncelik verin.',
        'rec_soc':       '👥 <strong>Sosyal destek:</strong> Yüksek yaşlı/çocuk oranı veya düşük gelişmişlik — tahliye yardımı, toplum çalışması ve afet sonrası sosyal hizmetleri güçlendirin.',
        'rec_acc':       '🚑 <strong>Erişim açığı:</strong> Hastane veya itfaiyeye uzun yol ağı mesafesi — acil kaynakları önceden konumlandırmayı veya yol bağlantısını iyileştirmeyi düşünün.',
        'rec_haz':       '⚠️ <strong>Yüksek tehlike maruziyeti:</strong> Yüksek sismik PGA, sel duyarlılığı veya sıcaklık — tehlike odaklı imar ve erken uyarı sistemleri uygulayın.',
        'rec_ok':        '✅ <strong>Kritik eşiklerin altında</strong> — standart hazırlık izlemesi önerilir.',
        'dimensions': {
            'MUPI':          'Kompozit MUPI',
            'Hazard':        'Tehlike',
            'Exposure':      'Maruziyet',
            'Social_Vuln':   'Sosyal Kırılganlık',
            'Physical_Vuln': 'Fiziksel Kırılganlık',
            'Access_Gap':    'Erişim Açığı',
        },
        'dim_desc': {
            'MUPI':          'Kompozit çok tehlikeli hazırlık skoru (5 boyutun geometrik ortalaması). İBB Mw7.5 senaryosuna göre doğrulandı: ρ=0.74, AUC=0.89.',
            'Hazard':        'Deprem PGA × Vs30 amplifikasyonu (ESHM20 + Wald & Allen 2007), sel duyarlılığı (HAND/GLO-30) ve yaz LST ısısı (Landsat C2L2 2020-2024).',
            'Exposure':      'GHSL R2023A 2020 dönemi nüfus ve yapılaşmış yüzey. Toplam modellenen nüfus: 14.45M.',
            'Social_Vuln':   'Yaşlı oranı + çocuk oranı (TÜİK) + ilçe gelişmişlik endeksi ters çevrilmiş (SEGE-2022). NOT: Deprem ölümleriyle negatif korelasyon (ρ=-0.28) — toparlanma açığını ölçer, yapısal ölümü değil.',
            'Physical_Vuln': '2000 öncesi bina oranı + orta katlı (5-9 kat) bina oranı (İBB 2017 bina envanteri). Deprem ölümlerinin en güçlü öngörücüsü (ρ=+0.60, AUC=0.82).',
            'Access_Gap':    'OSMnx çok kaynaklı Dijkstra ile en yakın hastaneye (n=435) ve itfaiyeye (n=127) yol ağı mesafesi.',
        },
        'tooltip_fields': ['Mahalle','District','MUPI','Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap'],
        'tooltip_aliases': ['Mahalle:','İlçe:','MUPI:','Tehlike:','Maruziyet:','Sos.Kırılg.:','Fiz.Kırılg.:','Erişim:'],
        'footer': 'MUPI-DSS v4.0 | Nazar & Tatlı (2025), Gümüşhane Üniversitesi | ESHM20 · GHSL · TÜİK · İBB · OSM · Landsat · SEGE-2022 · Copernicus DEM',
        'validated': 'Doğrulandı: ρ=0.74 · AUC=0.89 (İBB Mw7.5, n=917)',
        'data_src': 'Veri',
        'reference': 'Referans',
    },
    'EN': {
        'lang_label':    'Dil / Language',
        'page_title':    'Multi-Hazard Urban Preparedness Index — Decision Support System',
        'subtitle':      'neighbourhoods',
        'all_districts': 'All Districts',
        'dim_label':     'Display Dimension',
        'dist_label':    'District Filter',
        'score_label':   'Score Range',
        'topn_label':    'Top N Neighbourhoods',
        'tab_map':       '🗺️ Map',
        'tab_compare':   '⚖️ Compare',
        'tab_analytics': '📊 Analytics',
        'tab_scenario':  '🎯 Scenario Filter',
        'tab_report':    '📋 Report',
        'top_label':     'Top',
        'export_csv':    '⬇️ Export CSV',
        'profile_label': 'Neighbourhood Profile',
        'compare_title': 'Neighbourhood Comparison',
        'compare_sub':   'Select two neighbourhoods to compare their risk profiles side by side.',
        'nb_a':          'Neighbourhood A',
        'nb_b':          'Neighbourhood B',
        'dim_scores':    'Dimension Scores',
        'diff_col':      'Difference (A-B)',
        'analytics_title':'Statistical Analytics',
        'analytics_sub': 'Explore distributions and inter-dimension correlations across the filtered dataset.',
        'corr_title':    'Dimension Correlation Matrix',
        'corr_sub':      'Spearman rank correlation — note the negative relationship between Social and Physical Vulnerability.',
        'scatter_title': 'Score Distribution',
        'x_axis':        'X axis',
        'y_axis':        'Y axis',
        'hist_title':    'Score Distributions by Dimension',
        'scenario_title':'Multi-Dimension Scenario Filter',
        'scenario_sub':  'Set thresholds across multiple dimensions to identify high-priority neighbourhoods.',
        'thresh_title':  'Set Thresholds',
        'scen_name':     'Scenario name',
        'scen_default':  'High Risk Priority',
        'results_match': 'neighbourhoods match',
        'active_filter': 'Active filters:',
        'no_match':      'No neighbourhoods match the current thresholds. Try lowering one or more values.',
        'export_scen':   '⬇️ Export Scenario CSV',
        'report_title':  'Neighbourhood Risk Report',
        'report_sub':    'Select a neighbourhood to generate a summary report for stakeholder briefings.',
        'select_nb':     'Select neighbourhood',
        'risk_report':   'MUPI Risk Report',
        'mupi_score':    'MUPI Score',
        'risk_level':    'Risk Level',
        'city_rank':     'City Rank',
        'percentile':    'Percentile',
        'top_pct':       'Top',
        'dim_scores2':   'Dimension Scores',
        'planning_rec':  'Planning Recommendations',
        'city_context':  'City Context (MUPI Distribution)',
        'HIGH':          'HIGH',
        'MEDIUM':        'MEDIUM',
        'LOW':           'LOW',
        'rec_phys':      '🏗️ <strong>Structural priority:</strong> High pre-2000 and/or mid-rise building fraction — prioritise seismic retrofit and building inspection programmes.',
        'rec_soc':       '👥 <strong>Social support:</strong> Elevated elderly/child share or low development index — strengthen evacuation assistance and post-disaster social services.',
        'rec_acc':       '🚑 <strong>Access deficit:</strong> Long road-network distances to hospital or fire station — consider pre-positioning emergency resources.',
        'rec_haz':       '⚠️ <strong>High hazard exposure:</strong> Elevated seismic PGA, flood susceptibility, or heat — enforce hazard-aware zoning and early-warning systems.',
        'rec_ok':        '✅ <strong>Below critical thresholds</strong> — standard preparedness monitoring recommended.',
        'dimensions': {
            'MUPI':          'Composite MUPI',
            'Hazard':        'Hazard',
            'Exposure':      'Exposure',
            'Social_Vuln':   'Social Vulnerability',
            'Physical_Vuln': 'Physical Vulnerability',
            'Access_Gap':    'Access Gap',
        },
        'dim_desc': {
            'MUPI':          'Composite multi-hazard preparedness score (geometric mean of 5 dimensions). Validated against IBB Mw7.5 scenario: rho=0.74, AUC=0.89.',
            'Hazard':        'Combined earthquake PGA x Vs30 amplification (ESHM20 + Wald & Allen 2007), flood susceptibility (HAND/GLO-30), and summer LST heat (Landsat C2L2 2020-2024).',
            'Exposure':      'Population and built-up surface from GHSL R2023A 2020 epoch. Total modelled population: 14.45M.',
            'Social_Vuln':   'Elderly share + child share (TUiK) + district development index inverted (SEGE-2022). NOTE: negatively correlated with earthquake fatalities (rho=-0.28) — captures recovery deficit, not structural mortality.',
            'Physical_Vuln': 'Pre-2000 building fraction + mid-rise (5-9 storey) fraction from IBB 2017 building inventory. Strongest predictor of earthquake fatalities (rho=+0.60, AUC=0.82).',
            'Access_Gap':    'Road-network distance to nearest hospital (n=435) and fire station (n=127) via OSMnx multi-source Dijkstra.',
        },
        'tooltip_fields': ['Mahalle','District','MUPI','Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap'],
        'tooltip_aliases': ['Neighbourhood:','District:','MUPI:','Hazard:','Exposure:','Social Vuln:','Physical Vuln:','Access Gap:'],
        'footer': 'MUPI-DSS v4.0 | Nazar & Tatli (2025), Gumusehane University | ESHM20 · GHSL · TUiK · IBB · OSM · Landsat · SEGE-2022 · Copernicus DEM',
        'validated': 'Validated: rho=0.74 · AUC=0.89 (IBB Mw7.5, n=917)',
        'data_src': 'Data',
        'reference': 'Reference',
    }
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown('''
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap");
html,body,[class*="css"]{font-family:"Inter",sans-serif;}
section[data-testid="stSidebar"]{background:#0f1923;border-right:1px solid #1e2d3d;}
section[data-testid="stSidebar"] *{color:#c8d6e5!important;}
section[data-testid="stSidebar"] hr{border-color:#1e2d3d;}
.main .block-container{padding-top:1rem;background:#f7f8fa;}
.mupi-header{background:linear-gradient(135deg,#0f1923 0%,#1a2d40 60%,#c0392b 100%);border-radius:12px;padding:1.1rem 1.6rem;margin-bottom:0.8rem;display:flex;align-items:center;justify-content:space-between;}
.mupi-header h1{color:#fff;font-size:1.3rem;font-weight:700;margin:0;letter-spacing:-0.02em;}
.mupi-header p{color:#7fa0c0;font-size:0.75rem;margin:0.15rem 0 0;}
.mupi-badge{background:rgba(192,57,43,0.2);border:1px solid #c0392b;color:#e74c3c;font-size:0.68rem;font-weight:600;padding:0.2rem 0.65rem;border-radius:20px;letter-spacing:0.05em;white-space:nowrap;}
.kpi-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:0.45rem;margin-bottom:0.8rem;}
.kpi-card{background:#fff;border-radius:10px;padding:0.55rem 0.7rem;border:1px solid #e8ecf0;box-shadow:0 1px 4px rgba(0,0,0,0.05);text-align:center;}
.kpi-card.active{border-color:#c0392b;box-shadow:0 0 0 2px rgba(192,57,43,0.15);}
.kpi-lbl{font-size:0.6rem;color:#8a9bb0;font-weight:500;text-transform:uppercase;letter-spacing:0.04em;}
.kpi-val{font-size:1.2rem;font-weight:700;color:#0f1923;font-family:"DM Mono",monospace;}
.kpi-sub{font-size:0.57rem;color:#aab;margin-top:0.1rem;}
.sec-label{font-size:0.63rem;font-weight:600;color:#8a9bb0;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.3rem;}
.rank-row{display:flex;align-items:center;padding:0.28rem 0;border-bottom:1px solid #f0f2f5;}
.rank-num{width:20px;font-size:0.68rem;color:#aaa;font-family:"DM Mono",monospace;flex-shrink:0;}
.rank-name{flex:1;font-size:0.76rem;color:#1a2d40;font-weight:500;}
.rank-score{font-size:0.76rem;font-family:"DM Mono",monospace;font-weight:600;margin-left:5px;}
.bar-bg{height:3px;background:#f0f2f5;border-radius:2px;margin-top:2px;}
.bar-fill{height:3px;border-radius:2px;}
.dim-desc{background:#f0f4f8;border-left:3px solid #c0392b;border-radius:0 6px 6px 0;padding:0.45rem 0.65rem;font-size:0.7rem;color:#445;margin-bottom:0.65rem;line-height:1.5;}
.lang-toggle{background:#1e2d3d;border-radius:8px;padding:0.3rem;display:flex;gap:0.3rem;margin-bottom:0.5rem;}
.report-card{background:#fff;border-radius:10px;border:1px solid #e8ecf0;padding:1rem 1.2rem;margin-bottom:0.6rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-thumb{background:#c0392b;border-radius:2px;}
</style>
''', unsafe_allow_html=True)

# ── Data load ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        return None
    return gpd.read_file(DATA_PATH)

gdf = load_data()
if gdf is None:
    st.error(f'Data not found: {DATA_PATH} — run prepare_data.py first.')
    st.stop()

avail_scores = [c for c in SCORE_COLS if c in gdf.columns]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('''
    <div style="padding:0.8rem 0 0.4rem;text-align:center;">
        <div style="font-size:1.8rem;margin-bottom:0.2rem;">🔴</div>
        <div style="font-size:0.95rem;font-weight:700;color:#fff;">MUPI-DSS</div>
        <div style="font-size:0.65rem;color:#4a6b8a;margin-top:0.1rem;">
            Multi-Hazard Urban Preparedness<br>Decision Support System
        </div>
    </div><hr style="border-color:#1e2d3d;margin:0.6rem 0;">
    ''', unsafe_allow_html=True)

    # Language toggle
    lang = st.radio('🌐 Dil / Language', ['Türkçe 🇹🇷', 'English 🇬🇧'],
                    horizontal=True, label_visibility='collapsed')
    L = T['TR'] if 'Türkçe' in lang else T['EN']

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)

    # Dimension selector
    st.markdown(f'<div class="sec-label" style="color:#4a6b8a!important;">{L["dim_label"]}</div>',
                unsafe_allow_html=True)
    dim_options = list(L['dimensions'].values())
    dim_keys    = list(L['dimensions'].keys())
    sel_label   = st.selectbox('Dim', dim_options, label_visibility='collapsed')
    sel_col     = dim_keys[dim_options.index(sel_label)]
    cmap        = COLORS.get(sel_col, 'YlOrRd')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-label" style="color:#4a6b8a!important;">{L["dist_label"]}</div>',
                unsafe_allow_html=True)
    has_dist = 'District' in gdf.columns and gdf['District'].notna().any()
    if has_dist:
        dists    = [L['all_districts']] + sorted(gdf['District'].dropna().unique().tolist())
        sel_dist = st.selectbox('District', dists, label_visibility='collapsed')
    else:
        sel_dist = L['all_districts']

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-label" style="color:#4a6b8a!important;">{L["score_label"]}</div>',
                unsafe_allow_html=True)
    srange = st.slider('Score', 0.0, 1.0, (0.0, 1.0), 0.05, label_visibility='collapsed')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-label" style="color:#4a6b8a!important;">{L["topn_label"]}</div>',
                unsafe_allow_html=True)
    top_n = st.slider('Top N', 5, 50, 15, label_visibility='collapsed')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown(f'''
    <div style="font-size:0.62rem;color:#3a5570;line-height:1.7;">
        <strong style="color:#5a8ab0;">{L["validated"]}</strong><br><br>
        <strong style="color:#5a8ab0;">{L["data_src"]}</strong><br>
        ESHM20 · GHSL R2023A<br>
        TUiK · IBB 2017 · OSM<br>
        Landsat C2L2 · SEGE-2022<br>
        Copernicus DEM<br><br>
        <strong style="color:#5a8ab0;">{L["reference"]}</strong><br>
        Nazar & Tatli (2025)<br>
        Gumusehane University
    </div>
    ''', unsafe_allow_html=True)

# ── Filter ────────────────────────────────────────────────────────────────────
filt = gdf.copy()
if sel_dist != L['all_districts'] and has_dist:
    filt = filt[filt['District'] == sel_dist]
if sel_col in filt.columns:
    filt = filt[filt[sel_col].fillna(0).between(srange[0], srange[1])]
filt = filt.dropna(subset=[sel_col])

# ── Header ────────────────────────────────────────────────────────────────────
dist_show = sel_dist if sel_dist != L['all_districts'] else ('Istanbul' if 'EN' in lang else 'İstanbul')
st.markdown(f'''
<div class="mupi-header">
    <div>
        <h1>MUPI-DSS — {L["page_title"]}</h1>
        <p>{dist_show} &nbsp;·&nbsp; {len(filt)} {L["subtitle"]} &nbsp;·&nbsp; {srange[0]:.2f}–{srange[1]:.2f}</p>
    </div>
    <span class="mupi-badge">{L["validated"]}</span>
</div>
''', unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
kpi_html = '<div class="kpi-grid">'
for col, lbl in L['dimensions'].items():
    if col in filt.columns:
        val  = filt[col].mean()
        hi   = filt[col].max()
        actv = 'active' if col == sel_col else ''
        kpi_html += f'''<div class="kpi-card {actv}">
            <div class="kpi-lbl">{lbl[:14]}</div>
            <div class="kpi-val">{val:.3f}</div>
            <div class="kpi-sub">max {hi:.3f}</div></div>'''
kpi_html += '</div>'
st.markdown(kpi_html, unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_map, tab_cmp, tab_an, tab_sc, tab_rep = st.tabs([
    L['tab_map'], L['tab_compare'], L['tab_analytics'],
    L['tab_scenario'], L['tab_report']
])

# helper: rank list html
def rank_html(df, col, top):
    html = ''
    top_df = df.sort_values(col, ascending=False).head(top).reset_index(drop=True)
    for i, row in top_df.iterrows():
        name  = str(row.get('Mahalle', row.get('unit_id', ''))).replace(' Mahallesi', '')[:20]
        score = float(row[col])
        color = '#c0392b' if score>=0.66 else '#e67e22' if score>=0.33 else '#27ae60'
        html += f'''<div class="rank-row">
            <div class="rank-num">{i+1}</div>
            <div style="flex:1">
                <div class="rank-name">{name}</div>
                <div class="bar-bg"><div class="bar-fill" style="width:{int(score*100)}%;background:{color};"></div></div>
            </div>
            <div class="rank-score" style="color:{color};">{score:.3f}</div></div>'''
    return html, top_df

# ════════════════════════════════════════════════
# TAB 1: MAP
# ════════════════════════════════════════════════
with tab_map:
    desc = L['dim_desc'].get(sel_col, '')
    if desc:
        st.markdown(f'<div class="dim-desc"><strong>{sel_label}:</strong> {desc}</div>',
                    unsafe_allow_html=True)

    col_map, col_panel = st.columns([3, 1])

    with col_map:
        m = folium.Map(location=[41.01, 28.95], zoom_start=10,
                       tiles='CartoDB positron', prefer_canvas=True)
        if len(filt) > 0 and sel_col in filt.columns:
            gj = json.loads(filt.to_json())
            folium.Choropleth(
                geo_data=gj, data=filt,
                columns=['unit_id', sel_col],
                key_on='feature.properties.unit_id',
                fill_color=cmap, fill_opacity=0.78,
                line_opacity=0.2, line_weight=0.3,
                legend_name=f'{sel_label} (0-1)',
                nan_fill_color='#e8ecf0', highlight=True,
            ).add_to(m)
            folium.GeoJson(
                gj,
                style_function=lambda x: {'fillOpacity':0,'weight':0},
                highlight_function=lambda x: {'weight':2.5,'color':'#c0392b','fillOpacity':0.1},
                tooltip=folium.GeoJsonTooltip(
                    fields=L['tooltip_fields'],
                    aliases=L['tooltip_aliases'],
                    sticky=True,
                    style='background:rgba(15,25,35,0.93);color:#c8d6e5;font-size:12px;border:1px solid #1e2d3d;border-radius:6px;padding:6px 10px;',
                ),
            ).add_to(m)
            top10 = filt.nlargest(10, 'MUPI')
            for idx, row in top10.iterrows():
                try:
                    cx = row.geometry.centroid.x
                    cy = row.geometry.centroid.y
                    name = str(row.get('Mahalle','')).replace(' Mahallesi','')[:16]
                    score = float(row.get('MUPI',0))
                    rank  = list(top10.index).index(idx)+1
                    folium.CircleMarker(
                        location=[cy,cx], radius=6,
                        color='#c0392b', fill=True, fill_color='#e74c3c',
                        fill_opacity=0.9, weight=1.5,
                        tooltip=f'#{rank} {name} — MUPI {score:.3f}',
                    ).add_to(m)
                except Exception:
                    pass
        folium.LayerControl(collapsed=True).add_to(m)
        st_folium(m, width=None, height=540, returned_objects=[])

    with col_panel:
        st.markdown(f'<div class="sec-label">{L["top_label"]} {top_n} — {sel_label}</div>',
                    unsafe_allow_html=True)
        if sel_col in filt.columns:
            rhtml, top_df = rank_html(filt, sel_col, top_n)
            st.markdown(rhtml, unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)
            csv = top_df[['Mahalle', sel_col] + (['District'] if has_dist else [])].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(L['export_csv'], csv,
                               file_name=f'MUPI_{sel_col}_top{top_n}.csv',
                               mime='text/csv', use_container_width=True)

        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(f'<div class="sec-label">{L["profile_label"]}</div>', unsafe_allow_html=True)
        rdims  = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
        rlabls = [L['dimensions'].get(d,d) for d in rdims]
        if len(filt) > 0 and 'MUPI' in filt.columns:
            top1  = filt.sort_values('MUPI', ascending=False).iloc[0]
            avail = [d for d in rdims if d in filt.columns]
            albls = [L['dimensions'].get(d,d) for d in avail]
            if avail:
                vals = [round(float(top1.get(d,0)),3) for d in avail]
                fig  = go.Figure(go.Scatterpolar(
                    r=vals+[vals[0]], theta=albls+[albls[0]],
                    fill='toself', fillcolor='rgba(192,57,43,0.15)',
                    line=dict(color='#c0392b',width=2),
                ))
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    polar=dict(
                        bgcolor='rgba(0,0,0,0)',
                        radialaxis=dict(visible=True,range=[0,1],tickfont=dict(size=8,color='#8a9bb0'),gridcolor='#e8ecf0'),
                        angularaxis=dict(tickfont=dict(size=9,color='#445'),gridcolor='#e8ecf0'),
                    ),
                    showlegend=False, margin=dict(l=20,r=20,t=35,b=10), height=220,
                    title=dict(text=str(top1.get('Mahalle','')).replace(' Mahallesi','')[:20],
                               font=dict(size=10,color='#1a2d40'),x=0.5),
                )
                st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════
# TAB 2: COMPARE
# ════════════════════════════════════════════════
with tab_cmp:
    st.markdown(f'#### {L["compare_title"]}')
    st.caption(L['compare_sub'])
    all_names = sorted(gdf['Mahalle'].dropna().unique().tolist()) if 'Mahalle' in gdf.columns else []
    c1, c2 = st.columns(2)
    with c1:
        n1 = st.selectbox(L['nb_a'], all_names, index=0, key='cmp_n1')
    with c2:
        n2 = st.selectbox(L['nb_b'], all_names, index=min(1,len(all_names)-1), key='cmp_n2')

    rdims = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
    albls = [L['dimensions'].get(d,d) for d in rdims]
    avail = [d for d in rdims if d in gdf.columns]
    av_lb = [L['dimensions'].get(d,d) for d in avail]

    row1 = gdf[gdf['Mahalle']==n1].iloc[0] if len(gdf[gdf['Mahalle']==n1])>0 else None
    row2 = gdf[gdf['Mahalle']==n2].iloc[0] if len(gdf[gdf['Mahalle']==n2])>0 else None

    if row1 is not None and row2 is not None and avail:
        vals1 = [round(float(row1.get(d,0)),3) for d in avail]
        vals2 = [round(float(row2.get(d,0)),3) for d in avail]
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatterpolar(
            r=vals1+[vals1[0]], theta=av_lb+[av_lb[0]],
            fill='toself', name=n1.replace(' Mahallesi',''),
            fillcolor='rgba(192,57,43,0.15)', line=dict(color='#c0392b',width=2),
        ))
        fig_cmp.add_trace(go.Scatterpolar(
            r=vals2+[vals2[0]], theta=av_lb+[av_lb[0]],
            fill='toself', name=n2.replace(' Mahallesi',''),
            fillcolor='rgba(41,128,185,0.15)', line=dict(color='#2980b9',width=2),
        ))
        fig_cmp.update_layout(
            polar=dict(radialaxis=dict(visible=True,range=[0,1])),
            legend=dict(orientation='h',yanchor='bottom',y=-0.15),
            margin=dict(l=40,r=40,t=40,b=60), height=400,
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_cmp, use_container_width=True)
        rows = []
        for d, lbl in zip(avail, av_lb):
            v1 = float(row1.get(d,0)); v2 = float(row2.get(d,0))
            rows.append({L['dim_scores']: lbl,
                         n1.replace(' Mahallesi','')[:18]: f'{v1:.3f}',
                         n2.replace(' Mahallesi','')[:18]: f'{v2:.3f}',
                         L['diff_col']: f'{v1-v2:+.3f}'})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        m1 = float(row1.get('MUPI',0)); m2 = float(row2.get('MUPI',0))
        mc1,mc2,mc3 = st.columns(3)
        mc1.metric(n1.replace(' Mahallesi','')[:18], f'{m1:.3f}', 'MUPI')
        mc2.metric(n2.replace(' Mahallesi','')[:18], f'{m2:.3f}', 'MUPI')
        mc3.metric('Δ', f'{abs(m1-m2):.3f}', 'A>B' if m1>m2 else 'B>A')
        csv2 = pd.DataFrame(rows).to_csv(index=False).encode('utf-8-sig')
        st.download_button(L['export_csv'], csv2, file_name='MUPI_comparison.csv', mime='text/csv')

# ════════════════════════════════════════════════
# TAB 3: ANALYTICS
# ════════════════════════════════════════════════
with tab_an:
    st.markdown(f'#### {L["analytics_title"]}')
    st.caption(L['analytics_sub'])
    if len(avail_scores) >= 2:
        acol1, acol2 = st.columns(2)
        with acol1:
            st.markdown(f'##### {L["corr_title"]}')
            st.caption(L['corr_sub'])
            corr_df = filt[avail_scores].corr(method='spearman').round(2)
            corr_labels = [L['dimensions'].get(c,c) for c in avail_scores]
            fig_corr = go.Figure(go.Heatmap(
                z=corr_df.values.tolist(), x=corr_labels, y=corr_labels,
                colorscale='RdBu_r', zmin=-1, zmax=1,
                text=[[f'{v:.2f}' for v in row] for row in corr_df.values.tolist()],
                texttemplate='%{text}', textfont=dict(size=11),
                colorbar=dict(title='ρ', len=0.8),
            ))
            fig_corr.update_layout(height=380, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_corr, use_container_width=True)
        with acol2:
            st.markdown(f'##### {L["scatter_title"]}')
            x_ax = st.selectbox(L['x_axis'], list(L['dimensions'].values()), index=0, key='an_x')
            y_ax = st.selectbox(L['y_axis'], list(L['dimensions'].values()), index=4, key='an_y')
            x_col = list(L['dimensions'].keys())[list(L['dimensions'].values()).index(x_ax)]
            y_col = list(L['dimensions'].keys())[list(L['dimensions'].values()).index(y_ax)]
            if x_col in filt.columns and y_col in filt.columns:
                plot_df = filt[['Mahalle',x_col,y_col,'MUPI']].dropna()
                x_vals = plot_df[x_col].tolist()
                y_vals = plot_df[y_col].tolist()
                c_vals = plot_df['MUPI'].tolist()
                names  = plot_df['Mahalle'].tolist()
                fig_sc = go.Figure(go.Scatter(
                    x=x_vals, y=y_vals, mode='markers',
                    marker=dict(color=c_vals, colorscale='YlOrRd', size=5,
                                opacity=0.7, colorbar=dict(title='MUPI')),
                    text=names, hovertemplate='%{text}<br>'+x_ax+': %{x:.3f}<br>'+y_ax+': %{y:.3f}<extra></extra>',
                ))
                fig_sc.update_layout(
                    height=380, margin=dict(l=10,r=10,t=10,b=10),
                    xaxis_title=x_ax, yaxis_title=y_ax,
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_sc, use_container_width=True)

        st.markdown(f'##### {L["hist_title"]}')
        hcols = st.columns(3)
        for i, col in enumerate(avail_scores[:6]):
            with hcols[i%3]:
                h_vals = filt[col].dropna().tolist()
                lbl    = L['dimensions'].get(col,col)
                fig_h  = go.Figure(go.Histogram(x=h_vals, nbinsx=30,
                                                 marker_color='#c0392b', opacity=0.85))
                fig_h.update_layout(height=200, margin=dict(l=5,r=5,t=25,b=5),
                                    title=dict(text=lbl,font=dict(size=11)),
                                    showlegend=False, bargap=0.05,
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    xaxis_title='Score', yaxis_title='N')
                st.plotly_chart(fig_h, use_container_width=True)

# ════════════════════════════════════════════════
# TAB 4: SCENARIO FILTER
# ════════════════════════════════════════════════
with tab_sc:
    st.markdown(f'#### {L["scenario_title"]}')
    st.caption(L['scenario_sub'])
    scol1, scol2 = st.columns([1,2])
    with scol1:
        st.markdown(f'##### {L["thresh_title"]}')
        thresholds = {}
        for col, lbl in L['dimensions'].items():
            if col in gdf.columns and col != 'MUPI':
                t = st.slider(f'{lbl} ≥', 0.0, 1.0, 0.0, 0.05, key=f'thr_{col}')
                thresholds[col] = t
        st.markdown('---')
        scenario_name = st.text_input(L['scen_name'], value=L['scen_default'])
    scen = gdf.copy()
    for col, t in thresholds.items():
        if t > 0:
            scen = scen[scen[col].fillna(0) >= t]
    with scol2:
        st.markdown(f'##### **{len(scen)}** {L["results_match"]}')
        chips = ' '.join([
            f'<span style="display:inline-block;background:#fff3f3;border:1px solid #f0a0a0;color:#c0392b;font-size:0.68rem;padding:0.15rem 0.5rem;border-radius:12px;margin:0.1rem;">{L["dimensions"].get(c,c)} ≥ {t:.2f}</span>'
            for c,t in thresholds.items() if t>0
        ])
        if chips:
            st.markdown(f'{L["active_filter"]} {chips}', unsafe_allow_html=True)
        st.markdown('')
        if len(scen) > 0 and 'MUPI' in scen.columns:
            disp_cols = ['Mahalle','District','MUPI']+[c for c in ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap'] if c in scen.columns]
            if not has_dist:
                disp_cols = [c for c in disp_cols if c != 'District']
            scen_disp = scen[disp_cols].dropna(subset=['MUPI']).sort_values('MUPI',ascending=False).reset_index(drop=True)
            scen_disp.index += 1
            scen_disp.columns = [L['dimensions'].get(c,c) if c in L['dimensions'] else c for c in scen_disp.columns]
            st.dataframe(scen_disp, use_container_width=True, height=350)
            csv_s = scen_disp.to_csv(index=True).encode('utf-8-sig')
            st.download_button(
                f'{L["export_scen"]} ({len(scen)})',
                csv_s, file_name=f'MUPI_{scenario_name.replace(" ","_")}.csv', mime='text/csv'
            )
        elif len(scen) == 0:
            st.info(L['no_match'])

# ════════════════════════════════════════════════
# TAB 5: REPORT
# ════════════════════════════════════════════════
with tab_rep:
    st.markdown(f'#### {L["report_title"]}')
    st.caption(L['report_sub'])
    all_names_r = sorted(gdf['Mahalle'].dropna().unique().tolist()) if 'Mahalle' in gdf.columns else []
    rep_name    = st.selectbox(L['select_nb'], all_names_r, key='rep_name')
    rep_row     = gdf[gdf['Mahalle']==rep_name]
    if len(rep_row) > 0:
        r = rep_row.iloc[0]
        rdims = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
        avail_r = [d for d in rdims if d in gdf.columns]
        albl_r  = [L['dimensions'].get(d,d) for d in avail_r]
        if 'MUPI' in gdf.columns:
            rank_val = int(gdf['MUPI'].rank(ascending=False).loc[rep_row.index[0]])
            total_n  = len(gdf)
            pct_rank = round((1-rank_val/total_n)*100,1)
        else:
            rank_val,total_n,pct_rank = 'N/A',len(gdf),0
        rc1,rc2 = st.columns([2,1])
        with rc1:
            mupi_val = float(r.get('MUPI',0))
            risk_lvl = L['HIGH'] if mupi_val>=0.66 else L['MEDIUM'] if mupi_val>=0.33 else L['LOW']
            risk_col = '#c0392b' if mupi_val>=0.66 else '#e67e22' if mupi_val>=0.33 else '#27ae60'
            dist_str = str(r.get('District','')) if has_dist else ''
            st.markdown(f'''
            <div class="report-card">
                <div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;font-weight:600;">{L["risk_report"]}</div>
                <h2 style="margin:0;color:#0f1923;">{rep_name.replace(" Mahallesi","")}</h2>
                <p style="color:#667;font-size:0.8rem;margin:0.2rem 0 0.6rem;">{dist_str} &nbsp;·&nbsp; Istanbul</p>
                <div style="display:flex;gap:1.2rem;margin-top:0.5rem;">
                    <div><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">{L["mupi_score"]}</div>
                         <div style="font-size:2rem;font-weight:700;color:{risk_col};font-family:DM Mono,monospace;">{mupi_val:.3f}</div></div>
                    <div><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">{L["risk_level"]}</div>
                         <div style="font-size:1.4rem;font-weight:700;color:{risk_col};">{risk_lvl}</div></div>
                    <div><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">{L["city_rank"]}</div>
                         <div style="font-size:1.4rem;font-weight:700;color:#1a2d40;">#{rank_val}/{total_n}</div></div>
                    <div><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">{L["percentile"]}</div>
                         <div style="font-size:1.4rem;font-weight:700;color:#1a2d40;">{L["top_pct"]} {100-pct_rank:.0f}%</div></div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            st.markdown('<div class="report-card"><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;font-weight:600;margin-bottom:0.4rem;">'+L['dim_scores2']+'</div>', unsafe_allow_html=True)
            for d,lbl in zip(avail_r,albl_r):
                v    = float(r.get(d,0))
                col_ = '#c0392b' if v>=0.66 else '#e67e22' if v>=0.33 else '#27ae60'
                st.markdown(f'''
                <div style="margin:0.4rem 0;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                        <span style="font-size:0.76rem;color:#445;font-weight:500;">{lbl}</span>
                        <span style="font-size:0.76rem;font-family:DM Mono,monospace;color:{col_};font-weight:600;">{v:.3f}</span>
                    </div>
                    <div style="background:#f0f2f5;border-radius:3px;height:5px;">
                        <div style="width:{int(v*100)}%;background:{col_};height:5px;border-radius:3px;"></div>
                    </div>
                </div>''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            recs = []
            phys=float(r.get('Physical_Vuln',0)); soc=float(r.get('Social_Vuln',0))
            acc=float(r.get('Access_Gap',0)); haz=float(r.get('Hazard',0))
            if phys>=0.66: recs.append(L['rec_phys'])
            if soc>=0.5:   recs.append(L['rec_soc'])
            if acc>=0.6:   recs.append(L['rec_acc'])
            if haz>=0.7:   recs.append(L['rec_haz'])
            if not recs:   recs.append(L['rec_ok'])
            st.markdown('<div class="report-card"><div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;font-weight:600;margin-bottom:0.4rem;">'+L['planning_rec']+'</div>', unsafe_allow_html=True)
            for rec in recs:
                st.markdown(f'<p style="font-size:0.75rem;color:#333;margin:0.4rem 0;">{rec}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with rc2:
            if avail_r:
                vals_r = [round(float(r.get(d,0)),3) for d in avail_r]
                fig_r  = go.Figure(go.Scatterpolar(
                    r=vals_r+[vals_r[0]], theta=albl_r+[albl_r[0]],
                    fill='toself', fillcolor='rgba(192,57,43,0.18)',
                    line=dict(color='#c0392b',width=2),
                ))
                fig_r.update_layout(
                    polar=dict(radialaxis=dict(visible=True,range=[0,1],tickfont=dict(size=8)),
                               angularaxis=dict(tickfont=dict(size=9))),
                    showlegend=False, margin=dict(l=25,r=25,t=40,b=10), height=280,
                    paper_bgcolor='rgba(0,0,0,0)',
                    title=dict(text='Risk Profile' if 'EN' in lang else 'Risk Profili',
                               font=dict(size=11,color='#445'),x=0.5),
                )
                st.plotly_chart(fig_r, use_container_width=True)
            if 'MUPI' in gdf.columns:
                st.markdown(f'<div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;font-weight:600;margin:0.5rem 0 0.3rem;">{L["city_context"]}</div>', unsafe_allow_html=True)
                mupi_list = gdf['MUPI'].dropna().tolist()
                fig_ctx   = go.Figure(go.Histogram(x=mupi_list, nbinsx=40,
                                                    marker_color='#c8d6e5', opacity=0.9))
                fig_ctx.add_vline(x=float(r.get('MUPI',0)), line_color='#c0392b', line_width=2,
                                  annotation_text=rep_name.replace(' Mahallesi','')[:12],
                                  annotation_font_size=9, annotation_font_color='#c0392b')
                fig_ctx.update_layout(height=200, margin=dict(l=5,r=5,t=5,b=5),
                                      xaxis_title='MUPI', yaxis_title='N',
                                      showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_ctx, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<hr style="margin-top:0.8rem;">', unsafe_allow_html=True)
st.markdown(f'''
<div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:0.62rem;color:#aab;">{L["footer"]}</span>
    <span style="font-size:0.62rem;color:#c0392b;font-weight:600;">{L["validated"]}</span>
</div>
''', unsafe_allow_html=True)
