<!--
  Graphique linéaire SVG sans dépendance externe.
  Référence : ARCHITECTURE_FRONTEND.md section 7.5

  Pour rester léger (pas de chart.js), on dessine directement en SVG :
  - Ligne pleine + points
  - Min/max sur l'axe Y
  - Premier / dernier point sur l'axe X
  - Couleurs alignées sur la palette brand
  - Responsive via viewBox + preserveAspectRatio

  Si on a besoin de plus (tooltips riches, zooms, multi-séries), on passera
  à un wrapper Chart.js dans une phase ultérieure.
-->

<script setup lang="ts">
import type { StatsTimeseries, StatsTimeseriesPoint } from '@/features/stats/types'

interface Props {
  series: StatsTimeseries | undefined
  /** Hauteur du SVG en px (largeur = 100% du conteneur) */
  height?: number
  /** Formate la valeur affichée (axe Y + tooltip) */
  formatValue?: (value: number) => string
}

const props = withDefaults(defineProps<Props>(), {
  height: 200,
  formatValue: (v: number) => String(v),
})

const { t } = useI18n()

const VIEWBOX_WIDTH = 800
const PADDING = { top: 16, right: 16, bottom: 30, left: 56 }

interface ChartGeometry {
  points: StatsTimeseriesPoint[]
  pathD: string
  pixels: ReadonlyArray<{ x: number; y: number; point: StatsTimeseriesPoint }>
  minValue: number
  maxValue: number
}

const geometry = computed<ChartGeometry | null>(() => {
  const series = props.series
  if (!series || series.points.length === 0) return null

  const points = [...series.points]
  const values = points.map((p) => p.value)
  const minValue = Math.min(...values, 0)
  const maxValue = Math.max(...values, 1)
  const range = maxValue - minValue || 1

  const innerWidth = VIEWBOX_WIDTH - PADDING.left - PADDING.right
  const innerHeight = props.height - PADDING.top - PADDING.bottom
  const xStep = points.length > 1 ? innerWidth / (points.length - 1) : 0

  const pixels = points.map((point, i) => {
    const x = PADDING.left + i * xStep
    const ratio = (point.value - minValue) / range
    const y = PADDING.top + (1 - ratio) * innerHeight
    return { x, y, point }
  })

  const pathD = pixels
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ')

  return { points, pathD, pixels, minValue, maxValue }
})

const hoveredIndex = ref<number | null>(null)
const hoveredPoint = computed(() =>
  hoveredIndex.value !== null && geometry.value
    ? geometry.value.pixels[hoveredIndex.value]
    : null,
)
</script>

<template>
  <div class="relative w-full">
    <!-- Empty state -->
    <div
      v-if="!geometry"
      class="flex items-center justify-center rounded-md border border-dashed border-border bg-muted/30 text-sm text-muted-foreground"
      :style="{ height: `${props.height}px` }"
    >
      {{ t('stats.noData') }}
    </div>

    <svg
      v-else
      :viewBox="`0 0 ${VIEWBOX_WIDTH} ${props.height}`"
      class="w-full"
      :style="{ height: `${props.height}px` }"
      preserveAspectRatio="none"
      role="img"
      :aria-label="series?.label"
      @mouseleave="hoveredIndex = null"
    >
      <!-- Grille horizontale (3 lignes) -->
      <g aria-hidden="true">
        <line
          v-for="ratio in [0, 0.5, 1]"
          :key="ratio"
          :x1="PADDING.left"
          :y1="PADDING.top + (1 - ratio) * (props.height - PADDING.top - PADDING.bottom)"
          :x2="VIEWBOX_WIDTH - PADDING.right"
          :y2="PADDING.top + (1 - ratio) * (props.height - PADDING.top - PADDING.bottom)"
          stroke="currentColor"
          stroke-width="1"
          class="text-border"
        />
      </g>

      <!-- Labels axe Y (min / max) -->
      <g class="fill-current text-[10px] text-muted-foreground" aria-hidden="true">
        <text :x="PADDING.left - 8" :y="PADDING.top + 4" text-anchor="end">
          {{ props.formatValue(geometry.maxValue) }}
        </text>
        <text
          :x="PADDING.left - 8"
          :y="props.height - PADDING.bottom + 4"
          text-anchor="end"
        >
          {{ props.formatValue(geometry.minValue) }}
        </text>
      </g>

      <!-- Labels axe X (premier / dernier point) -->
      <g
        v-if="geometry.points.length > 0"
        class="fill-current text-[10px] text-muted-foreground"
        aria-hidden="true"
      >
        <text
          :x="PADDING.left"
          :y="props.height - 8"
          text-anchor="start"
        >
          {{ geometry.points[0]?.date }}
        </text>
        <text
          :x="VIEWBOX_WIDTH - PADDING.right"
          :y="props.height - 8"
          text-anchor="end"
        >
          {{ geometry.points[geometry.points.length - 1]?.date }}
        </text>
      </g>

      <!-- Ligne -->
      <path
        :d="geometry.pathD"
        fill="none"
        stroke="hsl(var(--primary))"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- Points + hover zones -->
      <g>
        <g v-for="(p, i) in geometry.pixels" :key="i">
          <circle
            :cx="p.x"
            :cy="p.y"
            r="3"
            fill="hsl(var(--primary))"
          />
          <rect
            :x="p.x - 12"
            :y="PADDING.top"
            :width="24"
            :height="props.height - PADDING.top - PADDING.bottom"
            fill="transparent"
            @mouseenter="hoveredIndex = i"
          />
        </g>
      </g>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="hoveredPoint"
      class="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border border-border bg-card px-2 py-1 text-xs shadow-sm"
      :style="{
        left: `${(hoveredPoint.x / VIEWBOX_WIDTH) * 100}%`,
        top: `${(hoveredPoint.y / props.height) * 100}%`,
      }"
    >
      <p class="font-medium text-foreground">{{ props.formatValue(hoveredPoint.point.value) }}</p>
      <p class="text-muted-foreground">{{ hoveredPoint.point.date }}</p>
    </div>
  </div>
</template>
