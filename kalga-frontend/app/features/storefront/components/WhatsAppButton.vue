<!--
  Bouton "Discuter sur WhatsApp" — ouvre wa.me avec un message pré-rempli.
-->

<script setup lang="ts">
import { MessageCircle } from 'lucide-vue-next'

import { buildWhatsAppLink } from '@/utils/whatsapp'

interface Props {
  /** Numéro du marchand (chiffres uniquement, indicatif inclus) */
  phone: string
  /** Code produit pour pré-remplir le message (ex: "#K001") */
  productCode?: string
  /** Variant de style : 'primary' (forest/gold) ou 'outline' */
  variant?: 'primary' | 'outline'
}

const props = withDefaults(defineProps<Props>(), {
  productCode: '',
  variant: 'primary',
})

const { t } = useI18n()

const href = computed(() => {
  const text = props.productCode
    ? t('storefront.whatsappPrefillProduct', { code: props.productCode })
    : t('storefront.whatsappPrefillGeneric')
  return buildWhatsAppLink(props.phone, text)
})

const classes = computed(() =>
  props.variant === 'primary'
    ? 'bg-primary text-warning hover:bg-primary/90'
    : 'border border-primary text-primary hover:bg-primary/5',
)
</script>

<template>
  <a
    :href="href"
    target="_blank"
    rel="noopener noreferrer"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-md px-5 py-2.5 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      classes,
    ]"
  >
    <MessageCircle class="h-4 w-4" aria-hidden="true" />
    {{ $t('storefront.chatOnWhatsApp') }}
  </a>
</template>
