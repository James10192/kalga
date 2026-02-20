"""
Router pour les statistiques et analytics
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
from typing import Optional

from ..database.repositories import get_stats_repository, MerchantRepository

router = APIRouter(prefix="/api/stats", tags=["statistics"])

stats_repo = get_stats_repository()
merchant_repo = MerchantRepository()


@router.get("/{merchant_phone}/summary")
async def get_summary_stats(
    merchant_phone: str,
    days: int = Query(30, ge=1, le=365, description="Nombre de jours")
):
    """
    Récupère un résumé des statistiques sur une période.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    summary = await stats_repo.get_summary_stats(merchant["id"], days)
    conversion = await stats_repo.get_conversion_rate(merchant["id"], days)

    return {
        "merchant_id": merchant["id"],
        "merchant_phone": merchant_phone,
        **summary,
        **conversion
    }


@router.get("/{merchant_phone}/daily")
async def get_daily_stats(
    merchant_phone: str,
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    days: int = Query(7, ge=1, le=90, description="Nombre de jours si pas de dates")
):
    """
    Récupère les statistiques quotidiennes pour les graphiques.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    # Parser les dates ou utiliser les jours par défaut
    if start_date and end_date:
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide")
    else:
        end = date.today()
        start = end - timedelta(days=days)

    stats = await stats_repo.get_stats_range(merchant["id"], start, end)

    # Remplir les jours manquants avec des zéros
    date_range = []
    current = start
    while current <= end:
        date_range.append(current.isoformat())
        current += timedelta(days=1)

    # Créer un dictionnaire des stats existantes
    stats_dict = {s["date"]: s for s in stats}

    # Remplir les données
    result = []
    for d in date_range:
        if d in stats_dict:
            result.append(stats_dict[d])
        else:
            result.append({
                "date": d,
                "conversations_count": 0,
                "messages_count": 0,
                "sales_count": 0,
                "revenue": 0,
                "unique_clients": 0
            })

    return {
        "merchant_id": merchant["id"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "data": result
    }


@router.get("/{merchant_phone}/top-products")
async def get_top_products(
    merchant_phone: str,
    limit: int = Query(5, ge=1, le=20, description="Nombre de produits")
):
    """
    Récupère les produits les plus populaires.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    products = await stats_repo.get_top_products(merchant["id"], limit)

    return {
        "merchant_id": merchant["id"],
        "products": products
    }


@router.get("/{merchant_phone}/hourly-activity")
async def get_hourly_activity(
    merchant_phone: str,
    days: int = Query(7, ge=1, le=30, description="Nombre de jours")
):
    """
    Récupère l'activité par heure de la journée.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    activity = await stats_repo.get_hourly_activity(merchant["id"], days)

    # S'assurer que toutes les heures sont présentes
    hour_data = {h: 0 for h in range(24)}
    for item in activity:
        hour_data[item["hour"]] = item["count"]

    return {
        "merchant_id": merchant["id"],
        "period_days": days,
        "data": [{"hour": h, "count": c} for h, c in hour_data.items()]
    }


@router.get("/{merchant_phone}/realtime")
async def get_realtime_stats(merchant_phone: str):
    """
    Récupère les statistiques en temps réel (aujourd'hui).
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    today_stats = await stats_repo.get_or_create_daily_stats(merchant["id"])

    return {
        "merchant_id": merchant["id"],
        "date": date.today().isoformat(),
        "conversations_today": today_stats.get("conversations_count", 0),
        "messages_today": today_stats.get("messages_count", 0),
        "sales_today": today_stats.get("sales_count", 0),
        "revenue_today": today_stats.get("revenue", 0)
    }
