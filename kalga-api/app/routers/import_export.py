"""
Router pour l'import/export de données (CSV)
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import csv
import io
from datetime import datetime

from ..database.repositories import MerchantRepository, ProductRepository
from ..database.repositories.category_repo import CategoryRepository

router = APIRouter(prefix="/api/import-export", tags=["import-export"])

merchant_repo = MerchantRepository()
product_repo = ProductRepository()
category_repo = CategoryRepository()


@router.get("/{merchant_phone}/products/export")
async def export_products_csv(merchant_phone: str):
    """
    Exporte tous les produits d'un marchand en CSV.
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    products = await product_repo.get_by_merchant(merchant["id"], active_only=False)

    # Créer le CSV en mémoire
    output = io.StringIO()
    writer = csv.writer(output)

    # En-têtes
    headers = [
        "code", "name", "price", "min_price", "description",
        "stock_quantity", "low_stock_threshold", "group_id",
        "variant_name", "is_available", "created_at"
    ]
    writer.writerow(headers)

    # Données
    for p in products:
        writer.writerow([
            p.get("code", ""),
            p.get("name", ""),
            p.get("price", 0),
            p.get("min_price", 0),
            p.get("description", ""),
            p.get("stock_quantity", -1),
            p.get("low_stock_threshold", 5),
            p.get("group_id", ""),
            p.get("variant_name", ""),
            1 if p.get("is_available", True) else 0,
            p.get("created_at", "")
        ])

    output.seek(0)

    # Nom du fichier
    filename = f"produits_{merchant_phone}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


class ImportResult(BaseModel):
    """Résultat de l'import"""
    success: bool
    imported: int
    errors: List[str]
    skipped: int


@router.post("/{merchant_phone}/products/import")
async def import_products_csv(
    merchant_phone: str,
    file: UploadFile = File(...)
):
    """
    Importe des produits depuis un fichier CSV.

    Format attendu:
    - name (requis): Nom du produit
    - price (requis): Prix affiché
    - min_price (requis): Prix minimum
    - description (optionnel): Description
    - stock_quantity (optionnel): Quantité en stock (-1 = illimité)
    - low_stock_threshold (optionnel): Seuil d'alerte stock bas
    """
    merchant = await merchant_repo.get_by_phone(merchant_phone)
    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    # Vérifier le type de fichier
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Le fichier doit être au format CSV")

    # Lire le contenu
    content = await file.read()

    try:
        # Décoder (UTF-8 avec fallback sur latin-1)
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')

        # Parser le CSV
        reader = csv.DictReader(io.StringIO(text))

        imported = 0
        errors = []
        skipped = 0

        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
            try:
                # Valider les champs requis
                name = row.get('name', '').strip()
                if not name:
                    errors.append(f"Ligne {row_num}: Nom manquant")
                    skipped += 1
                    continue

                # Prix
                try:
                    price = float(row.get('price', 0))
                except ValueError:
                    errors.append(f"Ligne {row_num}: Prix invalide")
                    skipped += 1
                    continue

                try:
                    min_price = float(row.get('min_price', price))
                except ValueError:
                    min_price = price

                if min_price > price:
                    min_price = price

                # Optionnels
                description = row.get('description', '').strip() or None

                try:
                    stock_quantity = int(row.get('stock_quantity', -1))
                except ValueError:
                    stock_quantity = -1

                try:
                    low_stock_threshold = int(row.get('low_stock_threshold', 5))
                except ValueError:
                    low_stock_threshold = 5

                group_id = row.get('group_id', '').strip() or None
                variant_name = row.get('variant_name', '').strip() or None

                # Créer le produit
                await product_repo.create(
                    merchant_id=merchant["id"],
                    name=name,
                    price=price,
                    min_price=min_price,
                    description=description,
                    stock_quantity=stock_quantity,
                    low_stock_threshold=low_stock_threshold,
                    group_id=group_id,
                    variant_name=variant_name
                )
                imported += 1

            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")
                skipped += 1

        return ImportResult(
            success=imported > 0,
            imported=imported,
            errors=errors[:10],  # Limiter à 10 erreurs max
            skipped=skipped
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de parsing CSV: {str(e)}")


@router.get("/{merchant_phone}/products/template")
async def get_import_template():
    """
    Télécharge un template CSV pour l'import de produits.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # En-têtes
    headers = [
        "name", "price", "min_price", "description",
        "stock_quantity", "low_stock_threshold", "group_id", "variant_name"
    ]
    writer.writerow(headers)

    # Exemple
    writer.writerow([
        "iPhone 14 Pro", "650000", "600000", "Smartphone Apple dernière génération",
        "10", "3", "", ""
    ])
    writer.writerow([
        "T-shirt Blanc M", "15000", "12000", "100% coton",
        "50", "10", "TSHIRT-BLANC", "Taille M"
    ])
    writer.writerow([
        "T-shirt Blanc L", "15000", "12000", "100% coton",
        "30", "10", "TSHIRT-BLANC", "Taille L"
    ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template_import_produits.csv"}
    )
