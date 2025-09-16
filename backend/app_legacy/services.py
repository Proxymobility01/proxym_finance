# app_legacy/services.py
from typing import Optional, Dict, Any
from django.db import connection


def fetch_association_summary(association_id: int) -> Optional[Dict[str, Any]]:
    """
    Return a dict:
    {
      "association_id": int,
      "validated_user_id": int | None,
      "moto_valide_id": int | None,
      "nom": str | None,
      "prenom": str | None,
      "vin": str | None
    }
    or None if not found.

    Assumes validated_users has columns: nom, prenom
            moto_valides has column: vin
    """
    sql = """
        SELECT a.id                AS association_id,
               a.validated_user_id AS validated_user_id,
               a.moto_valide_id    AS moto_valide_id,
               vu.nom              AS nom,
               vu.prenom           AS prenom,
               mv.vin              AS vin
        FROM association_user_motos a
        LEFT JOIN validated_users vu ON vu.id = a.validated_user_id
        LEFT JOIN motos_valides mv    ON mv.id = a.moto_valide_id
        WHERE a.id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [association_id])
        row = cursor.fetchone()

    if not row:
        return None

    columns = [
        "association_id",
        "validated_user_id",
        "moto_valide_id",
        "nom",
        "prenom",
        "vin",
    ]
    return dict(zip(columns, row))
