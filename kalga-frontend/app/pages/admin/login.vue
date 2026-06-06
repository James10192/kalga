<!--
  Page login admin — port 1:1 depuis dashboard/admin.html ll. 13-95.
  Référence : ARCHITECTURE_FRONTEND.md sections 3 + 7.1 (Auth)

  Flow : admin saisit email + mot de passe → POST /api/auth/login → redirect /admin.
  Layout dark permanent indépendant de l'identité visuelle du dashboard admin global.
-->

<script setup lang="ts">
import { ArrowRight, ChartNetwork, Lock, Mail, Shield } from 'lucide-vue-next'

import { extractApiErrorMessage } from '@/composables/useApiError'
import { loginInputSchema } from '@/features/auth/schemas'
import type { LoginInput } from '@/features/auth/types'
import { ROUTES } from '@/utils/routes'

definePageMeta({
  layout: false,
  middleware: [], // bypass merchant/admin middleware (page publique)
})

const { t } = useI18n()
const { login } = useAuth()
const { push } = useToast()
const router = useRouter()

const form = reactive<LoginInput>({ email: '', password: '' })
const fieldErrors = reactive<{ email?: string; password?: string }>({})
const serverError = ref<string | null>(null)
const submitting = ref(false)

useHead({ title: t('auth.admin.title') })

function clearErrors(): void {
  fieldErrors.email = undefined
  fieldErrors.password = undefined
  serverError.value = null
}

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  clearErrors()

  const parsed = loginInputSchema.safeParse(form)
  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const key = issue.path[0] as keyof typeof fieldErrors | undefined
      if (key) fieldErrors[key] = issue.message
    }
    return
  }

  submitting.value = true
  try {
    await login(parsed.data)
    await router.push(ROUTES.admin.home)
  } catch (err) {
    serverError.value = extractApiErrorMessage(err, t('auth.admin.loginError'))
    push.error(serverError.value)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="admin-login">
    <!-- Orbes blur en background -->
    <div aria-hidden="true" class="orb orb-1" />
    <div aria-hidden="true" class="orb orb-2" />

    <!-- ============ Panneau gauche ============ -->
    <aside class="login-left">
      <div class="login-left-inner">
        <div class="brand">
          <div class="brand-icon">
            <ChartNetwork class="h-5 w-5" aria-hidden="true" />
          </div>
          <span class="brand-name">KALGA</span>
        </div>

        <div>
          <h2 class="hero-h2">
            {{ $t('auth.admin.heroLine1') }}<br>
            <em>{{ $t('auth.admin.heroLine2') }}</em><br>
            {{ $t('auth.admin.heroLine3') }}
          </h2>
          <p class="hero-p">{{ $t('auth.admin.heroSub') }}</p>
        </div>

        <div class="stats">
          <div class="stat">
            <span class="stat-value">+1k</span>
            <span class="stat-label">{{ $t('auth.admin.statMerchants') }}</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-value">24/7</span>
            <span class="stat-label">{{ $t('auth.admin.statAvailability') }}</span>
          </div>
          <div class="stat-divider" />
          <div class="stat">
            <span class="stat-value">v1.0</span>
            <span class="stat-label">{{ $t('auth.admin.statVersion') }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- ============ Panneau droit : form ============ -->
    <main class="login-right">
      <div class="login-card">
        <div class="card-top">
          <span class="restricted-tag">
            <Lock class="h-3 w-3" aria-hidden="true" />
            {{ $t('auth.admin.restrictedAccess') }}
          </span>
        </div>

        <div class="heading">
          <h1>
            {{ $t('auth.admin.headingLine1') }}<br>
            {{ $t('auth.admin.headingLine2') }}
          </h1>
          <p>{{ $t('auth.admin.subheading') }}</p>
        </div>

        <form class="form" novalidate @submit="handleSubmit">
          <div class="form-group">
            <label for="admin-email">{{ $t('auth.email') }}</label>
            <div class="input-field">
              <Mail class="input-icon" aria-hidden="true" />
              <input
                id="admin-email"
                v-model="form.email"
                type="email"
                autocomplete="username"
                required
                placeholder="admin@kalga.com"
                :disabled="submitting"
                :aria-invalid="!!fieldErrors.email"
              >
            </div>
            <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
          </div>

          <div class="form-group">
            <label for="admin-password">{{ $t('auth.password') }}</label>
            <div class="input-field">
              <Lock class="input-icon" aria-hidden="true" />
              <input
                id="admin-password"
                v-model="form.password"
                type="password"
                autocomplete="current-password"
                required
                placeholder="••••••••"
                :disabled="submitting"
                :aria-invalid="!!fieldErrors.password"
              >
            </div>
            <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
          </div>

          <button type="submit" class="btn-login" :disabled="submitting">
            <span>{{ submitting ? $t('common.loading') : $t('auth.admin.signIn') }}</span>
            <ArrowRight class="h-4 w-4" aria-hidden="true" />
          </button>

          <p v-if="serverError" role="alert" class="server-error">{{ serverError }}</p>
        </form>

        <p class="secure-note">
          <Shield class="h-3 w-3" aria-hidden="true" />
          {{ $t('auth.admin.secureNote') }}
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* Port 1:1 depuis dashboard/static/admin.css — section LOGIN SCREEN. */

.admin-login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 480px;
  background: #0f1117;
  position: relative;
  overflow-x: hidden;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  color: #ffffff;
}

@media (max-width: 900px) {
  .admin-login { grid-template-columns: 1fr; }
  .login-left { display: none; }
}

/* Orbes décoratifs */
@keyframes orb-float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-30px) scale(1.05); }
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
  z-index: 0;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: rgba(245, 158, 11, 0.08);
  top: -150px;
  left: -100px;
  animation: orb-float 12s ease-in-out infinite;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: rgba(99, 102, 241, 0.07);
  bottom: -100px;
  left: 30%;
  animation: orb-float 16s ease-in-out infinite reverse;
}

/* ---- Panneau gauche ---- */
@keyframes slide-in-left {
  from { opacity: 0; transform: translateX(-30px); }
  to { opacity: 1; transform: translateX(0); }
}

.login-left {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06) 0%, rgba(15, 17, 23, 0) 60%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.login-left-inner {
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 3.5rem;
  animation: slide-in-left 0.7s cubic-bezier(0.4, 0, 0.2, 1) both;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.brand-icon {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f1117;
  box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
}

.brand-name {
  font-family: 'Outfit', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 0.08em;
}

.hero-h2 {
  font-family: 'Outfit', system-ui, sans-serif;
  font-size: 3.25rem;
  font-weight: 800;
  line-height: 1.1;
  color: #ffffff;
  margin-bottom: 1.25rem;
}

.hero-h2 em {
  font-style: normal;
  color: #f59e0b;
}

.hero-p {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.7;
  max-width: 380px;
  font-weight: 300;
}

.stats {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 1.5rem 2rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 16px;
  width: fit-content;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stat-value {
  font-family: 'Outfit', system-ui, sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: #f59e0b;
}

.stat-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 400;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.08);
}

/* ---- Panneau droit ---- */
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-right {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2.5rem;
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255, 255, 255, 0.05);
  min-width: 0;
}

.login-card {
  width: 100%;
  max-width: 400px;
  animation: fade-in-up 0.6s cubic-bezier(0.4, 0, 0.2, 1) 0.15s both;
}

.card-top {
  margin-bottom: 2.5rem;
}

.restricted-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.875rem;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 100px;
  font-size: 0.75rem;
  font-weight: 500;
  color: #f59e0b;
  letter-spacing: 0.02em;
}

.heading {
  margin-bottom: 2.5rem;
}

.heading h1 {
  font-family: 'Outfit', system-ui, sans-serif;
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.1;
  color: #ffffff;
  margin-bottom: 0.75rem;
}

.heading p {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.4);
  line-height: 1.6;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 0.5rem;
}

.input-field {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 1rem;
  width: 0.875rem;
  height: 0.875rem;
  color: rgba(255, 255, 255, 0.25);
  pointer-events: none;
  transition: color 0.2s;
}

.input-field:focus-within .input-icon {
  color: #f59e0b;
}

.form input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 2.75rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  color: #ffffff;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  font-size: 0.9rem;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}

.form input::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

.form input:focus {
  outline: none;
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.04);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.08);
}

.btn-login {
  width: 100%;
  margin-top: 2rem;
  padding: 0.95rem 1.5rem;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #0f1117;
  border: none;
  border-radius: 12px;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 20px rgba(245, 158, 11, 0.25);
}

.btn-login:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 8px 28px rgba(245, 158, 11, 0.35);
}

.btn-login:active:not(:disabled) {
  transform: translateY(0);
}

.btn-login:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.field-error {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #f87171;
}

.server-error {
  color: #f87171;
  font-size: 0.8rem;
  margin-top: 0.875rem;
  text-align: center;
}

.secure-note {
  margin-top: 2rem;
  text-align: center;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}
</style>
