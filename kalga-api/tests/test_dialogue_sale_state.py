"""Tests de la machine à états de vente."""
from app.services.dialogue.sale_state import SaleState, DB_STATUS, from_db_status


def test_all_states_map_to_existing_db_statuses():
    # Aucune migration : on retombe sur les statuts DB actuels
    assert set(DB_STATUS) == set(SaleState)
    assert set(DB_STATUS.values()) <= {
        "active", "negotiating", "agreed", "pending_delivery",
        "pending_pickup", "completed", "ended",
    }


def test_db_mapping_values():
    assert DB_STATUS[SaleState.ACCUEIL] == "active"
    assert DB_STATUS[SaleState.RENSEIGNEMENT] == "active"
    assert DB_STATUS[SaleState.NEGOCIATION] == "negotiating"
    assert DB_STATUS[SaleState.CONCLUSION] == "agreed"
    assert DB_STATUS[SaleState.LOGISTIQUE_LIVRAISON] == "pending_delivery"
    assert DB_STATUS[SaleState.LOGISTIQUE_RETRAIT] == "pending_pickup"
    assert DB_STATUS[SaleState.APRES_VENTE] == "completed"
    assert DB_STATUS[SaleState.FIN] == "ended"


def test_from_db_status_active_first_message_is_accueil():
    assert from_db_status("active", message_count=1) == SaleState.ACCUEIL


def test_from_db_status_active_later_is_renseignement():
    assert from_db_status("active", message_count=5) == SaleState.RENSEIGNEMENT


def test_from_db_status_known_statuses():
    assert from_db_status("negotiating", 9) == SaleState.NEGOCIATION
    assert from_db_status("agreed", 9) == SaleState.CONCLUSION
    assert from_db_status("pending_delivery", 9) == SaleState.LOGISTIQUE_LIVRAISON
    assert from_db_status("pending_pickup", 9) == SaleState.LOGISTIQUE_RETRAIT
    assert from_db_status("completed", 9) == SaleState.APRES_VENTE
    assert from_db_status("ended", 9) == SaleState.FIN


def test_from_db_status_unknown_defaults_to_renseignement():
    assert from_db_status("abandoned", 9) == SaleState.RENSEIGNEMENT
