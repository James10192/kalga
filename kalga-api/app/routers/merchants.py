from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from ..database import get_db
from ..database.repositories.merchant_repo import get_merchant_repository
from ..models.schemas import MerchantCreate, Merchant, validate_phone_number
from typing import List, Optional
from pydantic import BaseModel
import os
import uuid

router = APIRouter(prefix="/merchants", tags=["Marchands"])

# Dossier uploads
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


class LocationUpdate(BaseModel):
    """Mise à jour de la localisation du marchand"""
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MerchantUpdate(BaseModel):
    """Mise à jour des infos marchand"""
    name: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    about: Optional[str] = None
    tagline: Optional[str] = None


class PhoneUpdate(BaseModel):
    """Correction du numéro de téléphone après détection du vrai numéro WhatsApp"""
    phone: str

# Constantes de pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.post("/", response_model=dict)
async def create_merchant(merchant: MerchantCreate):
    """
    Crée un nouveau marchand

    - **name**: Nom du marchand
    - **phone**: Numéro WhatsApp (format: 22500000000)
    - **business_name**: Nom du commerce (optionnel)
    """
    db = await get_db()

    # Vérifier si le numéro existe déjà
    existing = await db.get_merchant_by_phone(merchant.phone)
    if existing:
        raise HTTPException(status_code=400, detail="Ce numéro WhatsApp est déjà enregistré")

    result = await db.create_merchant(
        name=merchant.name,
        phone=merchant.phone,
        business_name=merchant.business_name
    )

    return {
        "success": True,
        "message": f"Marchand {result['name']} créé avec succès",
        "merchant": result
    }


@router.get("/")
async def list_merchants(
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Éléments par page")
):
    """Liste tous les marchands actifs avec pagination"""
    db = await get_db()
    merchants = await db.get_all_merchants()

    # Pagination manuelle (simple pour SQLite)
    total = len(merchants)
    start = (page - 1) * limit
    end = start + limit
    paginated = merchants[start:end]

    return {
        "merchants": paginated,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit  # Arrondi supérieur
    }


@router.get("/{phone}")
async def get_merchant(phone: str):
    """Récupère un marchand par son numéro WhatsApp"""
    db = await get_db()

    # Normaliser le numéro pour la recherche
    try:
        normalized_phone = validate_phone_number(phone)
    except ValueError:
        normalized_phone = phone  # Si invalide, essayer tel quel

    # Chercher avec le numéro normalisé d'abord, puis avec le numéro original
    merchant = await db.get_merchant_by_phone(normalized_phone)
    if not merchant:
        merchant = await db.get_merchant_by_phone(phone)

    if not merchant:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    return merchant


@router.get("/{merchant_id}/products")
async def get_merchant_products(
    merchant_id: int,
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Éléments par page")
):
    """Liste les produits d'un marchand avec pagination"""
    db = await get_db()
    products = await db.get_products_by_merchant(merchant_id)

    # Pagination
    total = len(products)
    start = (page - 1) * limit
    end = start + limit
    paginated = products[start:end]

    return {
        "merchant_id": merchant_id,
        "products": paginated,
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit
    }


@router.put("/{merchant_id}/location")
async def update_merchant_location(merchant_id: int, location: LocationUpdate):
    """
    Met à jour la localisation du marchand

    - **address**: Adresse textuelle (ex: "Cocody, Abidjan")
    - **latitude**: Latitude GPS
    - **longitude**: Longitude GPS
    """
    db = await get_db()

    success = await db.update_merchant_location(
        merchant_id=merchant_id,
        address=location.address,
        latitude=location.latitude,
        longitude=location.longitude
    )

    if not success:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

    return {
        "success": True,
        "message": "Localisation mise à jour"
    }


@router.put("/{merchant_id}/phone")
async def update_merchant_phone(merchant_id: int, update: PhoneUpdate):
    """
    Corrige le numéro de téléphone du marchand.
    Appelé automatiquement quand le vrai numéro WhatsApp est détecté après scan QR.
    """
    db = await get_db()

    # Vérifier qu'un autre marchand n'utilise pas déjà ce numéro
    existing = await db.get_merchant_by_phone(update.phone)
    if existing and existing["id"] != merchant_id:
        raise HTTPException(
            status_code=409,
            detail=f"Ce numéro est déjà utilisé par un autre marchand (id={existing['id']})"
        )

    success = await db.update_merchant(merchant_id, phone=update.phone)
    if not success:
        raise HTTPException(status_code=404, detail="Marchand non trouvé")

    return {
        "success": True,
        "message": f"Numéro mis à jour: {update.phone}",
        "phone": update.phone
    }


@router.put("/{merchant_id}")
async def update_merchant(merchant_id: int, update: MerchantUpdate):
    """Met à jour les informations du marchand"""
    db = await get_db()

    update_data = {k: v for k, v in update.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

    success = await db.update_merchant(merchant_id, **update_data)

    if not success:
        raise HTTPException(status_code=400, detail="Erreur lors de la mise à jour")

    return {
        "success": True,
        "message": "Marchand mis à jour"
    }


@router.post("/{merchant_id}/upload-image")
async def upload_merchant_image(
    merchant_id: int,
    image_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload une image pour le marchand (logo ou bannière).
    image_type: 'logo' ou 'banner'
    """
    if image_type not in ("logo", "banner"):
        raise HTTPException(status_code=400, detail="image_type doit être 'logo' ou 'banner'")

    # Vérifier le type de fichier
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format d'image non supporté (JPG, PNG, WebP, GIF)")

    # Limiter la taille (5 MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 5 MB)")

    # Générer un nom unique
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{image_type}_{merchant_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)

    # Sauvegarder le fichier
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)

    # Mettre à jour la DB
    merchant_repo = get_merchant_repository()
    field = "logo_path" if image_type == "logo" else "banner_path"

    # Supprimer l'ancienne image si elle existe
    merchant = await merchant_repo.get_by_id(merchant_id)
    if merchant and merchant.get(field):
        old_path = os.path.join(UPLOADS_DIR, merchant[field])
        if os.path.exists(old_path):
            os.remove(old_path)

    await merchant_repo.update(merchant_id, **{field: filename})

    return {
        "success": True,
        "message": f"{image_type.capitalize()} mis à jour",
        "url": f"/uploads/{filename}"
    }
