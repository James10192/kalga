<!--
  Bulle d'un message dans le thread.
  - Client : aligné à gauche, fond muted
  - Bot/marchand : aligné à droite, fond primary
-->

<script setup lang="ts">
import { formatDateTime } from '@/utils/format'
import type { Message } from '../types'

interface Props {
  message: Message
}

const props = defineProps<Props>()
const { locale } = useI18n()

const timeLabel = computed(() =>
  formatDateTime(props.message.created_at, locale.value === 'en' ? 'en-US' : 'fr-FR'),
)
</script>

<template>
  <div
    :class="[
      'flex w-full',
      message.is_from_client ? 'justify-start' : 'justify-end',
    ]"
  >
    <div
      :class="[
        'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
        message.is_from_client
          ? 'rounded-tl-sm bg-muted text-foreground'
          : 'rounded-tr-sm bg-primary text-warning',
      ]"
    >
      <p class="whitespace-pre-wrap break-words">{{ message.content }}</p>
      <p
        :class="[
          'mt-1 text-[10px]',
          message.is_from_client ? 'text-muted-foreground' : 'text-warning/70',
        ]"
      >
        {{ timeLabel }}
      </p>
    </div>
  </div>
</template>
