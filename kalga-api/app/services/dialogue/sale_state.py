"""
Étage ③ — Machine à états de vente (spec §6).

La méthode de vente du marchand, formalisée. Les états internes se projettent
sur les statuts DB EXISTANTS (aucune migration, le dashboard reste compatible).
"""
from enum import Enum


class SaleState(str, Enum):
    ACCUEIL = "accueil"
    RENSEIGNEMENT = "renseignement"
    NEGOCIATION = "negociation"
    CONCLUSION = "conclusion"
    LOGISTIQUE_LIVRAISON = "logistique_livraison"
    LOGISTIQUE_RETRAIT = "logistique_retrait"
    APRES_VENTE = "apres_vente"
    FIN = "fin"


DB_STATUS = {
    SaleState.ACCUEIL: "active",
    SaleState.RENSEIGNEMENT: "active",
    SaleState.NEGOCIATION: "negotiating",
    SaleState.CONCLUSION: "agreed",
    SaleState.LOGISTIQUE_LIVRAISON: "pending_delivery",
    SaleState.LOGISTIQUE_RETRAIT: "pending_pickup",
    SaleState.APRES_VENTE: "completed",
    SaleState.FIN: "ended",
}

_FROM_DB = {
    "negotiating": SaleState.NEGOCIATION,
    "agreed": SaleState.CONCLUSION,
    "pending_delivery": SaleState.LOGISTIQUE_LIVRAISON,
    "pending_pickup": SaleState.LOGISTIQUE_RETRAIT,
    "completed": SaleState.APRES_VENTE,
    "ended": SaleState.FIN,
}


def from_db_status(status: str, message_count: int) -> SaleState:
    """Statut DB → état interne. « active » se raffine selon l'avancement."""
    if status == "active":
        return SaleState.ACCUEIL if message_count <= 1 else SaleState.RENSEIGNEMENT
    return _FROM_DB.get(status, SaleState.RENSEIGNEMENT)
