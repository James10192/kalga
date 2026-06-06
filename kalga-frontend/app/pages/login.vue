<!--
  Page login marchand — port 1:1 depuis dashboard/index.html ll. 14-228.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.5

  Flow : marchand saisit numéro WhatsApp + indicatif → POST /api/whatsapp/connect.
  Le QR / étape suivante vivent dans la PR onboarding (out of scope ici).
  Layout dark permanent (override le mode light/dark global).
-->

<script setup lang="ts">
import { ArrowRight, MessageCircle, Shield } from 'lucide-vue-next'

import CountryPhoneInput, {
  type CountryPhoneValue,
} from '@/components/auth/CountryPhoneInput.vue'
import { extractApiErrorMessage } from '@/composables/useApiError'
import { PHONE_DIGITS_ONLY_REGEX, WHATSAPP_COUNTRY_DEFAULT } from '@/utils/constants'
import { ROUTES } from '@/utils/routes'

definePageMeta({
  layout: false, // page autonome, design dark permanent qui sort du système light/dark
})

const { t } = useI18n()
const { push } = useToast()
const router = useRouter()

const phone = ref<CountryPhoneValue>({
  countryCode: WHATSAPP_COUNTRY_DEFAULT.code,
  localNumber: '',
})

const submitting = ref(false)
const fieldError = ref<string | null>(null)

useHead({ title: t('auth.merchant.title') })

function buildFullNumber(value: CountryPhoneValue): string {
  return `${value.countryCode}${value.localNumber.replace(/\D/g, '')}`
}

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  fieldError.value = null

  const fullNumber = buildFullNumber(phone.value)
  if (!PHONE_DIGITS_ONLY_REGEX.test(fullNumber)) {
    fieldError.value = t('auth.merchant.phoneInvalid')
    return
  }

  submitting.value = true
  try {
    await $fetch('/api/whatsapp/connect', {
      method: 'POST',
      body: { merchant_phone: fullNumber },
    })
    // Le QR + suite de l'onboarding sont sur /connecting — porté en PR onboarding.
    await router.push(`${ROUTES.connecting}?phone=${encodeURIComponent(fullNumber)}`)
  } catch (err) {
    push.error(extractApiErrorMessage(err, t('auth.merchant.connectError')))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <!-- ============ Panneau gauche : décoratif ============ -->
    <aside class="login-panel-left">
      <div aria-hidden="true" class="panel-deco panel-deco-1" />
      <div aria-hidden="true" class="panel-deco panel-deco-2" />
      <div aria-hidden="true" class="panel-deco panel-deco-3" />
      <div aria-hidden="true" class="panel-orb panel-orb-1" />
      <div aria-hidden="true" class="panel-orb panel-orb-2" />

      <div class="panel-left-inner">
        <div class="flex items-center gap-3.5">
          <div class="panel-logo-mark">
            <MessageCircle class="h-[22px] w-[22px]" aria-hidden="true" />
          </div>
          <span class="panel-brand-name">KALGA</span>
        </div>

        <div>
          <h2 class="panel-headline">
            {{ $t('auth.merchant.heroLine1') }}<br>
            <em>{{ $t('auth.merchant.heroLine2') }}</em><br>
            {{ $t('auth.merchant.heroLine3') }}
          </h2>
          <p class="panel-sub">{{ $t('auth.merchant.heroSub') }}</p>
        </div>

        <div class="panel-stats">
          <div class="panel-stat">
            <span class="panel-stat-value">+1k</span>
            <span class="panel-stat-label">{{ $t('auth.merchant.statMerchants') }}</span>
          </div>
          <div class="panel-stat">
            <span class="panel-stat-value">98%</span>
            <span class="panel-stat-label">{{ $t('auth.merchant.statResponse') }}</span>
          </div>
          <div class="panel-stat">
            <span class="panel-stat-value">24/7</span>
            <span class="panel-stat-label">{{ $t('auth.merchant.statAi') }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- ============ Panneau droit : form ============ -->
    <main class="login-panel-right">
      <div class="login-container">
        <div class="login-logo">
          <div class="logo-icon">
            <MessageCircle class="h-8 w-8" aria-hidden="true" />
          </div>
          <h1>{{ $t('auth.merchant.welcomeTitle') }}</h1>
          <p>{{ $t('auth.merchant.welcomeSubtitle') }}</p>
        </div>

        <form class="space-y-4" novalidate @submit="handleSubmit">
          <div>
            <label class="form-label-float">
              <span>{{ $t('auth.merchant.phoneLabel') }}</span>
            </label>
            <CountryPhoneInput
              v-model="phone"
              :disabled="submitting"
              :invalid="!!fieldError"
            />
            <p
              v-if="fieldError"
              role="alert"
              class="mt-2 text-center text-xs text-destructive"
            >
              {{ fieldError }}
            </p>
          </div>

          <button type="submit" class="btn-connect" :disabled="submitting">
            <MessageCircle class="h-4 w-4 shrink-0" aria-hidden="true" />
            <span class="flex-1">
              {{ submitting ? $t('common.loading') : $t('auth.merchant.connect') }}
            </span>
            <ArrowRight class="h-4 w-4 shrink-0" aria-hidden="true" />
          </button>
        </form>

        <p class="login-footer">
          <Shield class="h-3 w-3" aria-hidden="true" />
          {{ $t('auth.merchant.secureNote') }}
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Port 1:1 depuis dashboard/static/style.css — section LOGIN SCREENS.
   Style scoped car ces décorations sont trop spécifiques pour Tailwind
   et utilisées UNIQUEMENT par cette page (pas de réutilisation). */

.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: stretch;
  background: #0a0a0a;
  overflow: hidden;
  color: #f0ede8;
}

.login-panel-left {
  width: 46%;
  min-height: 100vh;
  background: linear-gradient(160deg, #071510 0%, #0a1a0e 50%, #061209 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.login-panel-left::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(22, 163, 74, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(22, 163, 74, 0.045) 1px, transparent 1px);
  background-size: 52px 52px;
  pointer-events: none;
  z-index: 0;
}

.panel-left-inner {
  position: relative;
  z-index: 2;
  padding: 56px 52px;
  display: flex;
  flex-direction: column;
  gap: 48px;
  width: 100%;
  max-width: 500px;
}

.panel-logo-mark {
  width: 46px;
  height: 46px;
  background: #16a34a;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 28px rgba(22, 163, 74, 0.35);
  color: #0a1a0e;
}

.panel-brand-name {
  font-family: 'Bricolage Grotesque', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
  color: #f0f8f2;
  letter-spacing: 5px;
}

.panel-headline {
  font-family: 'Bricolage Grotesque', system-ui, sans-serif;
  font-size: clamp(2.2rem, 3.2vw, 3.2rem);
  font-weight: 800;
  color: #edf7ef;
  line-height: 1.1;
  letter-spacing: -0.5px;
}

.panel-headline em {
  font-style: normal;
  color: #16a34a;
  position: relative;
  display: inline-block;
}

.panel-headline em::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 2px;
  width: 100%;
  height: 3px;
  background: #16a34a;
  opacity: 0.3;
  border-radius: 2px;
}

.panel-sub {
  font-size: 0.95rem;
  color: rgba(237, 247, 239, 0.48);
  line-height: 1.7;
  margin-top: 16px;
  max-width: 350px;
}

.panel-stats {
  display: flex;
  gap: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(22, 163, 74, 0.1);
}

.panel-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.panel-stat-value {
  font-family: 'Bricolage Grotesque', system-ui, sans-serif;
  font-size: 1.7rem;
  font-weight: 800;
  color: #16a34a;
  line-height: 1;
}

.panel-stat-label {
  font-size: 0.7rem;
  color: rgba(237, 247, 239, 0.38);
  letter-spacing: 0.6px;
  text-transform: uppercase;
}

.panel-deco {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(22, 163, 74, 0.1);
  pointer-events: none;
}

.panel-deco-1 {
  width: 380px;
  height: 380px;
  bottom: -90px;
  right: -110px;
  animation: ring-spin 45s linear infinite;
}

.panel-deco-2 {
  width: 220px;
  height: 220px;
  bottom: -30px;
  right: -50px;
  border-color: rgba(22, 163, 74, 0.16);
  animation: ring-spin 30s linear infinite reverse;
}

.panel-deco-3 {
  width: 120px;
  height: 120px;
  top: 14%;
  right: 7%;
  border-color: rgba(22, 163, 74, 0.09);
  animation: ring-spin 22s linear infinite;
}

@keyframes ring-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.panel-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(72px);
  pointer-events: none;
  z-index: 1;
}

.panel-orb-1 {
  width: 280px;
  height: 280px;
  background: rgba(22, 163, 74, 0.08);
  bottom: -60px;
  right: -60px;
}

.panel-orb-2 {
  width: 160px;
  height: 160px;
  background: rgba(16, 185, 129, 0.1);
  top: 20%;
  right: 5%;
}

.login-panel-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background: #0a0a0a;
  position: relative;
}

.login-panel-right::before {
  content: '';
  position: absolute;
  top: -150px;
  right: -150px;
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, rgba(22, 163, 74, 0.05) 0%, transparent 70%);
  pointer-events: none;
}

.login-container {
  background: #111111;
  border: 1px solid #202020;
  border-radius: 20px;
  padding: 48px 42px;
  width: 100%;
  max-width: 432px;
  box-shadow:
    0 28px 72px rgba(0, 0, 0, 0.55),
    0 0 0 1px rgba(22, 163, 74, 0.04);
  animation: container-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) both;
  position: relative;
  z-index: 1;
}

@keyframes container-in {
  from { opacity: 0; transform: translateY(22px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-logo {
  text-align: center;
  margin-bottom: 36px;
}

.logo-icon {
  width: 68px;
  height: 68px;
  background: linear-gradient(135deg, #16a34a 0%, #0d7a36 100%);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 18px;
  box-shadow:
    0 0 0 8px rgba(22, 163, 74, 0.07),
    0 10px 28px rgba(22, 163, 74, 0.22);
  position: relative;
  color: #0a1a0e;
}

.logo-icon::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 22px;
  border: 1px solid rgba(22, 163, 74, 0.18);
  animation: logo-pulse 3s ease-in-out infinite;
}

@keyframes logo-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(1.06); }
}

.login-logo h1 {
  font-family: 'Bricolage Grotesque', system-ui, sans-serif;
  font-size: 1.65rem;
  font-weight: 700;
  color: #edf7ef;
  letter-spacing: -0.2px;
}

.login-logo p {
  color: rgba(237, 247, 239, 0.42);
  margin-top: 7px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.form-label-float {
  display: block;
  margin-bottom: 7px;
}

.form-label-float span {
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(237, 247, 239, 0.42);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.btn-connect {
  width: 100%;
  margin-top: 8px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #16a34a 0%, #0d7a36 100%);
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-family: 'Geist', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: transform 0.15s, box-shadow 0.2s, opacity 0.2s;
  box-shadow: 0 8px 24px rgba(22, 163, 74, 0.25);
}

.btn-connect:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 32px rgba(22, 163, 74, 0.35);
}

.btn-connect:active:not(:disabled) {
  transform: translateY(0);
}

.btn-connect:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.login-footer {
  margin-top: 26px;
  text-align: center;
  font-size: 0.72rem;
  color: rgba(237, 247, 239, 0.32);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

@media (max-width: 900px) {
  .login-panel-left { display: none; }
  .login-panel-right { width: 100%; }
}
</style>
