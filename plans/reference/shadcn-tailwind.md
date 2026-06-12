# Référence — shadcn/ui + Tailwind v4 dans TanStack Start (Vite/React)

Fichier de référence pour agents exécuteurs sans contexte. Patterns concrets, copiables, testés.

Source : ctx7 `/shadcn-ui/ui` (shadcn 3.x, mai 2026) + `/tailwindlabs/tailwindcss.com` (Tailwind v4).

---

## 0. Versions de référence (juin 2026)

| Package | Version | Note |
|---|---|---|
| `tailwindcss` | `^4.x` | v4 = pas de `tailwind.config.js`, config en CSS via `@theme` |
| `@tailwindcss/vite` | `^4.x` | plugin Vite officiel (remplace PostCSS) |
| `shadcn` (CLI) | `3.x` | binaire = `shadcn` (PLUS `shadcn-ui`, déprécié depuis 2024) |
| `tw-animate-css` | latest | remplace `tailwindcss-animate` (plugin v3, obsolète) |
| `@tanstack/react-start` | `1.168+` | voir gotchas TanStack Start |
| `react` | `19.x` | |
| `vite` | `6+` / `8` | |

**Pièges de versions périmées (training data) :**
- ❌ `npx shadcn-ui@latest init` → utiliser `npx shadcn@latest init`
- ❌ `tailwind.config.ts` avec `content: [...]` → en v4 il n'existe plus, config = CSS
- ❌ `@tailwind base; @tailwind components; @tailwind utilities;` → en v4 = `@import "tailwindcss";`
- ❌ `tailwindcss-animate` (plugin JS) → utiliser `tw-animate-css` (`@import "tw-animate-css";`)
- ❌ `postcss.config.js` + `autoprefixer` → plus nécessaire, le plugin Vite gère tout
- ❌ HSL `0 0% 98%` dans les variables → shadcn 3.x utilise **OKLCH** (`oklch(0.985 0 0)`)

**Marcel (préférences globales) : utiliser `pnpm` exclusivement, jamais `npm`.** Les commandes ci-dessous montrent `pnpm`.

---

## 1. Setup Tailwind v4 dans Vite + TanStack Start

### 1.1 Install

```bash
pnpm add tailwindcss @tailwindcss/vite
pnpm add tw-animate-css        # remplace tailwindcss-animate
```

### 1.2 `vite.config.ts` — plugin Tailwind + alias `@`

Ordre des plugins : `tailwindcss()` peut être avant ou après `tanstackStart()`. L'alias `@` est requis par shadcn.

```ts
// vite.config.ts
import path from "node:path"
import { defineConfig } from "vite"
import tailwindcss from "@tailwindcss/vite"
import { tanstackStart } from "@tanstack/react-start/plugin/vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [
    tailwindcss(),
    tanstackStart({ tsr: { autoCodeSplitting: true } }),
    react(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

> Note TanStack Start : `getRouter` (pas `createRouter`) dans `src/router.tsx` ; providers Convex/auth NON dans `__root.tsx`. Voir rule `tanstack-start-vite-gotchas`.

### 1.3 CSS d'entrée — `src/styles.css` (ou `src/index.css`)

En Tailwind v4, une seule ligne importe tout. C'est ce fichier que shadcn va enrichir avec `@theme` et les variables.

```css
/* src/styles.css */
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));
```

`@custom-variant dark` = active le dark mode par **classe** `.dark` (au lieu de `prefers-color-scheme`). Obligatoire pour un toggle manuel. Forme alternative plus stricte : `@custom-variant dark (&:where(.dark, .dark *));`.

### 1.4 Charger le CSS dans `__root.tsx` (TanStack Start)

TanStack Start gère le `<head>`. Importer le CSS avec `?url` et le déclarer dans `head.links`.

```tsx
// src/routes/__root.tsx
import { createRootRoute, HeadContent, Scripts, Outlet } from "@tanstack/react-router"
import appCss from "../styles.css?url"

export const Route = createRootRoute({
  head: () => ({
    meta: [{ charSet: "utf-8" }, { name: "viewport", content: "width=device-width, initial-scale=1" }],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head><HeadContent /></head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  )
}
```

### 1.5 `tsconfig.json` — paths `@/*` (requis par shadcn CLI)

Le CLI shadcn lit `tsconfig.json` pour résoudre l'alias. Si Vite utilise un `tsconfig.app.json` séparé, ajouter `baseUrl`/`paths` dans **les deux** (root + app), sinon `shadcn init` plante avec « Import alias not found ».

```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  }
}
```

---

## 2. Init shadcn/ui (components.json, alias)

### 2.1 Commande init

```bash
pnpm dlx shadcn@latest init
```

Réponses CLI typiques pour ce stack : style `new-york`, base color `neutral`, CSS variables `yes`. Le CLI détecte Vite + Tailwind v4 et écrit `components.json` + `src/lib/utils.ts` + injecte les variables OKLCH dans le CSS d'entrée.

Init non-interactif (utile en script agent) :
```bash
pnpm dlx shadcn@latest init -d        # -d = defaults (new-york, neutral, css vars)
```

### 2.2 `components.json` cible (Vite + Tailwind v4)

**`tailwind.config` reste vide** (`""`) en v4. `css` pointe vers le fichier d'entrée réel.

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/styles.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

Champs clés :
- `rsc: false` → Vite/TanStack (pas Next App Router).
- `tailwind.config: ""` → v4, pas de fichier config JS.
- `tailwind.css` → DOIT matcher le chemin réel du CSS d'entrée (ici `src/styles.css`).
- `cssVariables: true` → theming par variables sémantiques (`bg-primary`, etc.).
- `iconLibrary: "lucide"` → `pnpm add lucide-react` requis.

### 2.3 `src/lib/utils.ts` (généré par init)

```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```
Déps installées par init : `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`.

---

## 3. Ajouter des composants

CLI `add`. Les composants sont copiés dans `src/components/ui/` (code possédé, modifiable).

```bash
pnpm dlx shadcn@latest add button card table form dialog input-otp sidebar badge
```

Ou un par un (idempotent ; `-o` pour overwrite) :
```bash
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add card
pnpm dlx shadcn@latest add table
pnpm dlx shadcn@latest add form        # tire aussi: label, react-hook-form, zod, @hookform/resolvers
pnpm dlx shadcn@latest add dialog
pnpm dlx shadcn@latest add input-otp    # tire la lib `input-otp`
pnpm dlx shadcn@latest add sidebar      # tire: button, separator, sheet, tooltip, skeleton, input + hook use-mobile
pnpm dlx shadcn@latest add badge
```

### 3.1 Dépendances transitives notables

| Composant | Tire (registry + npm) |
|---|---|
| `form` | `label`, `react-hook-form`, `zod`, `@hookform/resolvers` |
| `dialog` | `radix-ui` (`@radix-ui/react-dialog`) |
| `input-otp` | npm `input-otp` |
| `sidebar` | registry `button`, `separator`, `sheet`, `tooltip`, `skeleton`, `input` + hook `use-mobile.ts` + variables CSS sidebar (injectées auto dans le CSS) |
| `table` | aucune (pur HTML stylé) |
| `badge` | `class-variance-authority` (déjà là) |

### 3.2 Imports (toujours via alias `@`)

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { SidebarProvider, Sidebar, SidebarTrigger, SidebarContent } from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"
```

### 3.3 Patterns d'usage concrets

**input-otp** (code WhatsApp à 6 chiffres — cas Kalga activation/login OTP) :
```tsx
<InputOTP maxLength={6} value={code} onChange={setCode}>
  <InputOTPGroup>
    {Array.from({ length: 6 }).map((_, i) => <InputOTPSlot key={i} index={i} />)}
  </InputOTPGroup>
</InputOTP>
```

**sidebar** (layout dashboard) — `SidebarProvider` enveloppe TOUT le layout, pas juste la sidebar :
```tsx
<SidebarProvider>
  <Sidebar>
    <SidebarContent>{/* nav items */}</SidebarContent>
  </Sidebar>
  <main className="flex-1">
    <SidebarTrigger />   {/* bouton toggle mobile */}
    {children}
  </main>
</SidebarProvider>
```
`sidebar` crée aussi `src/hooks/use-mobile.ts` (breakpoint mobile). Variables CSS dédiées : `--sidebar`, `--sidebar-foreground`, `--sidebar-primary`, `--sidebar-accent`, `--sidebar-border`, `--sidebar-ring` (light + dark, voir §4).

**form** (react-hook-form + zod) :
```tsx
const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) })
// <Form {...form}><form onSubmit={form.handleSubmit(onSubmit)}>
//   <FormField control={form.control} name="..." render={({ field }) => (
//     <FormItem><FormLabel/><FormControl><Input {...field}/></FormControl><FormMessage/></FormItem>
//   )} />
```

---

## 4. Tokens & theming (1 accent + monochrome)

### 4.1 Structure complète du CSS (`src/styles.css` après init)

Tailwind v4 + shadcn 3.x = **OKLCH** (pas HSL). Trois blocs : `@theme inline` (mappe variables → utilitaires Tailwind), `:root` (light), `.dark` (dark).

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
}

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --chart-1: oklch(0.646 0.222 41.116);
  --chart-2: oklch(0.6 0.118 184.704);
  --chart-3: oklch(0.398 0.07 227.392);
  --chart-4: oklch(0.828 0.189 84.429);
  --chart-5: oklch(0.769 0.188 70.08);
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.556 0 0);
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --sidebar: oklch(0.205 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-primary: oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.556 0 0);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

### 4.2 Stratégie « 1 accent + monochrome » (préférence Marcel)

Le défaut `neutral` ci-dessus est déjà **monochrome** (toutes les couleurs sont des gris OKLCH chroma=0). Pour ajouter **un seul accent** (cas Kalga = vert `#16a34a`), il suffit de :

1. **Remplacer `--primary`** (light + dark) par l'accent. Garder TOUT le reste en gris (`secondary`, `muted`, `accent` sémantique, `border`, `card` restent monochromes).
2. Le `--accent` sémantique de shadcn ≠ « couleur d'accent design ». C'est la couleur de hover/highlight neutre. **Ne pas y mettre le vert** — laisser gris, sinon tous les hovers deviennent verts.

Conversion `#16a34a` → OKLCH ≈ `oklch(0.627 0.17 149)`. Exemple :

```css
:root {
  /* ... tout le reste reste monochrome (gris) ... */
  --primary: oklch(0.627 0.17 149);          /* vert Kalga */
  --primary-foreground: oklch(0.985 0 0);    /* texte blanc sur vert */
  --ring: oklch(0.627 0.17 149);             /* focus ring = accent */
}
.dark {
  --primary: oklch(0.7 0.16 149);            /* vert un peu plus clair en dark */
  --primary-foreground: oklch(0.205 0 0);
  --ring: oklch(0.7 0.16 149);
}
```

Résultat : boutons primaires, liens actifs, focus rings = vert ; tout le reste (cards, borders, textes secondaires, hovers) = monochrome. Conforme « 1 accent color + monochrome ».

Utilitaires Tailwind correspondants : `bg-primary text-primary-foreground`, `border-border`, `text-muted-foreground`, `bg-card`, `ring-ring`. NE PAS coder en dur `bg-green-600` — toujours passer par les tokens sémantiques.

### 4.3 Toggle dark mode (classe `.dark` sur `<html>`)

```tsx
// active/désactive le dark mode
document.documentElement.classList.toggle("dark")
```
Comme `@custom-variant dark (&:is(.dark *))` cible `.dark`, mettre la classe sur `<html>` (ou `<body>`) suffit. Pas de config JS supplémentaire en v4.

### 4.4 Rayon (radius)

Un seul token pilote tous les rayons : `--radius: 0.625rem`. Les utilitaires `rounded-sm/md/lg/xl` sont dérivés via `calc()` dans `@theme inline`. Changer la rondeur globale = changer `--radius` uniquement.

---

## 5. Checklist de validation (avant `pnpm dev`)

- [ ] `pnpm add tailwindcss @tailwindcss/vite tw-animate-css`
- [ ] `vite.config.ts` : `tailwindcss()` dans plugins + alias `@` → `./src`
- [ ] `src/styles.css` : `@import "tailwindcss";` + `@custom-variant dark`
- [ ] CSS chargé via `?url` dans `__root.tsx` `head.links`
- [ ] `tsconfig.json` : `baseUrl: "."` + `paths { "@/*": ["./src/*"] }`
- [ ] `pnpm dlx shadcn@latest init -d` → `components.json` avec `tailwind.config: ""`, `css: "src/styles.css"`, `cssVariables: true`
- [ ] `src/lib/utils.ts` présent (`cn()`)
- [ ] `pnpm dlx shadcn@latest add button card table form dialog input-otp sidebar badge`
- [ ] Variables OKLCH dans `:root` et `.dark` ; `--primary` = accent unique, reste monochrome
- [ ] `@layer base { body { @apply bg-background text-foreground } }` présent

## 6. Pièges récapitulés

1. CLI = `shadcn` (PAS `shadcn-ui`).
2. Tailwind v4 = config en CSS (`@theme`), **aucun** `tailwind.config.js` ni `postcss.config.js`.
3. Couleurs = **OKLCH**, pas HSL (le format `0 0% 98%` est v3/ancien shadcn).
4. `tw-animate-css` (`@import`), pas `tailwindcss-animate` (plugin).
5. `components.json` → `tailwind.config: ""` et `css` doit pointer le bon fichier d'entrée.
6. Alias `@` requis dans `vite.config.ts` ET `tsconfig.json` (sinon init échoue).
7. `--accent` sémantique ≠ couleur d'accent design : pour « 1 accent », modifier `--primary` (+`--ring`), pas `--accent`.
8. Sidebar : `SidebarProvider` enveloppe tout le layout ; crée `use-mobile.ts` et des variables `--sidebar-*`.
9. TanStack Start : CSS importé via `?url` dans `__root.tsx`, pas un `<link>` statique dans un `index.html` (Start gère le document).
