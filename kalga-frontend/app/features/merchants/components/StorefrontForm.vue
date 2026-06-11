<!--
  Ma Vitrine — personnalisation de la boutique en ligne du marchand.
  Porté fidèlement depuis dashboard/index.html (#section-settings « Ma Vitrine »)
  + app.js (saveStorefrontProfile).

  Champs texte (business_name, tagline, about) → PUT /merchants/{id}.
  Images (bannière, logo) → POST /merchants/{id}/upload-image (multipart), via la
  route serveur dédiée. Aperçu des images existantes via /uploads/{path}.
-->

<script setup lang="ts">
import { Image as ImageIcon, Loader2, Upload } from 'lucide-vue-next'

import {
  useUpdateMerchantProfile,
  useUploadMerchantImage,
} from '@/features/merchants/composables/useMerchants'
import type { Merchant } from '@/features/merchants/types'

interface Props {
  merchant: Merchant
}

const props = defineProps<Props>()

const { t } = useI18n()
const { push } = useToast()
const { mutateAsync: updateProfile } = useUpdateMerchantProfile()
const { mutateAsync: uploadImage } = useUploadMerchantImage()

const form = reactive({
  business_name: props.merchant.business_name ?? '',
  tagline: props.merchant.tagline ?? '',
  about: props.merchant.about ?? '',
})

const bannerFile = ref<File | null>(null)
const logoFile = ref<File | null>(null)
const bannerPreview = ref<string | null>(
  props.merchant.banner_path ? `/uploads/${props.merchant.banner_path}` : null,
)
const logoPreview = ref<string | null>(
  props.merchant.logo_path ? `/uploads/${props.merchant.logo_path}` : null,
)
const saving = ref(false)

function onSelectImage(event: Event, kind: 'banner' | 'logo'): void {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null
  if (!file) return
  const url = URL.createObjectURL(file)
  if (kind === 'banner') {
    bannerFile.value = file
    bannerPreview.value = url
  } else {
    logoFile.value = file
    logoPreview.value = url
  }
}

async function uploadIfSelected(file: File | null, imageType: 'banner' | 'logo'): Promise<void> {
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  formData.append('image_type', imageType)
  await uploadImage({ id: props.merchant.id, formData })
}

async function save(): Promise<void> {
  saving.value = true
  try {
    await updateProfile({
      id: props.merchant.id,
      data: {
        business_name: form.business_name,
        tagline: form.tagline,
        about: form.about,
      },
    })
    await uploadIfSelected(bannerFile.value, 'banner')
    await uploadIfSelected(logoFile.value, 'logo')
    bannerFile.value = null
    logoFile.value = null
    push.success(t('settings.storefrontSaved'))
  } catch (error) {
    push.error(extractApiErrorMessage(error, t('settings.saveError')))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="save">
    <p class="text-sm text-muted-foreground">{{ $t('settings.storefrontIntro') }}</p>

    <div>
      <label for="sf-business" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.storefrontBusinessName') }}
      </label>
      <input
        id="sf-business"
        v-model="form.business_name"
        type="text"
        class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
    </div>

    <div>
      <label for="sf-tagline" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.storefrontTagline') }}
      </label>
      <input
        id="sf-tagline"
        v-model="form.tagline"
        type="text"
        maxlength="120"
        :placeholder="$t('settings.storefrontTaglinePlaceholder')"
        class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
    </div>

    <div>
      <label for="sf-about" class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.storefrontAbout') }}
      </label>
      <textarea
        id="sf-about"
        v-model="form.about"
        rows="3"
        maxlength="500"
        :placeholder="$t('settings.storefrontAboutPlaceholder')"
        class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
    </div>

    <!-- Bannière -->
    <div>
      <span class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.storefrontBanner') }}
      </span>
      <div class="flex items-center gap-3">
        <div
          class="flex h-20 w-32 shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-muted text-muted-foreground"
        >
          <img v-if="bannerPreview" :src="bannerPreview" alt="" class="h-full w-full object-cover">
          <ImageIcon v-else class="h-6 w-6" aria-hidden="true" />
        </div>
        <label
          class="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted"
        >
          <Upload class="h-4 w-4" aria-hidden="true" />
          {{ $t('settings.chooseImage') }}
          <input type="file" accept="image/*" class="hidden" @change="onSelectImage($event, 'banner')">
        </label>
      </div>
    </div>

    <!-- Logo -->
    <div>
      <span class="mb-1 block text-sm font-medium text-foreground">
        {{ $t('settings.storefrontLogo') }}
      </span>
      <div class="flex items-center gap-3">
        <div
          class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-muted text-muted-foreground"
        >
          <img v-if="logoPreview" :src="logoPreview" alt="" class="h-full w-full object-cover">
          <ImageIcon v-else class="h-5 w-5" aria-hidden="true" />
        </div>
        <label
          class="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-muted"
        >
          <Upload class="h-4 w-4" aria-hidden="true" />
          {{ $t('settings.chooseImage') }}
          <input type="file" accept="image/*" class="hidden" @change="onSelectImage($event, 'logo')">
        </label>
      </div>
    </div>

    <button
      type="submit"
      :disabled="saving"
      class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition hover:bg-primary-hi disabled:cursor-not-allowed disabled:opacity-60"
    >
      <Loader2 v-if="saving" class="h-4 w-4 animate-spin" aria-hidden="true" />
      {{ $t('common.save') }}
    </button>
  </form>
</template>
