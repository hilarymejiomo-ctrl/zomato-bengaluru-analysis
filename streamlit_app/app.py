"""
Application Streamlit - Analyse des Restaurants Zomato à Bengaluru
"""

from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(
    page_title="Analyse Zomato Bengaluru",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #E23744;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2C3E50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

def _find_dataset_path() -> Path:
    """
    Rend le chemin dataset robuste:
    - fonctionne si on lance streamlit depuis la racine
    - ou depuis streamlit_app/
    """
    here = Path(__file__).resolve()
    candidates = [
        here.parent / ".." / "data" / "zomato.csv",  # streamlit_app/app.py -> ../data
        Path.cwd() / "data" / "zomato.csv",          # si on lance depuis la racine
        here.parent / "data" / "zomato.csv",         # si data est dans streamlit_app (rare)
    ]
    for p in candidates:
        p = p.resolve()
        if p.exists():
            return p
    return candidates[0].resolve()

@st.cache_data
def load_data() -> pd.DataFrame:
    """Charge et nettoie les données Zomato"""
    path = _find_dataset_path()

    if not path.exists():
        # Message clair et stop (évite bugs)
        st.error("⚠️ Dataset introuvable : `data/zomato.csv`")
        st.info(
            "👉 Solution : télécharge le dataset et place-le ici :\n\n"
            "**zomato-bengaluru-analysis/data/zomato.csv**\n\n"
            "Puis relance l'application."
        )
        st.stop()

    df = pd.read_csv(path)

    # Nettoyage de la colonne rate
    def clean_rate(rate):
        if pd.isna(rate):
            return np.nan
        rate = str(rate).strip()
        if rate in ("NEW", "-", "nan", ""):
            return np.nan
        try:
            return float(rate.split("/")[0].strip())
        except Exception:
            return np.nan

    if "rate" in df.columns:
        df["rate"] = df["rate"].apply(clean_rate)
    else:
        df["rate"] = np.nan

    # Nettoyage du coût
    def clean_cost(cost):
        if pd.isna(cost):
            return np.nan
        try:
            return float(str(cost).replace(",", "").strip())
        except Exception:
            return np.nan

    cost_col = "approx_cost(for two people)"
    if cost_col in df.columns:
        df[cost_col] = df[cost_col].apply(clean_cost)
    else:
        df[cost_col] = np.nan

    # Conversion des votes
    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce")
    else:
        df["votes"] = np.nan

    # Catégorisation des prix
    def categorize_price(cost):
        if pd.isna(cost):
            return "Inconnu"
        if cost < 300:
            return "Économique"
        if cost < 700:
            return "Modéré"
        if cost < 1500:
            return "Élevé"
        return "Luxe"

    df["price_category"] = df[cost_col].apply(categorize_price)

    # Normaliser quelques colonnes attendues
    for col in ["location", "listed_in(city)", "rest_type", "cuisines", "name"]:
        if col not in df.columns:
            df[col] = np.nan

    return df

# Chargement des données
df = load_data()

# ============================================================================
# EN-TÊTE
# ============================================================================

st.markdown('<h1 class="main-header">🍽️ Analyse des Restaurants à Bengaluru</h1>', unsafe_allow_html=True)
st.markdown("**Exploration interactive du paysage gastronomique de Bengaluru via Zomato**")
st.markdown("---")

# ============================================================================
# SIDEBAR - FILTRES
# ============================================================================

st.sidebar.title("🔍 Filtres")
st.sidebar.markdown("Personnalisez votre analyse")

# Filtre par quartier
all_locations = ["Tous"] + sorted(df["location"].dropna().unique().tolist())
selected_location = st.sidebar.selectbox("📍 Sélectionner un quartier", all_locations)

# Filtre par catégorie de prix
price_categories = ["Tous"] + sorted(df["price_category"].dropna().unique().tolist())
selected_price = st.sidebar.selectbox("💰 Catégorie de prix", price_categories)

# Filtre par note minimale
min_rating = st.sidebar.slider(
    "⭐ Note minimale",
    min_value=0.0,
    max_value=5.0,
    value=0.0,
    step=0.5
)

# Application des filtres
df_filtered = df.copy()

if selected_location != "Tous":
    df_filtered = df_filtered[df_filtered["location"] == selected_location]

if selected_price != "Tous":
    df_filtered = df_filtered[df_filtered["price_category"] == selected_price]

# Important: éviter NaN >= min_rating (sinon NaN disparaît sans surprise)
df_filtered = df_filtered[df_filtered["rate"].fillna(-1) >= min_rating]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Restaurants affichés :** {len(df_filtered):,} / {len(df):,}")

# ============================================================================
# MÉTRIQUES PRINCIPALES
# ============================================================================

st.markdown('<h2 class="sub-header">📊 Vue d\'ensemble</h2>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🏪 Nombre de restaurants", f"{len(df_filtered):,}")

with col2:
    avg_rating = df_filtered["rate"].mean()
    st.metric("⭐ Note moyenne", f"{avg_rating:.2f}/5.0" if not pd.isna(avg_rating) else "N/A")

with col3:
    avg_cost = df_filtered["approx_cost(for two people)"].mean()
    st.metric("💵 Coût moyen (2 pers.)", f"{avg_cost:.0f} INR" if not pd.isna(avg_cost) else "N/A")

with col4:
    total_votes = df_filtered["votes"].sum()
    st.metric("👥 Total des votes", f"{total_votes:,.0f}" if not pd.isna(total_votes) else "N/A")

st.markdown("---")

# ============================================================================
# VISUALISATIONS INTERACTIVES
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺️ Géographie",
    "🍽️ Types & Cuisines",
    "💰 Prix & Popularité",
    "📈 Comparaisons"
])

# ========== ONGLET 1 : GÉOGRAPHIE ==========
with tab1:
    st.markdown('<h2 class="sub-header">📍 Distribution géographique</h2>', unsafe_allow_html=True)

    colA, colB = st.columns(2)

    with colA:
        top_locations = df_filtered["location"].value_counts().head(15)
        fig_loc = px.bar(
            x=top_locations.values,
            y=top_locations.index,
            orientation="h",
            title="Top 15 des quartiers",
            labels={"x": "Nombre de restaurants", "y": "Quartier"},
            color=top_locations.values,
            color_continuous_scale="Viridis"
        )
        fig_loc.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_loc, use_container_width=True)

    with colB:
        city_dist = df_filtered["listed_in(city)"].value_counts().head(10)
        fig_city = px.pie(
            values=city_dist.values,
            names=city_dist.index,
            title="Distribution par zone urbaine (Top 10)",
            hole=0.4
        )
        fig_city.update_layout(height=500)
        st.plotly_chart(fig_city, use_container_width=True)

    st.markdown("#### 📊 Profil des quartiers (Top 10)")
    top_10_locations = df_filtered["location"].value_counts().head(10).index
    location_profile = (
        df_filtered[df_filtered["location"].isin(top_10_locations)]
        .groupby("location")
        .agg({
            "name": "count",
            "rate": "mean",
            "votes": "mean",
            "approx_cost(for two people)": "mean"
        })
        .round(2)
    )
    location_profile.columns = ["Nombre", "Note moy.", "Votes moy.", "Coût moy. (INR)"]
    location_profile = location_profile.sort_values("Nombre", ascending=False)
    st.dataframe(location_profile, use_container_width=True)

# ========== ONGLET 2 : TYPES & CUISINES ==========
with tab2:
    st.markdown('<h2 class="sub-header">🍽️ Types de restaurants et cuisines</h2>', unsafe_allow_html=True)

    colA, colB = st.columns(2)

    with colA:
        rest_types = df_filtered["rest_type"].value_counts().head(15)
        fig_types = px.bar(
            x=rest_types.values,
            y=rest_types.index,
            orientation="h",
            title="Top 15 types de restaurants",
            labels={"x": "Nombre", "y": "Type"},
            color=rest_types.values,
            color_continuous_scale="Blues"
        )
        fig_types.update_layout(height=600)
        st.plotly_chart(fig_types, use_container_width=True)

    with colB:
        all_cuisines = df_filtered["cuisines"].dropna().str.split(",").explode().str.strip()
        cuisine_counts = all_cuisines.value_counts().head(15)
        fig_cuisines = px.bar(
            x=cuisine_counts.values,
            y=cuisine_counts.index,
            orientation="h",
            title="Top 15 cuisines",
            labels={"x": "Nombre de restaurants", "y": "Cuisine"},
            color=cuisine_counts.values,
            color_continuous_scale="Reds"
        )
        fig_cuisines.update_layout(height=600)
        st.plotly_chart(fig_cuisines, use_container_width=True)

# ========== ONGLET 3 : PRIX & POPULARITÉ ==========
with tab3:
    st.markdown('<h2 class="sub-header">💰 Analyse des prix et de la popularité</h2>', unsafe_allow_html=True)

    colA, colB = st.columns(2)

    with colA:
        fig_rate = px.histogram(
            df_filtered.dropna(subset=["rate"]),
            x="rate",
            nbins=30,
            title="Distribution des notes",
            labels={"rate": "Note", "count": "Fréquence"}
        )
        fig_rate.update_layout(height=400)
        st.plotly_chart(fig_rate, use_container_width=True)

    with colB:
        price_dist = df_filtered["price_category"].value_counts()
        fig_price = px.pie(
            values=price_dist.values,
            names=price_dist.index,
            title="Répartition par catégorie de prix",
            hole=0.3
        )
        fig_price.update_layout(height=400)
        st.plotly_chart(fig_price, use_container_width=True)

    st.markdown("#### 🔗 Relation entre prix, note et popularité")
    fig_scatter = px.scatter(
        df_filtered.dropna(subset=["approx_cost(for two people)", "rate", "votes"]),
        x="approx_cost(for two people)",
        y="rate",
        size="votes",
        color="votes",
        hover_data=["name", "location"],
        title="Prix vs Note (taille = votes)",
        labels={
            "approx_cost(for two people)": "Coût pour deux (INR)",
            "rate": "Note",
            "votes": "Votes"
        },
        color_continuous_scale="Viridis"
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("#### 📊 Matrice de corrélation")
    corr_data = df_filtered[["rate", "votes", "approx_cost(for two people)"]].corr()
    fig_corr = px.imshow(
        corr_data,
        text_auto=".3f",
        aspect="auto",
        title="Corrélation : Note, Votes, Coût",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1
    )
    fig_corr.update_layout(height=400)
    st.plotly_chart(fig_corr, use_container_width=True)

# ========== ONGLET 4 : COMPARAISONS ==========
with tab4:
    st.markdown('<h2 class="sub-header">📈 Comparaisons détaillées</h2>', unsafe_allow_html=True)

    st.markdown("#### ⭐ Distribution des notes par catégorie de prix")
    price_order = ["Économique", "Modéré", "Élevé", "Luxe"]
    price_data = df_filtered[df_filtered["price_category"].isin(price_order)]

    fig_box_price = px.box(
        price_data,
        x="price_category",
        y="rate",
        color="price_category",
        title="Notes par catégorie de prix",
        labels={"price_category": "Catégorie", "rate": "Note"},
        category_orders={"price_category": price_order}
    )
    fig_box_price.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig_box_price, use_container_width=True)

    st.markdown("#### 🏙️ Comparaison des quartiers (Top 5)")
    top_5_locations = df_filtered["location"].value_counts().head(5).index

    fig_box_loc = go.Figure()
    for loc in top_5_locations:
        loc_data = df_filtered[df_filtered["location"] == loc]
        fig_box_loc.add_trace(go.Box(y=loc_data["rate"], name=loc, boxmean="sd"))

    fig_box_loc.update_layout(
        title="Distribution des notes par quartier",
        yaxis_title="Note",
        xaxis_title="Quartier",
        height=500
    )
    st.plotly_chart(fig_box_loc, use_container_width=True)

# ============================================================================
# TOP RESTAURANTS
# ============================================================================

st.markdown("---")
st.markdown('<h2 class="sub-header">🏆 Top Restaurants</h2>', unsafe_allow_html=True)

colA, colB = st.columns(2)

with colA:
    st.markdown("#### 👥 Les plus populaires (votes)")
    top_popular = (
        df_filtered.dropna(subset=["votes"])
        .nlargest(10, "votes")[["name", "location", "rate", "votes", "approx_cost(for two people)"]]
        .reset_index(drop=True)
    )
    top_popular.index += 1
    st.dataframe(top_popular, use_container_width=True)

with colB:
    st.markdown("#### ⭐ Les mieux notés")
    top_rated = (
        df_filtered.dropna(subset=["rate"])
        .nlargest(10, "rate")[["name", "location", "rate", "votes", "approx_cost(for two people)"]]
        .reset_index(drop=True)
    )
    top_rated.index += 1
    st.dataframe(top_rated, use_container_width=True)

# ============================================================================
# RECHERCHE DE RESTAURANT
# ============================================================================

st.markdown("---")
st.markdown('<h2 class="sub-header">🔎 Recherche de restaurant</h2>', unsafe_allow_html=True)

search_name = st.text_input("Rechercher un restaurant par nom :")

if search_name:
    search_results = df_filtered[
        df_filtered["name"].astype(str).str.contains(search_name, case=False, na=False)
    ][["name", "location", "cuisines", "rate", "votes", "approx_cost(for two people)", "rest_type"]]

    if len(search_results) > 0:
        st.success(f"✅ {len(search_results)} restaurant(s) trouvé(s)")
        st.dataframe(search_results.reset_index(drop=True), use_container_width=True)
    else:
        st.warning("⚠️ Aucun restaurant trouvé avec ce nom")

# ============================================================================
# PIED DE PAGE
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d; padding: 2rem;'>
    <p><strong>🍽️ Analyse des Restaurants Zomato à Bengaluru</strong></p>
    <p>Projet réalisé dans le cadre du cours 8PRO408</p>
    <p>UQAC - Décembre 2025</p>
</div>
""", unsafe_allow_html=True)
