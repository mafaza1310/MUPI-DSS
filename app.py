# app.py  -  MUPI-DSS v3 (Full Featured)
# Calistirma:
#   cd C:\Users\Flower\PycharmProjects\MUPI-DSS
#   C:\Users\Flower\AppData\Local\Programs\Python\Python311\python.exe -m streamlit run app.py
#
# Yeni ozellikler v3:
#   - Sekmeli arayuz (Map / Compare / Analytics / Report)
#   - Mahalle karsilastirma modu (2 mahalle radar ust uste)
#   - Istatistik paneli (korelasyon matrisi + dagilim grafigi)
#   - Senaryo filtresi (coklu boyut esigi)
#   - PDF benzeri rapor sekmesi (ekran goruntusu icin)

import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import folium
from streamlit_folium import st_folium

# ── Sayfa ayarlari ────────────────────────────────────────────────────────────
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

DIMENSIONS = {
    'Composite MUPI':        'MUPI',
    'Hazard':                'Hazard',
    'Exposure':              'Exposure',
    'Social Vulnerability':  'Social_Vuln',
    'Physical Vulnerability':'Physical_Vuln',
    'Access Gap':            'Access_Gap',
}

SCORE_COLS = ['MUPI','Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']

DIM_DESC = {
    'MUPI':          'Composite multi-hazard preparedness score (geometric mean of 5 dimensions). Validated against IBB Mw7.5 scenario: rho=0.74, AUC=0.89.',
    'Hazard':        'Combined earthquake PGA x Vs30 amplification (ESHM20 + Wald & Allen 2007), flood susceptibility (HAND/GLO-30), and summer LST heat (Landsat C2L2 2020-2024).',
    'Exposure':      'Population and built-up surface from GHSL R2023A 2020 epoch. Total modelled population: 14.45M.',
    'Social_Vuln':   'Elderly share + child share (TUiK) + district development index inverted (SEGE-2022). Note: negatively correlated with earthquake fatalities (rho=-0.28) — captures recovery deficit, not structural mortality.',
    'Physical_Vuln': 'Pre-2000 building fraction + mid-rise (5-9 storey) fraction from IBB 2017 building inventory. Strongest predictor of earthquake fatalities (rho=+0.60, AUC=0.82).',
    'Access_Gap':    'Road-network distance to nearest hospital (n=435) and fire station (n=127) via OSMnx multi-source Dijkstra on OSM drivable graph.',
}

COLORS = {
    'MUPI':'YlOrRd','Hazard':'OrRd','Exposure':'YlOrBr',
    'Social_Vuln':'BuPu','Physical_Vuln':'Reds','Access_Gap':'RdPu',
}

DIM_LABELS = {
    'MUPI':'MUPI','Hazard':'Hazard','Exposure':'Exposure',
    'Social_Vuln':'Social Vuln','Physical_Vuln':'Physical Vuln','Access_Gap':'Access Gap',
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
.mupi-header h1{color:#fff;font-size:1.35rem;font-weight:700;margin:0;letter-spacing:-0.02em;}
.mupi-header p{color:#7fa0c0;font-size:0.75rem;margin:0.15rem 0 0;}
.mupi-badge{background:rgba(192,57,43,0.2);border:1px solid #c0392b;color:#e74c3c;font-size:0.68rem;font-weight:600;padding:0.2rem 0.65rem;border-radius:20px;letter-spacing:0.05em;}
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
.report-card{background:#fff;border-radius:10px;border:1px solid #e8ecf0;padding:1rem 1.2rem;margin-bottom:0.6rem;box-shadow:0 1px 4px rgba(0,0,0,0.04);}
.report-title{font-size:0.65rem;color:#8a9bb0;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;}
.scenario-chip{display:inline-block;background:#fff3f3;border:1px solid #f0a0a0;color:#c0392b;font-size:0.68rem;padding:0.15rem 0.5rem;border-radius:12px;margin:0.1rem;}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-thumb{background:#c0392b;border-radius:2px;}
</style>
''', unsafe_allow_html=True)

# ── Veri yukleme ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        return None
    return gpd.read_file(DATA_PATH)

gdf = load_data()
if gdf is None:
    st.error(f'Veri bulunamadi: {DATA_PATH} — once prepare_data.py calistirin.')
    st.stop()

# score cols that exist
avail_scores = [c for c in SCORE_COLS if c in gdf.columns]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('''
    <div style="padding:0.8rem 0 0.4rem;text-align:center;">
        <div style="font-size:1.8rem;margin-bottom:0.2rem;">🔴</div>
        <div style="font-size:0.95rem;font-weight:700;color:#fff;">MUPI-DSS</div>
        <div style="font-size:0.65rem;color:#4a6b8a;margin-top:0.1rem;">Multi-Hazard Urban Preparedness<br>Decision Support System</div>
    </div>
    <hr style="border-color:#1e2d3d;margin:0.6rem 0;">
    ''', unsafe_allow_html=True)

    st.markdown('<div class="sec-label" style="color:#4a6b8a!important;">Display Dimension</div>', unsafe_allow_html=True)
    sel_label = st.selectbox('Dimension', list(DIMENSIONS.keys()), label_visibility='collapsed')
    sel_col   = DIMENSIONS[sel_label]
    cmap      = COLORS.get(sel_col, 'YlOrRd')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown('<div class="sec-label" style="color:#4a6b8a!important;">District Filter</div>', unsafe_allow_html=True)
    has_dist = 'District' in gdf.columns and gdf['District'].notna().any()
    if has_dist:
        dists    = ['All Districts'] + sorted(gdf['District'].dropna().unique().tolist())
        sel_dist = st.selectbox('District', dists, label_visibility='collapsed')
    else:
        sel_dist = 'All Districts'

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown('<div class="sec-label" style="color:#4a6b8a!important;">Score Range</div>', unsafe_allow_html=True)
    srange = st.slider('Score', 0.0, 1.0, (0.0, 1.0), 0.05, label_visibility='collapsed')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown('<div class="sec-label" style="color:#4a6b8a!important;">Top N</div>', unsafe_allow_html=True)
    top_n = st.slider('Neighbourhoods', 5, 50, 15, label_visibility='collapsed')

    st.markdown('<hr style="border-color:#1e2d3d;">', unsafe_allow_html=True)
    st.markdown('''
    <div style="font-size:0.62rem;color:#3a5570;line-height:1.7;">
        <strong style="color:#5a8ab0;">Validation</strong><br>
        IBB Mw7.5 scenario · n=917<br>
        Earthquake core rho=0.74<br>
        AUC=0.89 (worst decile)<br><br>
        <strong style="color:#5a8ab0;">Data</strong><br>
        ESHM20 · GHSL R2023A<br>
        TUiK · IBB 2017 · OSM<br>
        Landsat C2L2 · SEGE-2022<br>
        Copernicus DEM<br><br>
        <strong style="color:#5a8ab0;">Reference</strong><br>
        Nazar & Tatli (2025)<br>
        Gumusehane University
    </div>
    ''', unsafe_allow_html=True)

# ── Filtreleme ────────────────────────────────────────────────────────────────
filt = gdf.copy()
if sel_dist != 'All Districts' and has_dist:
    filt = filt[filt['District'] == sel_dist]
if sel_col in filt.columns:
    filt = filt[filt[sel_col].fillna(0).between(srange[0], srange[1])]
filt = filt.dropna(subset=[sel_col])

# ── Header ────────────────────────────────────────────────────────────────────
dist_show = sel_dist if sel_dist != 'All Districts' else 'Istanbul — All Districts'
st.markdown(f'''
<div class="mupi-header">
    <div>
        <h1>Multi-Hazard Urban Preparedness Index — Decision Support System</h1>
        <p>{dist_show} &nbsp;·&nbsp; {len(filt)} neighbourhoods &nbsp;·&nbsp; Score {srange[0]:.2f}–{srange[1]:.2f}</p>
    </div>
    <span class="mupi-badge">VALIDATED · rho=0.74 · AUC=0.89</span>
</div>
''', unsafe_allow_html=True)

# ── KPI kartlari ──────────────────────────────────────────────────────────────
kpi_html = '<div class="kpi-grid">'
for lbl, col in DIMENSIONS.items():
    if col in filt.columns:
        val  = filt[col].mean()
        hi   = filt[col].max()
        actv = 'active' if col == sel_col else ''
        kpi_html += f'''<div class="kpi-card {actv}">
            <div class="kpi-lbl">{lbl[:12]}</div>
            <div class="kpi-val">{val:.3f}</div>
            <div class="kpi-sub">max {hi:.3f}</div></div>'''
kpi_html += '</div>'
st.markdown(kpi_html, unsafe_allow_html=True)

# ── Sekmeler ──────────────────────────────────────────────────────────────────
tab_map, tab_compare, tab_analytics, tab_scenario, tab_report = st.tabs([
    '🗺️ Map', '⚖️ Compare', '📊 Analytics', '🎯 Scenario Filter', '📋 Report'
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1: MAP
# ════════════════════════════════════════════════════════════════════════════
with tab_map:
    desc = DIM_DESC.get(sel_col, '')
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

            tip_f, tip_a = [], []
            for f, a in [('Mahalle','Neighbourhood'),('District','District'),
                          ('MUPI','MUPI'),('Hazard','Hazard'),
                          ('Exposure','Exposure'),('Social_Vuln','Social Vuln'),
                          ('Physical_Vuln','Physical Vuln'),('Access_Gap','Access Gap')]:
                if f in filt.columns:
                    tip_f.append(f); tip_a.append(a)

            folium.GeoJson(
                gj,
                style_function=lambda x: {'fillOpacity':0,'weight':0},
                highlight_function=lambda x: {'weight':2.5,'color':'#c0392b','fillOpacity':0.1},
                tooltip=folium.GeoJsonTooltip(
                    fields=tip_f, aliases=tip_a, sticky=True,
                    style=('background:rgba(15,25,35,0.93);color:#c8d6e5;'
                           'font-size:12px;border:1px solid #1e2d3d;border-radius:6px;padding:6px 10px;'),
                ),
            ).add_to(m)

            # Top-10 markers
            top10 = filt.nlargest(10, 'MUPI')
            for idx, row in top10.iterrows():
                try:
                    cx = row.geometry.centroid.x
                    cy = row.geometry.centroid.y
                    name  = str(row.get('Mahalle', row.get('unit_id',''))).replace(' Mahallesi','')[:18]
                    score = float(row.get('MUPI', 0))
                    rank  = list(top10.index).index(idx) + 1
                    folium.CircleMarker(
                        location=[cy, cx], radius=6,
                        color='#c0392b', fill=True,
                        fill_color='#e74c3c', fill_opacity=0.9, weight=1.5,
                        tooltip=f'#{rank} {name} — MUPI {score:.3f}',
                    ).add_to(m)
                except Exception:
                    pass

        folium.LayerControl(collapsed=True).add_to(m)
        st_folium(m, width=None, height=540, returned_objects=[])

    with col_panel:
        st.markdown(f'<div class="sec-label">Top {top_n} — {sel_label}</div>', unsafe_allow_html=True)
        if sel_col in filt.columns:
            top_df = (
                filt[['Mahalle', sel_col] + (['District'] if has_dist and 'District' in filt.columns else [])]
                .sort_values(sel_col, ascending=False)
                .head(top_n)
                .reset_index(drop=True)
            )
            rank_html = ''
            for i, row in top_df.iterrows():
                name  = str(row['Mahalle']).replace(' Mahallesi','')[:20]
                score = float(row[sel_col])
                pct   = int(score * 100)
                color = '#c0392b' if score>=0.66 else '#e67e22' if score>=0.33 else '#27ae60'
                rank_html += f'''<div class="rank-row">
                    <div class="rank-num">{i+1}</div>
                    <div style="flex:1">
                        <div class="rank-name">{name}</div>
                        <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;background:{color};"></div></div>
                    </div>
                    <div class="rank-score" style="color:{color};">{score:.3f}</div></div>'''
            st.markdown(rank_html, unsafe_allow_html=True)
            st.markdown('<br>', unsafe_allow_html=True)
            csv = top_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button('⬇️ Export CSV', csv,
                               file_name=f'MUPI_{sel_col}_top{top_n}.csv',
                               mime='text/csv', use_container_width=True)

        # Radar — top mahalle
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="sec-label">Neighbourhood Profile</div>', unsafe_allow_html=True)
        rdims  = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
        rlabls = ['Hazard','Exposure','Social','Physical','Access']
        if len(filt) > 0 and 'MUPI' in filt.columns:
            top1  = filt.sort_values('MUPI', ascending=False).iloc[0]
            avail = [d for d in rdims if d in filt.columns]
            albls = [rlabls[rdims.index(d)] for d in avail]
            if avail:
                vals = [round(float(top1.get(d, 0)), 3) for d in avail]
                fig = go.Figure(go.Scatterpolar(
                    r=vals+[vals[0]], theta=albls+[albls[0]],
                    fill='toself',
                    fillcolor='rgba(192,57,43,0.15)',
                    line=dict(color='#c0392b', width=2),
                ))
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    polar=dict(
                        bgcolor='rgba(0,0,0,0)',
                        radialaxis=dict(visible=True, range=[0,1], tickfont=dict(size=8,color='#8a9bb0'), gridcolor='#e8ecf0'),
                        angularaxis=dict(tickfont=dict(size=9,color='#445'), gridcolor='#e8ecf0'),
                    ),
                    showlegend=False,
                    margin=dict(l=20,r=20,t=35,b=10), height=220,
                    title=dict(text=str(top1.get('Mahalle','')).replace(' Mahallesi','')[:20],
                               font=dict(size=10,color='#1a2d40'), x=0.5),
                )
                st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2: COMPARE (2 mahalle yan yana)
# ════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown('#### Neighbourhood Comparison')
    st.caption('Select two neighbourhoods to compare their risk profiles side by side.')

    all_names = sorted(gdf['Mahalle'].dropna().unique().tolist()) if 'Mahalle' in gdf.columns else []

    c1, c2 = st.columns(2)
    with c1:
        n1 = st.selectbox('Neighbourhood A', all_names,
                           index=0, key='cmp_n1')
    with c2:
        n2 = st.selectbox('Neighbourhood B', all_names,
                           index=min(1, len(all_names)-1), key='cmp_n2')

    rdims  = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
    rlabls = ['Hazard','Exposure','Social Vuln','Physical Vuln','Access Gap']
    avail  = [d for d in rdims if d in gdf.columns]
    albls  = [rlabls[rdims.index(d)] for d in avail]

    row1 = gdf[gdf['Mahalle'] == n1].iloc[0] if len(gdf[gdf['Mahalle']==n1]) > 0 else None
    row2 = gdf[gdf['Mahalle'] == n2].iloc[0] if len(gdf[gdf['Mahalle']==n2]) > 0 else None

    if row1 is not None and row2 is not None and avail:
        vals1 = [round(float(row1.get(d, 0)), 3) for d in avail]
        vals2 = [round(float(row2.get(d, 0)), 3) for d in avail]

        # Radar karsilastirma
        fig_cmp = go.Figure()
        fig_cmp.add_trace(go.Scatterpolar(
            r=vals1+[vals1[0]], theta=albls+[albls[0]],
            fill='toself', name=n1.replace(' Mahallesi',''),
            fillcolor='rgba(192,57,43,0.15)',
            line=dict(color='#c0392b', width=2),
        ))
        fig_cmp.add_trace(go.Scatterpolar(
            r=vals2+[vals2[0]], theta=albls+[albls[0]],
            fill='toself', name=n2.replace(' Mahallesi',''),
            fillcolor='rgba(41,128,185,0.15)',
            line=dict(color='#2980b9', width=2),
        ))
        fig_cmp.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,1])),
            legend=dict(orientation='h', yanchor='bottom', y=-0.15),
            margin=dict(l=40,r=40,t=40,b=60), height=400,
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

        # Tablo karsilastirma
        st.markdown('##### Dimension Scores')
        rows = []
        for d, lbl in zip(avail, albls):
            v1 = float(row1.get(d, 0))
            v2 = float(row2.get(d, 0))
            diff = v1 - v2
            rows.append({'Dimension': lbl,
                         n1.replace(' Mahallesi',''): f'{v1:.3f}',
                         n2.replace(' Mahallesi',''): f'{v2:.3f}',
                         'Difference (A-B)': f'{diff:+.3f}'})
        cmp_df = pd.DataFrame(rows)
        st.dataframe(cmp_df, use_container_width=True, hide_index=True)

        # MUPI ozeti
        m1 = float(row1.get('MUPI', 0))
        m2 = float(row2.get('MUPI', 0))
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric(n1.replace(' Mahallesi','')[:20], f'{m1:.3f}', 'MUPI Score')
        mc2.metric(n2.replace(' Mahallesi','')[:20], f'{m2:.3f}', 'MUPI Score')
        mc3.metric('Difference', f'{abs(m1-m2):.3f}',
                   f'{"A higher" if m1>m2 else "B higher"}')

        # Export
        csv2 = cmp_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button('⬇️ Export Comparison CSV', csv2,
                           file_name='MUPI_comparison.csv', mime='text/csv')

# ════════════════════════════════════════════════════════════════════════════
# TAB 3: ANALYTICS
# ════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown('#### Statistical Analytics')
    st.caption('Explore distributions and inter-dimension correlations across the filtered dataset.')

    if len(avail_scores) >= 2:
        acol1, acol2 = st.columns(2)

        # Korelasyon matrisi
        with acol1:
            st.markdown('##### Dimension Correlation Matrix')
            st.caption('Spearman rank correlation — note Social Vuln vs Physical Vuln divergence.')
            corr_df = filt[avail_scores].corr(method='spearman').round(2)
            corr_labels = [DIM_LABELS.get(c, c) for c in avail_scores]
            fig_corr = go.Figure(go.Heatmap(
                z=corr_df.values.tolist(),
                x=corr_labels, y=corr_labels,
                colorscale='RdBu_r',
                zmin=-1, zmax=1,
                text=[[f'{v:.2f}' for v in row] for row in corr_df.values.tolist()],
                texttemplate='%{text}',
                textfont=dict(size=11),
                colorbar=dict(title='rho', len=0.8),
            ))
            fig_corr.update_layout(
                height=380, margin=dict(l=10,r=10,t=10,b=10),
                coloraxis_colorbar=dict(title='rho', len=0.8),
            )
            fig_corr.update_traces(textfont_size=11)
            st.plotly_chart(fig_corr, use_container_width=True)

        # Dagilim
        with acol2:
            st.markdown('##### Score Distribution')
            x_ax = st.selectbox('X axis', list(DIMENSIONS.keys()), index=0, key='an_x')
            y_ax = st.selectbox('Y axis', list(DIMENSIONS.keys()), index=4, key='an_y')
            x_col = DIMENSIONS[x_ax]
            y_col = DIMENSIONS[y_ax]
            if x_col in filt.columns and y_col in filt.columns:
                # Use go.Scatter directly to avoid narwhals duplicate-column bug
                sc_df = filt.copy()
                x_vals = sc_df[x_col].fillna(0).tolist()
                y_vals = sc_df[y_col].fillna(0).tolist()
                c_vals = sc_df['MUPI'].fillna(0).tolist() if 'MUPI' in sc_df.columns else [0]*len(sc_df)
                names  = sc_df['Mahalle'].fillna('').tolist() if 'Mahalle' in sc_df.columns else ['']*len(sc_df)
                tips   = [f'{n}<br>{x_ax}: {x:.3f}<br>{y_ax}: {y:.3f}<br>MUPI: {c:.3f}'
                          for n, x, y, c in zip(names, x_vals, y_vals, c_vals)]
                fig_sc = go.Figure(go.Scatter(
                    x=x_vals, y=y_vals, mode='markers',
                    marker=dict(
                        size=5, opacity=0.75,
                        color=c_vals, colorscale='YlOrRd',
                        colorbar=dict(title='MUPI', len=0.8),
                        showscale=True,
                    ),
                    text=tips, hoverinfo='text',
                ))
                fig_sc.update_layout(
                    height=380, margin=dict(l=10,r=10,t=10,b=10),
                    xaxis_title=x_ax, yaxis_title=y_ax,
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_sc, use_container_width=True)

        # Histogram grid
        st.markdown('##### Score Distributions by Dimension')
        hist_cols = st.columns(3)
        for i, col in enumerate(avail_scores[:6]):
            with hist_cols[i % 3]:
                h_vals = filt[col].dropna().tolist()
                fig_h  = go.Figure(go.Histogram(
                    x=h_vals, nbinsx=30,
                    marker_color='#c0392b', opacity=0.85,
                ))
                fig_h.update_layout(
                    height=200, margin=dict(l=5,r=5,t=25,b=5),
                    title=dict(text=DIM_LABELS.get(col,col), font=dict(size=11)),
                    showlegend=False, bargap=0.05,
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis_title='Score', yaxis_title='Count',
                )
                st.plotly_chart(fig_h, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 4: SCENARIO FILTER
# ════════════════════════════════════════════════════════════════════════════
with tab_scenario:
    st.markdown('#### Multi-Dimension Scenario Filter')
    st.caption('Set thresholds across multiple dimensions simultaneously to identify high-priority neighbourhoods.')

    scol1, scol2 = st.columns([1, 2])

    with scol1:
        st.markdown('##### Set Thresholds')
        thresholds = {}
        for lbl, col in DIMENSIONS.items():
            if col in gdf.columns and col != 'MUPI':
                t = st.slider(
                    f'{lbl} ≥',
                    min_value=0.0, max_value=1.0, value=0.0, step=0.05,
                    key=f'thresh_{col}'
                )
                thresholds[col] = t

        st.markdown('---')
        scenario_name = st.text_input('Scenario name', value='High Risk Priority')

    # Senaryo filtresi uygula
    scen = gdf.copy()
    for col, t in thresholds.items():
        if t > 0:
            scen = scen[scen[col].fillna(0) >= t]

    with scol2:
        st.markdown(f'##### Results: **{len(scen)}** neighbourhoods match')

        active_chips = ' '.join([
            f'<span class="scenario-chip">{DIM_LABELS.get(c,c)} ≥ {t:.2f}</span>'
            for c, t in thresholds.items() if t > 0
        ])
        if active_chips:
            st.markdown(f'Active filters: {active_chips}', unsafe_allow_html=True)
        st.markdown('')

        if len(scen) > 0 and 'MUPI' in scen.columns:
            scen_display = (
                scen[['Mahalle','District','MUPI','Hazard','Exposure',
                       'Social_Vuln','Physical_Vuln','Access_Gap']]
                if has_dist else
                scen[['Mahalle','MUPI','Hazard','Exposure',
                       'Social_Vuln','Physical_Vuln','Access_Gap']]
            )
            scen_display = (
                scen_display
                .dropna(subset=['MUPI'])
                .sort_values('MUPI', ascending=False)
                .reset_index(drop=True)
            )
            scen_display.index += 1
            scen_display.columns = [c.replace('_',' ') for c in scen_display.columns]
            st.dataframe(scen_display, use_container_width=True, height=350)

            csv_s = scen_display.to_csv(index=True).encode('utf-8-sig')
            st.download_button(
                f'⬇️ Export "{scenario_name}" ({len(scen)} neighbourhoods)',
                csv_s,
                file_name=f'MUPI_scenario_{scenario_name.replace(" ","_")}.csv',
                mime='text/csv',
            )
        elif len(scen) == 0:
            st.info('No neighbourhoods match the current thresholds. Try lowering one or more values.')

# ════════════════════════════════════════════════════════════════════════════
# TAB 5: REPORT
# ════════════════════════════════════════════════════════════════════════════
with tab_report:
    st.markdown('#### Neighbourhood Risk Report')
    st.caption('Select a neighbourhood to generate a summary report suitable for stakeholder briefings.')

    all_names_r = sorted(gdf['Mahalle'].dropna().unique().tolist()) if 'Mahalle' in gdf.columns else []
    rep_name    = st.selectbox('Select neighbourhood', all_names_r, key='rep_name')

    rep_row = gdf[gdf['Mahalle'] == rep_name]
    if len(rep_row) > 0:
        r = rep_row.iloc[0]
        rdims  = ['Hazard','Exposure','Social_Vuln','Physical_Vuln','Access_Gap']
        rlabls = ['Hazard','Exposure','Social Vulnerability','Physical Vulnerability','Access Gap']
        avail_r = [d for d in rdims if d in gdf.columns]
        albl_r  = [rlabls[rdims.index(d)] for d in avail_r]

        # Rank hesapla
        if 'MUPI' in gdf.columns:
            rank_val = int(gdf['MUPI'].rank(ascending=False).loc[rep_row.index[0]])
            total_n  = len(gdf)
            pct_rank = round((1 - rank_val/total_n)*100, 1)
        else:
            rank_val, total_n, pct_rank = 'N/A', len(gdf), 0

        rc1, rc2 = st.columns([2, 1])

        with rc1:
            mupi_val = float(r.get('MUPI', 0))
            risk_lvl = 'HIGH' if mupi_val >= 0.66 else 'MEDIUM' if mupi_val >= 0.33 else 'LOW'
            risk_col = '#c0392b' if mupi_val >= 0.66 else '#e67e22' if mupi_val >= 0.33 else '#27ae60'

            st.markdown(f'''
            <div class="report-card">
                <div class="report-title">MUPI Risk Report</div>
                <h2 style="margin:0;color:#0f1923;">{rep_name.replace(" Mahallesi","")}</h2>
                <p style="color:#667;font-size:0.8rem;margin:0.2rem 0 0.6rem;">
                    {r.get("District","") if has_dist else ""} &nbsp;·&nbsp; Istanbul, Turkiye
                </p>
                <div style="display:flex;gap:1.2rem;margin-top:0.5rem;">
                    <div>
                        <div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">MUPI Score</div>
                        <div style="font-size:2rem;font-weight:700;color:{risk_col};font-family:DM Mono,monospace;">{mupi_val:.3f}</div>
                    </div>
                    <div>
                        <div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">Risk Level</div>
                        <div style="font-size:1.4rem;font-weight:700;color:{risk_col};">{risk_lvl}</div>
                    </div>
                    <div>
                        <div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">City Rank</div>
                        <div style="font-size:1.4rem;font-weight:700;color:#1a2d40;">#{rank_val} / {total_n}</div>
                    </div>
                    <div>
                        <div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;">Percentile</div>
                        <div style="font-size:1.4rem;font-weight:700;color:#1a2d40;">Top {100-pct_rank:.0f}%</div>
                    </div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

            # Boyut detaylari
            st.markdown('<div class="report-card"><div class="report-title">Dimension Scores</div>', unsafe_allow_html=True)
            for d, lbl in zip(avail_r, albl_r):
                v    = float(r.get(d, 0))
                pct  = int(v * 100)
                col_ = '#c0392b' if v>=0.66 else '#e67e22' if v>=0.33 else '#27ae60'
                note = ''
                if d == 'Social_Vuln' and v < 0.4:
                    note = ' (Note: low social vuln may mask recovery deficit — see paper dissociation finding)'
                if d == 'Physical_Vuln' and v >= 0.7:
                    note = ' (High pre-2000 or mid-rise stock — priority for structural retrofit)'
                st.markdown(f'''
                <div style="margin:0.4rem 0;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                        <span style="font-size:0.76rem;color:#445;font-weight:500;">{lbl}</span>
                        <span style="font-size:0.76rem;font-family:DM Mono,monospace;color:{col_};font-weight:600;">{v:.3f}</span>
                    </div>
                    <div style="background:#f0f2f5;border-radius:3px;height:5px;">
                        <div style="width:{pct}%;background:{col_};height:5px;border-radius:3px;"></div>
                    </div>
                    <div style="font-size:0.63rem;color:#999;margin-top:1px;">{note}</div>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Eylem onerileri
            st.markdown('<div class="report-card"><div class="report-title">Planning Recommendations</div>', unsafe_allow_html=True)
            recs = []
            phys = float(r.get('Physical_Vuln', 0))
            soc  = float(r.get('Social_Vuln', 0))
            acc  = float(r.get('Access_Gap', 0))
            haz  = float(r.get('Hazard', 0))
            if phys >= 0.66:
                recs.append('🏗️ <strong>Structural priority:</strong> High pre-2000 and/or mid-rise building fraction — prioritise seismic retrofit and building inspection programmes.')
            if soc >= 0.5:
                recs.append('👥 <strong>Social support:</strong> Elevated elderly/child share or low development index — strengthen evacuation assistance, community outreach, and post-disaster social services.')
            if acc >= 0.6:
                recs.append('🚑 <strong>Access deficit:</strong> Long road-network distances to hospital or fire station — consider pre-positioning emergency resources or improving road connectivity.')
            if haz >= 0.7:
                recs.append('⚠️ <strong>High hazard exposure:</strong> Elevated seismic PGA, flood susceptibility, or heat — enforce hazard-aware zoning and early-warning systems.')
            if not recs:
                recs.append('✅ <strong>Below critical thresholds</strong> across all dimensions — standard preparedness monitoring recommended.')
            for rec in recs:
                st.markdown(f'<p style="font-size:0.75rem;color:#333;margin:0.4rem 0;">{rec}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with rc2:
            # Radar
            if avail_r:
                vals_r = [round(float(r.get(d, 0)), 3) for d in avail_r]
                fig_r  = go.Figure(go.Scatterpolar(
                    r=vals_r+[vals_r[0]], theta=albl_r+[albl_r[0]],
                    fill='toself',
                    fillcolor=f'rgba(192,57,43,0.18)',
                    line=dict(color='#c0392b', width=2),
                ))
                fig_r.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0,1], tickfont=dict(size=8)),
                        angularaxis=dict(tickfont=dict(size=9)),
                    ),
                    showlegend=False,
                    margin=dict(l=25,r=25,t=40,b=10), height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    title=dict(text='Risk Profile', font=dict(size=11,color='#445'), x=0.5),
                )
                st.plotly_chart(fig_r, use_container_width=True)

            # City context bar chart
            if 'MUPI' in gdf.columns:
                st.markdown('<div style="font-size:0.65rem;color:#8a9bb0;text-transform:uppercase;font-weight:600;margin:0.5rem 0 0.3rem;">City Context (MUPI Distribution)</div>', unsafe_allow_html=True)
                mupi_list = gdf['MUPI'].dropna().tolist()
                fig_ctx = go.Figure(go.Histogram(
                    x=mupi_list, nbinsx=40,
                    marker_color='#c8d6e5', opacity=0.9,
                ))
                mupi_v  = float(r.get('MUPI', 0))
                fig_ctx.add_vline(x=mupi_v, line_color='#c0392b', line_width=2,
                                  annotation_text=f'{rep_name.replace(" Mahallesi","")[:12]}',
                                  annotation_font_size=9, annotation_font_color='#c0392b')
                fig_ctx.update_layout(
                    height=200, margin=dict(l=5,r=5,t=5,b=5),
                    xaxis_title='MUPI Score', yaxis_title='Count',
                    showlegend=False, bargap=0.05,
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(fig_ctx, use_container_width=True)

        # Kaynak / imza
        st.markdown(f'''
        <div style="font-size:0.62rem;color:#aab;margin-top:0.5rem;border-top:1px solid #e8ecf0;padding-top:0.4rem;">
        Generated by MUPI-DSS v3.0 &nbsp;|&nbsp; Nazar & Tatli (2025), Gumusehane University &nbsp;|&nbsp;
        External validation: rho=0.74, AUC=0.89 vs IBB Mw7.5 scenario (n=917) &nbsp;|&nbsp;
        Data: ESHM20 · GHSL R2023A · TUiK · IBB 2017 · OSM · Landsat C2L2 · SEGE-2022 · Copernicus DEM
        </div>
        ''', unsafe_allow_html=True)

# ── Alt footer ────────────────────────────────────────────────────────────────
st.markdown('<hr style="margin-top:0.8rem;">', unsafe_allow_html=True)
st.markdown('''
<div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:0.62rem;color:#aab;">
        MUPI-DSS v3.0 &nbsp;|&nbsp; Nazar & Tatli (2025), Gumusehane University &nbsp;|&nbsp;
        ESHM20 · GHSL · TUiK · IBB · OSM · Landsat · SEGE-2022 · Copernicus DEM
    </span>
    <span style="font-size:0.62rem;color:#c0392b;font-weight:600;">
        Validated: rho=0.74 · AUC=0.89 (IBB Mw7.5, n=917)
    </span>
</div>
''', unsafe_allow_html=True)
