"""
Module d'analyse de données — Y-Plaza
Utilise pandas pour le nettoyage/agrégation et SQLAlchemy text() pour les requêtes SQL brutes.
"""

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _query_to_df(db: Session, sql: str, params: dict | None = None) -> pd.DataFrame:
    """Exécute une requête SQL brute et retourne un DataFrame pandas."""
    result = db.execute(text(sql), params or {})
    rows = result.fetchall()
    columns = list(result.keys())
    return pd.DataFrame(rows, columns=columns)


# ---------------------------------------------------------------------------
# 1. Rapport des ventes (CA, volumes, par agence, par ville, par type)
# ---------------------------------------------------------------------------

def rapport_ventes(db: Session) -> dict:
    """
    Requête SQL brute : récapitulatif des ventes finalisées.
    Retourne CA total, volume, détail par agence, par ville et par type de bien.
    """

    # Transactions finalisées avec données du bien et de l'agence
    sql_transactions = """
        SELECT
            t.id            AS tx_id,
            t.offered_price AS prix_offert,
            t.created_at    AS date_transaction,
            p.price         AS prix_annonce,
            p.city          AS ville,
            p.property_type AS type_bien,
            p.transaction_type AS type_transaction,
            a.name          AS agence
        FROM transactions t
        JOIN properties p ON t.property_id = p.id
        LEFT JOIN agencies a ON p.agency_id = a.id
        WHERE t.status = 'completed'
        ORDER BY t.created_at DESC
    """
    df = _query_to_df(db, sql_transactions)

    if df.empty:
        return {
            "ca_total": 0,
            "volume_transactions": 0,
            "par_agence": [],
            "par_ville": [],
            "par_type_bien": [],
            "par_mois": [],
        }

    df["prix_offert"] = pd.to_numeric(df["prix_offert"], errors="coerce").fillna(0)
    df["date_transaction"] = pd.to_datetime(df["date_transaction"], utc=True)
    df["mois"] = df["date_transaction"].dt.to_period("M").astype(str)

    # Agrégation par agence
    par_agence = (
        df.groupby("agence", dropna=False)
        .agg(ca=("prix_offert", "sum"), volume=("tx_id", "count"))
        .reset_index()
        .rename(columns={"agence": "label"})
        .sort_values("ca", ascending=False)
        .to_dict("records")
    )

    # Agrégation par ville
    par_ville = (
        df.groupby("ville")
        .agg(ca=("prix_offert", "sum"), volume=("tx_id", "count"))
        .reset_index()
        .rename(columns={"ville": "label"})
        .sort_values("ca", ascending=False)
        .head(10)
        .to_dict("records")
    )

    # Agrégation par type de bien
    par_type = (
        df.groupby("type_bien")
        .agg(ca=("prix_offert", "sum"), volume=("tx_id", "count"))
        .reset_index()
        .rename(columns={"type_bien": "label"})
        .sort_values("ca", ascending=False)
        .to_dict("records")
    )

    # Évolution mensuelle
    par_mois = (
        df.groupby("mois")
        .agg(ca=("prix_offert", "sum"), volume=("tx_id", "count"))
        .reset_index()
        .rename(columns={"mois": "label"})
        .sort_values("label")
        .to_dict("records")
    )

    return {
        "ca_total": float(df["prix_offert"].sum()),
        "volume_transactions": int(df["tx_id"].count()),
        "par_agence": par_agence,
        "par_ville": par_ville,
        "par_type_bien": par_type,
        "par_mois": par_mois,
    }


# ---------------------------------------------------------------------------
# 2. Biens les plus populaires (favoris + demandes)
# ---------------------------------------------------------------------------

def biens_populaires(db: Session, limit: int = 10) -> list[dict]:
    """
    SQL brut : classe les biens par nombre de favoris + nombre de demandes.
    Indique la popularité relative pour cibler les biens à forte demande.
    """
    sql = """
        SELECT
            p.id,
            p.title,
            p.city,
            p.price,
            p.property_type,
            p.status,
            COUNT(DISTINCT f.id) AS nb_favoris,
            COUNT(DISTINCT t.id) AS nb_demandes
        FROM properties p
        LEFT JOIN favorites f ON f.property_id = p.id
        LEFT JOIN transactions t ON t.property_id = p.id
        GROUP BY p.id, p.title, p.city, p.price, p.property_type, p.status
        ORDER BY (COUNT(DISTINCT f.id) + COUNT(DISTINCT t.id) * 2) DESC
        LIMIT :limit
    """
    df = _query_to_df(db, sql, {"limit": limit})
    if df.empty:
        return []
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# 3. Prix au m² par ville (zones intéressantes)
# ---------------------------------------------------------------------------

def prix_m2_par_ville(db: Session) -> list[dict]:
    """
    SQL brut : prix moyen au m² par ville, pour les biens disponibles avec surface renseignée.
    Permet d'identifier les zones intéressantes et les tendances de marché.
    """
    sql = """
        SELECT
            p.city                                    AS ville,
            COUNT(p.id)                               AS nb_biens,
            ROUND(AVG(p.price)::numeric, 0)           AS prix_moyen,
            ROUND(AVG(p.price / NULLIF(p.surface, 0))::numeric, 0) AS prix_m2_moyen,
            ROUND(MIN(p.price / NULLIF(p.surface, 0))::numeric, 0) AS prix_m2_min,
            ROUND(MAX(p.price / NULLIF(p.surface, 0))::numeric, 0) AS prix_m2_max
        FROM properties p
        WHERE p.surface IS NOT NULL
          AND p.surface > 0
          AND p.status = 'available'
        GROUP BY p.city
        HAVING COUNT(p.id) >= 1
        ORDER BY prix_m2_moyen DESC
    """
    df = _query_to_df(db, sql)
    if df.empty:
        return []
    # Nettoyage pandas : supprime les lignes avec prix_m2_moyen nul
    df = df.dropna(subset=["prix_m2_moyen"])
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# 4. Statistiques globales du catalogue
# ---------------------------------------------------------------------------

def stats_catalogue(db: Session) -> dict:
    """
    SQL brut : statistiques descriptives du catalogue de biens.
    """
    sql_global = """
        SELECT
            COUNT(*)                                         AS total_biens,
            COUNT(*) FILTER (WHERE status = 'available')    AS disponibles,
            COUNT(*) FILTER (WHERE status = 'under_offer')  AS en_offre,
            COUNT(*) FILTER (WHERE status = 'sold')         AS vendus,
            COUNT(*) FILTER (WHERE status = 'rented')       AS loues,
            ROUND(AVG(price)::numeric, 0)                   AS prix_moyen,
            MIN(price)                                       AS prix_min,
            MAX(price)                                       AS prix_max
        FROM properties
    """
    df_global = _query_to_df(db, sql_global)

    # Répartition par type de bien (pandas)
    sql_types = """
        SELECT property_type AS type, COUNT(*) AS nb
        FROM properties
        GROUP BY property_type
        ORDER BY nb DESC
    """
    df_types = _query_to_df(db, sql_types)

    # Transactions en attente (demandes non traitées)
    sql_pending = """
        SELECT COUNT(*) AS en_attente FROM transactions WHERE status = 'pending'
    """
    df_pending = _query_to_df(db, sql_pending)

    result = df_global.iloc[0].to_dict() if not df_global.empty else {}
    result["repartition_types"] = df_types.to_dict("records") if not df_types.empty else []
    result["transactions_en_attente"] = int(df_pending.iloc[0]["en_attente"]) if not df_pending.empty else 0

    # Conversion des types numpy/Decimal pour JSON
    for k, v in result.items():
        if hasattr(v, "item"):
            result[k] = v.item()
        elif v is not None:
            try:
                result[k] = float(v)
            except (TypeError, ValueError):
                pass

    return result


# ---------------------------------------------------------------------------
# 5. Prédiction simple : délai moyen de vente par ville
# ---------------------------------------------------------------------------

def delai_vente_par_ville(db: Session) -> list[dict]:
    """
    SQL brut : calcule le délai moyen entre la création d'une annonce et
    la finalisation de la transaction. Indicateur prédictif de liquidité par zone.
    """
    sql = """
        SELECT
            p.city                                                  AS ville,
            COUNT(t.id)                                             AS nb_ventes,
            ROUND(AVG(
                EXTRACT(EPOCH FROM (t.updated_at - p.created_at)) / 86400
            )::numeric, 1)                                          AS delai_moyen_jours
        FROM transactions t
        JOIN properties p ON t.property_id = p.id
        WHERE t.status = 'completed'
        GROUP BY p.city
        HAVING COUNT(t.id) >= 1
        ORDER BY delai_moyen_jours ASC
    """
    df = _query_to_df(db, sql)
    if df.empty:
        return []
    df = df.dropna(subset=["delai_moyen_jours"])
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# 6. Prédiction du prix au m² à 3 et 6 mois par ville (numpy.polyfit)
# ---------------------------------------------------------------------------

def prediction_prix(db: Session) -> list[dict]:
    """
    Régression linéaire (numpy.polyfit deg=1) sur le prix au m² mensuel par ville.
    Prédit la tendance à 3 et 6 mois à partir du dernier point connu.

    Fiabilité :
      - "insuffisant" : 1 seul point (impossible de tracer une droite)
      - "modérée"     : 2-3 points
      - "élevée"      : 4 points et plus
    """
    sql = """
        SELECT
            p.city                                                      AS ville,
            DATE_TRUNC('month', p.created_at)::date                    AS mois,
            ROUND(AVG(p.price / NULLIF(p.surface, 0))::numeric, 0)    AS prix_m2
        FROM properties p
        WHERE p.surface IS NOT NULL
          AND p.surface > 0
        GROUP BY p.city, DATE_TRUNC('month', p.created_at)
        ORDER BY p.city, mois
    """
    df = _query_to_df(db, sql)
    if df.empty:
        return []

    df = df.dropna(subset=["prix_m2"])
    df["prix_m2"] = pd.to_numeric(df["prix_m2"], errors="coerce")

    results = []
    for ville, grp in df.groupby("ville"):
        grp = grp.reset_index(drop=True)
        y = grp["prix_m2"].astype(float).values
        prix_actuel = round(float(y[-1]), 0)
        n = len(y)

        if n < 2:
            # Un seul point : pas de régression possible, on retourne la valeur actuelle
            results.append({
                "ville": ville,
                "prix_m2_actuel": prix_actuel,
                "tendance": "stable",
                "variation_mensuelle": 0.0,
                "prediction_3m": prix_actuel,
                "prediction_6m": prix_actuel,
                "nb_points": n,
                "fiabilite": "insuffisant",
            })
            continue

        x = np.arange(n, dtype=float)
        coef = np.polyfit(x, y, 1)   # coef[0]=pente €/m²/mois, coef[1]=intercept
        slope = float(coef[0])

        # Extrapolation : dernier indice connu = x[-1]
        pred_3m = round(max(float(np.polyval(coef, x[-1] + 3)), 0), 0)
        pred_6m = round(max(float(np.polyval(coef, x[-1] + 6)), 0), 0)

        if abs(slope) < 50:
            tendance = "stable"
        elif slope > 0:
            tendance = "hausse"
        else:
            tendance = "baisse"

        results.append({
            "ville": ville,
            "prix_m2_actuel": prix_actuel,
            "tendance": tendance,
            "variation_mensuelle": round(slope, 0),
            "prediction_3m": pred_3m,
            "prediction_6m": pred_6m,
            "nb_points": n,
            "fiabilite": "élevée" if n >= 4 else "modérée",
        })

    # Trier par prédiction 6 mois décroissante (zones les plus chères en tête)
    return sorted(results, key=lambda r: r["prediction_6m"], reverse=True)
