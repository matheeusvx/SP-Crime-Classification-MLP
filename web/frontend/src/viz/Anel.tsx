import { useEffect, useId, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import { inteiro, percentual } from '../format'
import { movimentoReduzido } from '../hooks/useMotion'
import { Numero } from '../ui/base'

/**
 * Anel em espiral: cada fatia, no sentido horário, é um degrau mais fina e passa por baixo da vizinha.
 * Geometria adaptada do "Portfolio Allocation Chart" enviado como referência.
 */
const TAM = 400
const C = TAM / 2
const EXTERNO = 200
const DEGRAU = 10
const INTERNO = 116.82
const DOBRA = 6 // graus que uma fatia corre por baixo da mais grossa
const DESTAQUE = 6
const INICIO = -30.188
const PILULA = 48

export interface FatiaAnel {
  chave: string
  nome: string
  valor: number
  cor: string
  textoPilula: string
}

interface Geo {
  inicio: number
  vao: number
  externo: number
  faixa: number
  dobraIni: number
  dobraFim: number
}

const rad = (g: number) => (g * Math.PI) / 180
const mod = (n: number, m: number) => ((n % m) + m) % m
const f = (n: number) => Math.round(n * 1000) / 1000
const polar = (r: number, a: number): [number, number] => [C + r * Math.sin(a), C - r * Math.cos(a)]

function setor(interno: number, externo: number, a0: number, a1: number) {
  const grande = a1 - a0 > 180 ? 1 : 0
  const [x0, y0] = polar(externo, rad(a0))
  const [x1, y1] = polar(externo, rad(a1))
  const [x2, y2] = polar(interno, rad(a1))
  const [x3, y3] = polar(interno, rad(a0))
  return `M${f(x0)} ${f(y0)}A${externo} ${externo} 0 ${grande} 1 ${f(x1)} ${f(y1)}L${f(x2)} ${f(y2)}A${interno} ${interno} 0 ${grande} 0 ${f(x3)} ${f(y3)}Z`
}

/** Contorno da fatia, opcionalmente recortado pela varredura de entrada (`ate` graus a partir do início). */
function caminho(g: Geo, ate?: number) {
  let a0 = g.inicio - g.dobraIni
  let a1 = g.inicio + g.vao + g.dobraFim
  if (ate !== undefined) {
    const u0 = mod(a0 - INICIO, 360)
    const u1 = Math.min(u0 + (a1 - a0), ate)
    if (!(u1 > u0)) return ''
    a0 = INICIO + u0
    a1 = INICIO + u1
  }
  return setor((INTERNO * g.externo) / g.faixa, g.externo, a0, Math.min(a1, a0 + 359.99))
}

function layout(valores: number[], ativa: number | null): Geo[] {
  const total = valores.reduce((a, b) => a + b, 0) || 1
  const m = valores.length
  let borda = INICIO
  return valores.map((v, i) => {
    const vao = (v / total) * 360
    const posto = i === 0 ? 0 : m - i
    const faixa = EXTERNO - DEGRAU * posto
    const externo = faixa + (i === ativa ? DESTAQUE : 0)
    if (i === 0) return { inicio: INICIO, vao, externo, faixa, dobraIni: 0, dobraFim: m > 1 && posto === m - 1 ? DOBRA : 0 }
    borda -= vao
    return { inicio: borda, vao, externo, faixa, dobraIni: DOBRA, dobraFim: posto === m - 1 ? DOBRA : 0 }
  })
}

function pilula(g: Geo) {
  const r = (INTERNO + g.faixa) / 2
  const [x, y] = polar(r, rad(g.inicio + g.vao - Math.min(13.15, g.vao / 2)))
  return { left: `${((x - PILULA / 2) / TAM) * 100}%`, top: `${((y - PILULA / 2) / TAM) * 100}%`, cabe: rad(g.vao) * r >= PILULA + 6 }
}

const suave = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)

export function Anel({ fatias, rotuloTotal }: { fatias: FatiaAnel[]; rotuloTotal: string }) {
  const id = useId().replace(/[^\w-]/g, '')
  const [sobre, setSobre] = useState<number | null>(null)
  const [fixa, setFixa] = useState<number | null>(null)
  const [varredura, setVarredura] = useState(() => (movimentoReduzido() ? 1 : 0))
  const valores = fatias.map((x) => x.valor)
  const total = valores.reduce((a, b) => a + b, 0)
  const ativa = sobre ?? fixa
  const geo = layout(valores, ativa)
  // as mais finas primeiro, para correrem por baixo das mais grossas
  const ordem = fatias.map((_, i) => i).sort((a, b) => geo[a].faixa - geo[b].faixa)

  useEffect(() => {
    if (movimentoReduzido()) return
    const t0 = performance.now()
    let q = 0
    const passo = (t: number) => {
      const p = Math.min((t - t0 - 150) / 1300, 1)
      setVarredura(Math.max(p, 0))
      if (p < 1) q = requestAnimationFrame(passo)
    }
    q = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(q)
  }, [])
  const ate = varredura < 1 ? suave(varredura) * (360 + DOBRA) : undefined

  function fatiaEm(e: PointerEvent<HTMLDivElement>) {
    const caixa = e.currentTarget.getBoundingClientRect()
    const u = caixa.width / TAM
    const x = (e.clientX - caixa.left) / u - C
    const y = (e.clientY - caixa.top) / u - C
    const r = Math.hypot(x, y)
    if (r < INTERNO - 10) return null
    const ang = (Math.atan2(x, -y) * 180) / Math.PI
    const i = geo.findIndex((g) => mod(ang - g.inicio, 360) < g.vao)
    return i >= 0 && r <= geo[i].externo + 6 ? i : null
  }

  function aoTeclar(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Escape') return setSobre(null)
    const atual = ativa ?? -1
    const proxima = { ArrowRight: atual + 1, ArrowDown: atual + 1, ArrowLeft: atual - 1, ArrowUp: atual - 1, Home: 0, End: fatias.length - 1 }[e.key]
    if (proxima === undefined) return
    e.preventDefault()
    setSobre(mod(proxima, fatias.length))
  }

  const iSlider = ativa ?? 0
  return (
    <div className="flex flex-col items-center">
      <div className="relative aspect-square w-full max-w-[17rem]">
        <svg aria-hidden="true" viewBox={`-12 -12 ${TAM + 24} ${TAM + 24}`} className="pointer-events-none absolute -inset-[3%] size-[106%] overflow-visible">
          <defs>
            <filter id={`${id}-sombra`} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
              <feDropShadow dx={-2} dy={2} stdDeviation={2.7} floodColor="#000" floodOpacity={0.14} />
            </filter>
            {fatias.map((x) => (
              <filter key={x.chave} id={`${id}-brilho-${x.chave}`} x="-30%" y="-30%" width="160%" height="160%" colorInterpolationFilters="sRGB">
                <feDropShadow dx={4} dy={0} stdDeviation={7} floodColor={x.cor} floodOpacity={0.45} />
              </filter>
            ))}
          </defs>
          {ordem.map((i) => {
            const d = caminho(geo[i], ate)
            return (
              <g key={fatias[i].chave}>
                <path d={d} filter={`url(#${id}-sombra)`} />
                <path d={d} fill={fatias[i].cor} filter={`url(#${id}-brilho-${fatias[i].chave})`} className="anel-fatia" />
                <path d={d} fill="#fff" className="transition-opacity duration-300" opacity={ativa !== null && ativa !== i ? 0.55 : 0} />
              </g>
            )
          })}
        </svg>

        <div
          role="slider"
          tabIndex={0}
          aria-label="Distribuição entre furtos e roubos"
          aria-valuemin={0}
          aria-valuemax={fatias.length - 1}
          aria-valuenow={iSlider}
          aria-valuetext={`${fatias[iSlider].nome}: ${inteiro(fatias[iSlider].valor)}, ${percentual(fatias[iSlider].valor / total, 1)}`}
          className="absolute inset-0 cursor-pointer rounded-full outline-none focus-visible:ring-2 focus-visible:ring-accent"
          onPointerMove={(e) => setSobre(fatiaEm(e))}
          onPointerLeave={(e) => e.pointerType === 'mouse' && setSobre(null)}
          onClick={(e) => {
            const i = fatiaEm(e as unknown as PointerEvent<HTMLDivElement>)
            setFixa((atual) => (atual === i ? null : i))
          }}
          onBlur={() => setSobre(null)}
          onKeyDown={aoTeclar}
        />

        {fatias.map((x, i) => {
          const p = pilula(geo[i])
          const visivel = p.cabe && (ate === undefined || ate >= mod(geo[i].inicio + geo[i].vao - INICIO, 360) - 13)
          return (
            <span
              key={x.chave}
              aria-hidden="true"
              className={`pointer-events-none absolute flex size-12 items-center justify-center rounded-full text-[13px] font-semibold transition-opacity duration-300 ${visivel ? (ativa !== null && ativa !== i ? 'opacity-40' : 'opacity-100') : 'opacity-0'}`}
              style={{ left: p.left, top: p.top, color: x.textoPilula, background: 'linear-gradient(135deg, rgb(255 255 255 / .06), rgb(255 255 255 / .2))', boxShadow: 'inset 0 0 0 1px rgb(255 255 255 / .32)' }}
            >
              {percentual(x.valor / total, 0)}
            </span>
          )
        })}

        <div aria-hidden="true" className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          {ativa !== null ? (
            <div key={ativa} className="subir">
              <p className="text-[13px] text-ink-2">{fatias[ativa].nome}</p>
              <p className="tabular text-[22px] font-bold tracking-tight">
                <Numero valor={fatias[ativa].valor} formato={(n) => inteiro(Math.round(n))} />
              </p>
              <p className="tabular text-xs text-ink-3">{percentual(fatias[ativa].valor / total, 1)} dos boletins</p>
            </div>
          ) : (
            <div className="subir">
              <p className="text-[13px] text-ink-2">{rotuloTotal}</p>
              <p className="tabular text-[22px] font-bold tracking-tight">
                <Numero valor={total} formato={(n) => inteiro(Math.round(n))} />
              </p>
            </div>
          )}
        </div>
      </div>

      <ul className="mt-4 flex w-full justify-center gap-5">
        {fatias.map((x, i) => (
          <li key={x.chave} onPointerEnter={() => setSobre(i)} onPointerLeave={() => setSobre(null)} className={`flex cursor-default items-center gap-1.5 text-[13px] text-ink-2 transition-opacity ${ativa !== null && ativa !== i ? 'opacity-60' : ''}`}>
            <span aria-hidden="true" className="size-2.5 rounded-full" style={{ background: x.cor }} />
            {x.nome} {percentual(x.valor / total, 1)}
          </li>
        ))}
      </ul>
    </div>
  )
}
