import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: Home,
})

function Home() {
  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '3rem', maxWidth: '40rem', margin: '0 auto' }}>
      <h1 style={{ fontSize: '2.25rem', margin: 0 }}>KALGA</h1>
      <p style={{ color: '#52525b', marginTop: '0.5rem' }}>
        Socle TanStack Start, en cours de construction.
      </p>
    </main>
  )
}
