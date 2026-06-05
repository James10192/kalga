<!--
  Détail / édition d'un produit existant.
  Référence : ARCHITECTURE_FRONTEND.md sections 9.1 + 9.4
-->

<script setup lang="ts">
import { ArrowLeft, Loader2, Trash2 } from 'lucide-vue-next'

import ProductForm from '@/features/products/components/ProductForm.vue'
import {
  useDeleteProduct,
  useProduct,
  useUpdateProduct,
} from '@/features/products/composables/useProducts'
import type { ProductUpdateInput } from '@/features/products/types'
import { ROUTES } from '@/utils/routes'

definePageMeta({ layout: 'dashboard' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { push } = useToast()

const productId = computed(() => {
  const raw = route.params.id
  const id = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(id) && id > 0 ? id : 0
})

const { data: product, isLoading, isError } = useProduct(productId)
const { mutateAsync: updateMutate, isPending: updating } = useUpdateProduct()
const { mutateAsync: deleteMutate, isPending: deleting } = useDeleteProduct()

useHead({ title: () => product.value?.name ?? t('common.loading') })

async function handleUpdate(data: ProductUpdateInput): Promise<void> {
  try {
    await updateMutate({ id: productId.value, data })
    push.success(t('products.updateSuccess'))
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('products.updateError')))
  }
}

async function handleDelete(): Promise<void> {
  if (!product.value) return
  if (!window.confirm(t('products.deleteConfirm', { name: product.value.name }))) {
    return
  }

  try {
    await deleteMutate(productId.value)
    push.success(t('products.deleteSuccess'))
    await router.push(ROUTES.dashboard.products)
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('products.deleteError')))
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

    <!-- Loading -->
    <div
      v-if="isLoading"
      class="flex items-center justify-center rounded-lg border border-border bg-card py-16"
    >
      <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
      <span class="ml-3 text-sm text-muted-foreground">{{ $t('common.loading') }}</span>
    </div>

    <!-- Erreur -->
    <div
      v-else-if="isError || !product"
      role="alert"
      class="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center"
    >
      <p class="text-sm text-destructive">{{ $t('products.loadError') }}</p>
    </div>

    <!-- Édition -->
    <template v-else>
      <header class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="font-serif text-2xl font-semibold text-brand-forest">{{ product.name }}</h1>
          <p class="text-sm text-muted-foreground">
            {{ $t('products.code') }} <strong>{{ product.code }}</strong>
          </p>
        </div>

        <button
          type="button"
          :disabled="deleting"
          class="inline-flex items-center gap-2 rounded-md border border-destructive/40 bg-card px-3 py-2 text-sm font-medium text-destructive transition hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive disabled:cursor-not-allowed disabled:opacity-60"
          @click="handleDelete"
        >
          <Trash2 v-if="!deleting" class="h-4 w-4" aria-hidden="true" />
          <Loader2 v-else class="h-4 w-4 animate-spin" aria-hidden="true" />
          {{ $t('common.delete') }}
        </button>
      </header>

      <div class="rounded-lg border border-border bg-card p-6">
        <ProductForm
          :initial="product"
          :loading="updating"
          submit-label-i18n-key="common.save"
          @submit="handleUpdate"
        />
      </div>
    </template>
  </div>
</template>
