<!--
  Country selector custom + input numéro WhatsApp.
  Port 1:1 depuis dashboard/index.html ll. 68-158 + style.css ll. 458-528.

  V-model : retourne `{ countryCode, localNumber }` où countryCode est
  l'indicatif sans `+` (ex: "225") et localNumber le numéro local saisi.
  Pour récupérer le numéro complet international : `${countryCode}${localNumber}`.
-->

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import { onClickOutside } from '@vueuse/core'

import { WHATSAPP_COUNTRIES, WHATSAPP_COUNTRY_DEFAULT } from '@/utils/constants'

export interface CountryPhoneValue {
  readonly countryCode: string
  readonly localNumber: string
}

interface Props {
  modelValue: CountryPhoneValue
  /** Désactive le composant pendant la soumission */
  disabled?: boolean
  /** Affiche un état d'erreur (border rouge + aria-invalid) */
  invalid?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  invalid: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: CountryPhoneValue]
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

onClickOutside(root, () => {
  open.value = false
})

const selectedCountry = computed(
  () =>
    WHATSAPP_COUNTRIES.find((c) => c.code === props.modelValue.countryCode) ??
    WHATSAPP_COUNTRY_DEFAULT,
)

function selectCountry(code: string): void {
  emit('update:modelValue', {
    countryCode: code,
    localNumber: props.modelValue.localNumber,
  })
  open.value = false
}

function handlePhoneInput(event: Event): void {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', {
    countryCode: props.modelValue.countryCode,
    localNumber: target.value,
  })
}

function toggleDropdown(): void {
  if (!props.disabled) open.value = !open.value
}
</script>

<template>
  <div ref="root" class="relative flex">
    <!-- Trigger country selector -->
    <button
      type="button"
      :disabled="disabled"
      :aria-expanded="open"
      :aria-haspopup="'listbox'"
      :aria-label="$t('auth.merchant.selectCountry')"
      class="inline-flex h-[50px] min-w-[92px] shrink-0 select-none items-center gap-1.5 rounded-l-[10px] border-y-[1.5px] border-l-[1.5px] border-white/[0.07] bg-[#0e1812] px-3 transition hover:border-white/[0.12] hover:bg-[#131f17] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
      :class="open && 'border-primary'"
      @click="toggleDropdown"
    >
      <span class="text-lg" aria-hidden="true">{{ selectedCountry.flag }}</span>
      <span class="flex-1 text-left text-sm font-semibold text-[hsl(120_18%_92%/0.88)]">
        +{{ selectedCountry.code }}
      </span>
      <ChevronDown
        class="h-2 w-2 shrink-0 text-white/20 transition"
        :class="open && 'rotate-180 text-primary'"
        aria-hidden="true"
      />
    </button>

    <!-- Input numéro local -->
    <input
      type="tel"
      inputmode="tel"
      autocomplete="tel"
      :value="modelValue.localNumber"
      :disabled="disabled"
      :aria-invalid="invalid"
      :placeholder="$t('auth.merchant.phonePlaceholder')"
      class="h-[50px] flex-1 rounded-r-[10px] border-y-[1.5px] border-r-[1.5px] border-l border-l-white/[0.05] border-white/[0.07] bg-[#0e1812] px-4 text-sm text-[hsl(120_18%_92%)] outline-none placeholder:text-white/20 focus:border-primary focus:bg-[#0f1d12] focus:shadow-[0_0_0_3px_rgba(22,163,74,0.08)] disabled:cursor-not-allowed disabled:opacity-60"
      :class="invalid && 'border-destructive'"
      @input="handlePhoneInput"
    >

    <!-- Dropdown -->
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <ul
        v-if="open"
        role="listbox"
        :aria-label="$t('auth.merchant.selectCountry')"
        class="absolute left-0 top-[calc(100%+5px)] z-50 max-h-[216px] w-[196px] overflow-y-auto rounded-[11px] border border-primary/15 bg-[#0e1812] p-1 shadow-[0_18px_44px_rgba(0,0,0,0.65)]"
      >
        <li
          v-for="country in WHATSAPP_COUNTRIES"
          :key="country.code"
          role="option"
          :aria-selected="country.code === selectedCountry.code"
          class="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] text-[hsl(120_18%_92%/0.65)] transition hover:bg-primary/10 hover:text-[hsl(120_18%_92%)]"
          :class="
            country.code === selectedCountry.code &&
            'bg-primary/[0.14] text-primary hover:bg-primary/[0.18]'
          "
          @click="selectCountry(country.code)"
        >
          <span class="w-5 text-sm" aria-hidden="true">{{ country.flag }}</span>
          <span class="flex-1 font-medium">{{ $t(country.nameKey) }}</span>
          <span class="text-xs font-semibold text-primary/80">+{{ country.code }}</span>
        </li>
      </ul>
    </Transition>
  </div>
</template>
