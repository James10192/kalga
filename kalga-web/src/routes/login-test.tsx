import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useMutation, useQuery } from 'convex/react'
import { api } from '../../convex/_generated/api'
import { authClient } from '~/lib/auth-client'

// Page de test JETABLE (remplacée par l'UI réelle en plan 006).
// Valide le flow : téléphone -> OTP WhatsApp -> code -> session -> org scopée.
export const Route = createFileRoute('/login-test')({
  component: LoginTest,
})

function LoginTest() {
  const session = authClient.useSession()
  const current = useQuery(api.merchants.current)

  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function requestOtp() {
    setError(null)
    setBusy(true)
    try {
      const { error: err } = await authClient.phoneNumber.sendOtp({
        phoneNumber: phone,
      })
      if (err) throw new Error(err.message ?? 'Envoi OTP échoué')
      setStep('code')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function verifyOtp() {
    setError(null)
    setBusy(true)
    try {
      const { error: err } = await authClient.phoneNumber.verify({
        phoneNumber: phone,
        code,
      })
      if (err) throw new Error(err.message ?? 'Code invalide')
      // recharge pour propager le JWT à Convex, puis provisionne l'org.
      window.location.href = '/login-test?verified=1'
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  async function signOut() {
    await authClient.signOut()
    window.location.href = '/login-test'
  }

  const isConnected = !!session.data

  return (
    <main
      style={{
        fontFamily: 'system-ui, sans-serif',
        padding: '3rem',
        maxWidth: '32rem',
        margin: '0 auto',
      }}
    >
      <h1 style={{ fontSize: '1.75rem' }}>Test connexion KALGA</h1>
      <p style={{ color: '#52525b' }}>
        Page de test (plan 003). Saisir un numéro WhatsApp, recevoir le code,
        puis valider.
      </p>

      {error && (
        <p style={{ color: '#dc2626', fontWeight: 600 }}>{error}</p>
      )}

      {!isConnected && step === 'phone' && (
        <section style={{ display: 'grid', gap: '0.75rem', marginTop: '1.5rem' }}>
          <label>
            Numéro WhatsApp (format international, ex 2250141540178)
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              style={{ display: 'block', width: '100%', padding: '0.5rem' }}
              placeholder="2250141540178"
            />
          </label>
          <label>
            Nom de la boutique
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ display: 'block', width: '100%', padding: '0.5rem' }}
              placeholder="Ma Boutique"
            />
          </label>
          <button onClick={requestOtp} disabled={busy || !phone}>
            {busy ? 'Envoi...' : 'Recevoir le code'}
          </button>
        </section>
      )}

      {!isConnected && step === 'code' && (
        <section style={{ display: 'grid', gap: '0.75rem', marginTop: '1.5rem' }}>
          <label>
            Code reçu sur WhatsApp
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={{ display: 'block', width: '100%', padding: '0.5rem' }}
              placeholder="123456"
            />
          </label>
          <button onClick={verifyOtp} disabled={busy || !code}>
            {busy ? 'Vérification...' : 'Valider'}
          </button>
        </section>
      )}

      {isConnected && (
        <ConnectedPanel
          name={name}
          phone={phone}
          current={current}
          onSignOut={signOut}
        />
      )}
    </main>
  )
}

function ConnectedPanel({
  name,
  phone,
  current,
  onSignOut,
}: {
  name: string
  phone: string
  current: unknown
  onSignOut: () => void
}) {
  const provision = useMutation(api.merchants.provisionMerchantOrg)
  const [msg, setMsg] = useState<string | null>(null)

  async function doProvision() {
    setMsg(null)
    try {
      const res = await provision({ name: name || 'Ma Boutique', phone })
      setMsg(`Org provisionnée : ${JSON.stringify(res)} — recharge en cours...`)
      setTimeout(() => (window.location.href = '/login-test'), 800)
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <p style={{ color: '#16a34a', fontWeight: 600 }}>Session active.</p>
      <p>
        Marchand courant (query scopée withOrg) :{' '}
        <code>{JSON.stringify(current ?? null)}</code>
      </p>
      <p style={{ color: '#52525b', fontSize: '0.875rem' }}>
        Si aucune organisation active n'existe encore, provisionner la boutique
        (nom : {name || 'Ma Boutique'}, tel : {phone}).
      </p>
      <button onClick={doProvision}>Provisionner la boutique</button>{' '}
      <button onClick={onSignOut}>Se déconnecter</button>
      {msg && <p style={{ marginTop: '0.5rem' }}>{msg}</p>}
    </section>
  )
}
