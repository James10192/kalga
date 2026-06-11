<!--
  Création d'un nouveau produit.
  Référence : ARCHITECTURE_FRONTEND.md sections 9.1 + 9.4
-->

<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'

import ProductForm from '@/features/products/components/ProductForm.vue'
import { useCreateProduct } from '@/features/products/composables/useProducts'
import type { ProductCreateInput } from '@/features/products/types'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const { user } = useAuth()
const { push } = useToast()
const router = useRouter()

const merchantId = computed(() => user.value?.merchant_id ?? 0)
const { mutateAsync, isPending } = useCreateProduct(merchantId)

useHead({ title: t('products.createNew') })

async function handleSubmit(data: ProductCreateInput): Promise<void> {
  try {
    const created = await mutateAsync(data)
    push.success(t('products.createSuccess', { code: created.code }))
    // Pas de page détail produit (KALGA n'édite pas un produit) → retour à la liste.
    await router.push(ROUTES.dashboard.products)
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('products.createError')))
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <NuxtLink
      :to="ROUTES.dashboard.products"
      class="inline-flex items-center gap-1 text-sm text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <ArrowLeft class="h-4 w-4" aria-hidden="true" />
      {{ $t('products.backToList') }}
    </NuxtLink>

    <header>
      <h1 class="font-display text-2xl font-semibold text-primary">
        {{ $t('products.createTitle') }}
      </h1>
      <p class="text-sm text-muted-foreground">{{ $t('products.createSubtitle') }}</p>
    </header>

    <div class="rounded-lg border border-border bg-card p-6">
      <ProductForm
        :loading="isPending"
        submit-label-i18n-key="products.createNew"
        @submit="handleSubmit"
      />
    </div>
  </div>
</template>
