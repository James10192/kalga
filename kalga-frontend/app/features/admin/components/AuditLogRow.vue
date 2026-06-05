<!--
  Ligne du journal d'audit admin.
-->

<script setup lang="ts">
import { ScrollText } from 'lucide-vue-next'

import { formatDateTime, initialsFrom } from '@/utils/format'
import type { AuditLogEntry } from '@/types/domain'

interface Props {
  entry: AuditLogEntry
}

const props = defineProps<Props>()
const { locale } = useI18n()

const createdAt = computed(() =>
  formatDateTime(props.entry.created_at, locale.value === 'en' ? 'en-US' : 'fr-FR'),
)

const adminInitials = computed(() => initialsFrom(props.entry.admin_email))
</script>

<template>
  <article
    class="grid grid-cols-[auto_1fr_auto] items-start gap-3 rounded-lg border border-border bg-card p-4"
  >
    <div
      class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-forest/10 text-brand-forest"
      aria-hidden="true"
    >
      <ScrollText class="h-4 w-4" aria-hidden="true" />
    </div>

    <div class="min-w-0">
      <p class="font-medium text-foreground">{{ entry.action }}</p>
      <p v-if="entry.target_type" class="text-xs text-muted-foreground">
        {{ entry.target_type }}
        <span v-if="entry.target_id">#{{ entry.target_id }}</span>
      </p>
      <p v-if="entry.admin_email" class="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground">
        <span
          class="inline-flex h-4 w-4 items-center justify-center rounded-full bg-brand-forest text-[10px] font-semibold text-brand-gold"
          aria-hidden="true"
        >
          {{ adminInitials }}
        </span>
        {{ entry.admin_email }}
      </p>
    </div>

    <time class="whitespace-nowrap text-xs text-muted-foreground">{{ createdAt }}</time>
  </article>
</template>
