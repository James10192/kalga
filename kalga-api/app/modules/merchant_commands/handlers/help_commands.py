"""
Handler pour les commandes d'aide et d'information
Gère: aide, liste des produits, suppression
"""
from typing import Any
import re
import logging

from .base import BaseHandler
from ..schemas import CommandResponse, CommandAction

logger = logging.getLogger("kalga.handlers.help")


class HelpCommandsHandler(BaseHandler):
    """Gère les commandes d'aide et d'information"""

    async def handle(self, *args, **kwargs) -> CommandResponse:
        """Non utilisé - ce handler a des méthodes spécifiques"""
        raise NotImplementedError("Utilisez les méthodes spécifiques")

    async def handle_help(self) -> CommandResponse:
        """Affiche l'aide des commandes disponibles"""
        return self._response(
            """📋 *Commandes disponibles:*

*PRODUITS*
• *produit* - Ajouter un nouveau produit
• *modifier #K001* - Modifier un produit existant
• *variante #K001* - Ajouter une couleur/taille
• *mes produits* - Voir tous tes produits
• *supprimer #K001* - Retirer un produit

*VENTES*
• *!ok* ou *!livré* - Marquer une vente comme terminée
• *!annuler* - Annuler une vente en attente

Pour ajouter un produit, écris *produit* et suis les étapes!""",
            CommandAction.HELP
        )

    async def handle_list_products(
        self,
        merchant: dict,
        db: Any
    ) -> CommandResponse:
        """Liste les produits du marchand, en regroupant les variantes"""
        products = await db.get_products_by_merchant(merchant['id'])

        if not products:
            return self._response(
                "Tu n'as pas encore de produits. Écris *produit* pour en ajouter un!",
                CommandAction.LIST_EMPTY
            )

        available = [p for p in products if p.get('is_available', True)]

        # Regrouper par group_id
        groups = {}
        standalone = []
        for p in available:
            gid = p.get('group_id')
            if gid:
                if gid not in groups:
                    groups[gid] = []
                groups[gid].append(p)
            else:
                standalone.append(p)

        lines = []

        # Produits avec variantes
        for gid, variants in groups.items():
            # Le premier produit du groupe (le parent) donne le code principal
            parent = min(variants, key=lambda v: v['id'])
            variant_names = [v.get('variant_name', '') for v in variants if v.get('variant_name')]
            if variant_names:
                variants_str = ", ".join(variant_names)
                lines.append(
                    f"• *{parent['code']}* - {parent['name'].split(' - ')[0]} ({parent['price']:,.0f} F)\n"
                    f"  🎨 {len(variants)} variantes: {variants_str}"
                )
            else:
                lines.append(f"• *{parent['code']}* - {parent['name']} ({parent['price']:,.0f} F)")

        # Produits sans variantes
        for p in standalone:
            lines.append(f"• *{p['code']}* - {p['name']} ({p['price']:,.0f} F)")

        product_list = "\n".join(lines)

        return self._response(
            f"📦 *Tes produits:*\n\n{product_list}\n\nPour ajouter: écris *produit*",
            CommandAction.LIST
        )

    async def handle_delete_product(
        self,
        message: str,
        merchant: dict,
        db: Any
    ) -> CommandResponse:
        """Supprime (désactive) un produit"""
        # Extraire le code produit
        code_match = re.search(r'#K\d{3}', message.upper())

        if not code_match:
            return self._error(
                "Indique le code du produit à supprimer.\n"
                "Exemple: *supprimer #K001*"
            )

        code = code_match.group(0)
        product = await db.get_product_by_code(code)

        if not product:
            return self._error(f"Produit {code} non trouvé.")

        if product['merchant_id'] != merchant['id']:
            return self._error("Ce produit ne t'appartient pas.")

        # Désactiver le produit
        await db.deactivate_product(code)

        logger.info(f"Produit supprimé: {code} par merchant={merchant['phone']}")

        return self._response(
            f"✅ Produit {code} ({product['name']}) supprimé!",
            CommandAction.DELETE
        )
