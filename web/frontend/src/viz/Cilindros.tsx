import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { inteiro } from '../format'
import { movimentoReduzido } from '../hooks/useMotion'
import type { Serie } from './Graficos'

/**
 * Cilindros de vidro com altura de líquido proporcional ao valor, a partir de zero.
 * Geometria adaptada do "Spending Overview Cylinder Chart" enviado como referência.
 */
const ALTURA = 300
const LARGURA_MAX = 72
const REFERENCIA = 84
const BORDA = 27.6
const TAMPA_RY = 8
const SUPERFICIE_RY = 10
const FURO_RX = 36
const FURO_RY = 6.75
const FUNDO_RY = 10.86
const TOPO = 0.8 // o maior valor ocupa esta fração do vidro
const FOLGA_BANDA = 6

const TONS: Record<Serie, { nome: string; claro: string; forte: string; suave1: string; suave2: string; anel: string; atras: string }> = {
  furtos: { nome: 'Furtos', claro: '#a9c8fb', forte: '#2563eb', suave1: '#e3ecfd', suave2: '#c3d6f9', anel: '#a8c2f4', atras: '#8fb0ee' },
  roubos: { nome: 'Roubos', claro: '#f7c79a', forte: '#d4701e', suave1: '#fbeadb', suave2: '#f4d6bc', anel: '#ecbd96', atras: '#e2a878' },
}

// Pontos do brilho (x, y, raio), sobre uma faixa de 96 px que se repete pelo líquido.
const FAISCAS = [
  [74, 32, 0.8], [92, 13, 0.7], [68, 65, 1], [63, 7, 1], [16, 79, 1], [35, 65, 1], [16, 32, 1], [32, 5, 1],
  [57, 40, 0.5], [46, 12, 0.5], [38, 75, 0.5], [88, 90, 0.5], [86, 34, 0.6], [20, 59, 0.5], [25, 17, 0.5], [59, 65, 0.5],
  [72, 14, 0.5], [65, 55, 0.6], [35, 33, 0.5], [50, 86, 0.7], [79, 49, 0.6], [28, 44, 0.8],
]

interface Linha {
  ano: number
  furtos: number
  roubos: number
}

interface Coluna {
  chave: string
  ano: number
  serie: Serie
  valor: number
  x: number
  w: number
}

const f = (n: number) => Math.round(n * 100) / 100
const elipse = (cx: number, cy: number, rx: number, ry: number) =>
  `M${f(cx - rx)} ${f(cy)}A${f(rx)} ${f(ry)} 0 1 0 ${f(cx + rx)} ${f(cy)}A${f(rx)} ${f(ry)} 0 1 0 ${f(cx - rx)} ${f(cy)}Z`

function geometria(x: number, w: number, nivel: number) {
  const s = w / REFERENCIA
  const rx = w / 2
  const cx = x + rx
  const dir = x + w
  const tampa = BORDA + TAMPA_RY * s
  const chao = ALTURA - FUNDO_RY * s
  const y = chao - nivel * (chao - tampa)
  return {
    cx,
    y,
    vidro: `M${f(x)} ${f(tampa)}A${f(rx)} ${f(TAMPA_RY * s)} 0 0 0 ${f(dir)} ${f(tampa)}V${f(y)}H${f(x)}Z`,
    lados: `M${f(x + 0.5)} ${f(tampa)}V${f(y)}M${f(dir - 0.5)} ${f(tampa)}V${f(y)}`,
    tampa: elipse(cx, tampa, rx - 0.5, TAMPA_RY * s - 0.5),
    atras: elipse(cx, y, rx, SUPERFICIE_RY * s),
    frente: `M${f(x)} ${f(y)}A${f(rx)} ${f(SUPERFICIE_RY * s)} 0 0 0 ${f(dir)} ${f(y)}V${f(chao)}A${f(rx)} ${f(FUNDO_RY * s)} 0 0 1 ${f(x)} ${f(chao)}Z`,
    anel: elipse(cx, y, rx, SUPERFICIE_RY * s) + elipse(cx, y, FURO_RX * s, FURO_RY * s),
  }
}

/** Enche os cilindros um após o outro; sem animação quando o movimento é reduzido. */
function useNiveis(alvos: number[]) {
  const [niveis, setNiveis] = useState<number[]>(() => (movimentoReduzido() ? alvos : alvos.map(() => 0)))
  const atual = useRef(niveis)
  const chave = alvos.join()
  useEffect(() => {
    if (movimentoReduzido()) {
      atual.current = alvos
      setNiveis(alvos)
      return
    }
    const inicio = alvos.map((_, i) => atual.current[i] ?? 0)
    const t0 = performance.now()
    let quadro = 0
    const passo = (t: number) => {
      let fim = true
      const proximo = alvos.map((alvo, i) => {
        const p = Math.min(Math.max((t - t0 - i * 70) / 900, 0), 1)
        if (p < 1) fim = false
        return inicio[i] + (alvo - inicio[i]) * (1 - (1 - p) ** 4)
      })
      atual.current = proximo
      setNiveis(proximo)
      if (!fim) quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave])
  return niveis
}

export function Cilindros({ linhas, series, descricao }: { linhas: Linha[]; series: Serie[]; descricao: string }) {
  const id = useId().replace(/[^\w-]/g, '')
  const caixa = useRef<HTMLDivElement>(null)
  const [largura, setLargura] = useState(440)
  const [escolhida, setEscolhida] = useState<string>()
  const [sobre, setSobre] = useState<string>()
  const [dica, setDica] = useState(false)

  useLayoutEffect(() => {
    const el = caixa.current!
    const medir = () => el.clientWidth && setLargura(el.clientWidth)
    medir()
    const obs = new ResizeObserver(medir)
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const colunas = useMemo<Coluna[]>(() => {
    const grupos = linhas.length
    const porGrupo = series.length
    const n = grupos * porGrupo
    const vaoInterno = 8
    const vaoGrupo = 26
    const vaos = grupos * (porGrupo - 1) * vaoInterno + (grupos - 1) * vaoGrupo
    const w = Math.min(LARGURA_MAX, (largura - 12 - vaos) / n)
    const ocupado = n * w + vaos
    let x = (largura - ocupado) / 2
    return linhas.flatMap((l, g) =>
      series.map((serie, i) => {
        const coluna = { chave: `${l.ano}-${serie}`, ano: l.ano, serie, valor: l[serie], x, w }
        x += w + (i < porGrupo - 1 ? vaoInterno : g < grupos - 1 ? vaoGrupo : 0)
        return coluna
      }),
    )
  }, [linhas, series, largura])

  const maximo = Math.max(...linhas.flatMap((l) => series.map((s) => l[s])), 1)
  const niveis = useNiveis(colunas.map((c) => (c.valor / maximo) * TOPO))
  const maior = colunas.reduce((a, c) => (c.valor > a.valor ? c : a), colunas[0])
  const fixa = colunas.find((c) => c.chave === escolhida) ?? maior
  const ativa = colunas.find((c) => c.chave === sobre) ?? fixa
  const iAtiva = colunas.indexOf(ativa)
  const gAtiva = geometria(ativa.x, ativa.w, niveis[iAtiva] ?? 0)

  function aoTeclar(e: KeyboardEvent<HTMLButtonElement>, i: number) {
    const destino = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: colunas.length - 1 }[e.key]
    if (destino === undefined) return
    e.preventDefault()
    const proxima = colunas[Math.min(Math.max(destino, 0), colunas.length - 1)]
    setEscolhida(proxima.chave)
    caixa.current?.querySelector<HTMLButtonElement>(`[data-chave="${proxima.chave}"]`)?.focus()
  }

  return (
    <div role="group" aria-label={descricao}>
      <div ref={caixa} className="relative" style={{ height: ALTURA }}>
        <svg aria-hidden="true" className="pointer-events-none absolute inset-0 size-full overflow-visible">
          <defs>
            {series.map((s) => (
              <g key={s}>
                <linearGradient id={`${id}-aceso-${s}`} x1="0" y1="0" x2="0.7" y2="1">
                  <stop offset="0" stopColor={TONS[s].claro} />
                  <stop offset="1" stopColor={TONS[s].forte} />
                </linearGradient>
                <linearGradient id={`${id}-suave-${s}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor={TONS[s].suave1} />
                  <stop offset="1" stopColor={TONS[s].suave2} />
                </linearGradient>
                <linearGradient id={`${id}-banda-${s}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor={TONS[s].forte} stopOpacity={0} />
                  <stop offset="0.4" stopColor={TONS[s].forte} stopOpacity={0.12} />
                  <stop offset="1" stopColor={TONS[s].forte} stopOpacity={0} />
                </linearGradient>
              </g>
            ))}
          </defs>
          <rect className="cilindro-banda" x={f(ativa.x - FOLGA_BANDA)} y={0} width={f(ativa.w + 2 * FOLGA_BANDA)} height={ALTURA} rx={10} fill={`url(#${id}-banda-${ativa.serie})`} />
          {colunas.map((c, i) => {
            const g = geometria(c.x, c.w, niveis[i] ?? 0)
            const ligado = c === ativa
            const s = c.w / REFERENCIA
            const tom = TONS[c.serie]
            return (
              <g key={c.chave}>
                <path d={g.vidro} fill="var(--color-soft)" />
                <path d={g.lados} fill="none" stroke="var(--color-line)" />
                <path d={g.tampa} fill="var(--color-soft)" stroke="var(--color-line)" />
                <g className="cilindro-tom" opacity={ligado ? 0 : 1}>
                  <path d={g.atras} fill={tom.atras} />
                  <path d={g.frente} fill={`url(#${id}-suave-${c.serie})`} />
                  <path d={g.anel} fillRule="evenodd" fill={tom.anel} />
                </g>
                <g className="cilindro-tom" opacity={ligado ? 1 : 0}>
                  <path d={g.atras} fill={tom.forte} />
                  <path d={g.frente} fill={`url(#${id}-aceso-${c.serie})`} />
                  <path d={g.anel} fillRule="evenodd" fill="#fff" />
                  <clipPath id={`${id}-corte-${i}`}>
                    <path d={g.frente} />
                  </clipPath>
                  {ligado && (
                    <g clipPath={`url(#${id}-corte-${i})`} fill="#fff">
                      {[0, 1, 2].map((copia) => (
                        <g key={copia} transform={`translate(${f(c.x)} ${f(g.y + 10 * s + copia * 92 * s)}) scale(${f(s)})`}>
                          {[0, 1, 2].map((grupo) => (
                            <g key={grupo} className={`cilindro-faisca faisca-${grupo}`} opacity={0.75}>
                              {FAISCAS.filter((_, k) => k % 3 === grupo).map(([x, y, r]) => (
                                <circle key={`${x}-${y}`} cx={x} cy={y} r={r} />
                              ))}
                            </g>
                          ))}
                        </g>
                      ))}
                    </g>
                  )}
                </g>
              </g>
            )
          })}
        </svg>

        {colunas.map((c, i) => (
          <button
            key={c.chave}
            type="button"
            data-chave={c.chave}
            aria-label={`${c.ano}, ${TONS[c.serie].nome}: ${inteiro(c.valor)}`}
            aria-pressed={c === fixa}
            tabIndex={c === fixa ? 0 : -1}
            className="absolute inset-y-0 cursor-pointer rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-accent"
            style={{ left: c.x, width: c.w }}
            onPointerEnter={() => {
              setSobre(c.chave)
              setDica(true)
            }}
            onPointerLeave={() => {
              setSobre(undefined)
              setDica(false)
            }}
            onClick={() => {
              setEscolhida(c.chave)
              setDica(true)
            }}
            onKeyDown={(e) => aoTeclar(e, i)}
            onFocus={(e) => e.currentTarget.matches(':focus-visible') && setDica(true)}
            onBlur={() => setDica(false)}
          />
        ))}

        {dica && (
          <div className="surgir pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-lg bg-ink px-2.5 py-1.5 text-white shadow-lg" style={{ left: Math.min(Math.max(gAtiva.cx, 56), largura - 56), top: Math.max(gAtiva.y - 16, 46) }}>
            <p className="text-[11px] opacity-75">
              {TONS[ativa.serie].nome} · {ativa.ano}
            </p>
            <p className="tabular text-sm font-semibold">{inteiro(ativa.valor)}</p>
          </div>
        )}
      </div>

      <div aria-hidden="true" className="relative mt-2 h-5">
        {linhas.map((l) => {
          const doAno = colunas.filter((c) => c.ano === l.ano)
          const centro = (doAno[0].x + doAno[doAno.length - 1].x + doAno[0].w) / 2
          return (
            <span key={l.ano} className={`absolute -translate-x-1/2 text-[13px] transition-colors ${ativa.ano === l.ano ? 'font-semibold text-ink' : 'text-ink-3'}`} style={{ left: centro }}>
              {l.ano}
            </span>
          )
        })}
      </div>
    </div>
  )
}
