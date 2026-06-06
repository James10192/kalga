<!--
  Page de connexion — accessible à /login.
  Référence : ARCHITECTURE_FRONTEND.md sections 7.1 (Auth) + 7.4 (Validation)

  - Layout `empty` (centré, fond crème, sans header)
  - Form validé avec Zod côté client AVANT envoi
  - Erreurs serveur affichées en banner accessible (aria-live)
  - Redirection vers `?redirect=...` après succès (sinon vers dashboard)
-->

<script setup lang="ts">
import { Eye, EyeOff, Loader2 } from 'lucide-vue-next'

import { loginInputSchema } from '@/features/auth/schemas'
import type { LoginInput } from '@/features/auth/types'
import { ROUTES } from '@/utils/routes'

definePageMeta({
  layout: 'empty',
  // Si l'utilisateur est déjà connecté, on le renvoie vers /dashboard
  // (le middleware ne s'applique pas ici car /login est public, on gère onMounted).
})

const { t } = useI18n()
const { login, isLoggedIn, isAdmin } = useAuth()
const route = useRoute()
const router = useRouter()

// État du formulaire
const form = reactive<LoginInput>({ email: '', password: '' })
const showPassword = ref(false)
const loading = ref(false)
const serverError = ref<string | null>(null)
const fieldErrors = reactive<Partial<Record<keyof LoginInput, string>>>({})

// Si déjà connecté, redirection auto
onMounted(() => {
  if (isLoggedIn.value) {
    redirectAfterLogin()
  }
})

function redirectAfterLogin(): void {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  const fallback = isAdmin.value ? ROUTES.admin.home : ROUTES.dashboard.home
  router.push(redirect ?? fallback)
}

function clearErrors(): void {
  serverError.value = null
  fieldErrors.email = undefined
  fieldErrors.password = undefined
}

async function handleSubmit(event: Event): Promise<void> {
  event.preventDefault()
  clearErrors()

  // Validation client via Zod
  const parsed = loginInputSchema.safeParse(form)
  if (!parsed.success) {
    for (const issue of parsed.error.issues) {
      const path = issue.path[0] as keyof LoginInput | undefined
      if (path) {
        fieldErrors[path] = issue.message
      }
    }
    return
  }

  loading.value = true
  try {
    await login(parsed.data)
    redirectAfterLogin()
  } catch (err) {
    serverError.value = extractApiErrorMessage(err, t('auth.loginGenericError'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-md">
    <NuxtLink :to="ROUTES.home" class="mb-8 flex justify-center" :aria-label="$t('common.home')">
      <KalgaLogo size="lg" />
    </NuxtLink>

    <div class="rounded-xl border border-border bg-card p-8 shadow-sm">
      <header class="mb-6 text-center">
        <h1 class="font-display text-2xl font-semibold text-primary">
          {{ $t('auth.loginTitle') }}
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ $t('auth.loginSubtitle') }}
        </p>
      </header>

      <!-- Banner d'erreur serveur, annoncé aux lecteurs d'écran -->
      <div
        v-if="serverError"
        role="alert"
        aria-live="assertive"
        class="mb-4 rounded-md border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive"
      >
        {{ serverError }}
      </div>

      <form class="space-y-4" novalidate @submit="handleSubmit">
        <!-- Email -->
        <div>
          <label for="email" class="mb-1 block text-sm font-medium text-foreground">
            {{ $t('auth.email') }}
          </label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            autocomplete="email"
            required
            :disabled="loading"
            :aria-invalid="!!fieldErrors.email"
            :aria-describedby="fieldErrors.email ? 'email-error' : undefined"
            class="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
          >
          <p v-if="fieldErrors.email" id="email-error" class="mt-1 text-xs text-destructive">
            {{ fieldErrors.email }}
          </p>
        </div>

        <!-- Mot de passe -->
        <div>
          <label for="password" class="mb-1 block text-sm font-medium text-foreground">
            {{ $t('auth.password') }}
          </label>
          <div class="relative">
            <input
              id="password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              required
              :disabled="loading"
              :aria-invalid="!!fieldErrors.password"
              :aria-describedby="fieldErrors.password ? 'password-error' : undefined"
              class="w-full rounded-md border border-input bg-card px-3 py-2 pr-10 text-sm text-foreground transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
            >
            <button
              type="button"
              class="absolute inset-y-0 right-0 inline-flex items-center px-3 text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="
                showPassword ? $t('auth.hidePassword') : $t('auth.showPassword')
              "
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" class="h-4 w-4" aria-hidden="true" />
              <Eye v-else class="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <p v-if="fieldErrors.password" id="password-error" class="mt-1 text-xs text-destructive">
            {{ fieldErrors.password }}
          </p>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-warning transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" aria-hidden="true" />
          {{ loading ? $t('common.loading') : $t('auth.login') }}
        </button>
      </form>
    </div>
  </div>
</template>
