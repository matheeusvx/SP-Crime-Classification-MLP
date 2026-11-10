import { useState } from 'react'
import type { ModeloPublico } from '../api/types'

const NOMES: Record<string, string> = { mes: 'Mês', dia_semana: 'Dia da semana', tipo_local: 'Tipo de local', bairro: 'Bairro' }
const OCULTOS = [40, 72, 104, 136, 184, 216]

/** Diagrama da rede real: um cartão por atributo, amostra da camada oculta e saída. */
export function Rede({ modelo }: { modelo: ModeloPublico }) {
  const [foco, setFoco] = useState<number>()
  const { entradas, camadas_ocultas } = modelo.arquitetura
  const descricao = `Arquitetura: ${entradas} entradas, ${camadas_ocultas[0]} neurônios ReLU, 1 saída sigmoid e limiar 0,5`
  const ys = modelo.atributos.map((_, i) => 44 + i * 58)
  return (
    <figure role="img" aria-label={descricao}>
      {/* Em telas pequenas o texto do SVG ficaria ilegível: usa etapas empilhadas. */}
      <div className="grid gap-2 sm:hidden" aria-hidden="true">
        {[
          [String(entradas), 'Entradas One-Hot'],
          [String(camadas_ocultas[0]), 'Neurônios ReLU'],
          ['1', 'Saída sigmoid'],
          ['0,5', 'Limiar: ≥ 0,5 ROUBO'],
        ].map(([v, r]) => (
          <div key={r} className="flex items-center justify-between rounded-xl bg-soft px-4 py-3">
            <span className="text-sm text-ink-2">{r}</span>
            <span className="tabular text-xl font-bold">{v}</span>
          </div>
        ))}
      </div>
      <svg viewBox="0 0 760 260" className="hidden w-full sm:block" aria-hidden="true" onMouseLeave={() => setFoco(undefined)}>
        {ys.map((y, i) =>
          OCULTOS.map((oy) => (
            <path
              key={`${i}-${oy}`}
              className="fluxo-linha"
              d={`M176 ${y} C 250 ${y}, 270 ${oy}, 350 ${oy}`}
              fill="none"
              stroke={foco === i ? 'var(--color-accent)' : 'var(--color-line-strong)'}
              strokeWidth={foco === i ? 1.4 : 0.9}
              opacity={foco === undefined || foco === i ? 1 : 0.35}
              style={{ transition: 'opacity .2s, stroke .2s' }}
            />
          )),
        )}
        {OCULTOS.map((oy) => (
          <path key={oy} className="fluxo-linha" d={`M364 ${oy} C 430 ${oy}, 450 130, 512 130`} fill="none" stroke="var(--color-line-strong)" strokeWidth={0.9} />
        ))}
        <path d="M552 130 H 598" stroke="var(--color-ink)" strokeWidth={1.5} markerEnd="" />
        {modelo.atributos.map((a, i) => (
          <g key={a} onMouseEnter={() => setFoco(i)} style={{ cursor: 'default' }}>
            <rect x={8} y={ys[i] - 22} width={168} height={44} rx={10} fill={foco === i ? 'var(--color-accent-soft)' : 'var(--color-soft)'} style={{ transition: 'fill .2s' }} />
            <text x={22} y={ys[i] + 5} fontSize={14} fontWeight={500} fill="var(--color-ink)">
              {NOMES[a]}
            </text>
            <text x={162} y={ys[i] + 5} fontSize={14} fontWeight={700} textAnchor="end" fill="var(--color-ink)">
              {modelo.colunas_por_atributo[a]}
            </text>
          </g>
        ))}
        {OCULTOS.map((oy) => (
          <circle key={oy} cx={357} cy={oy} r={8} fill="var(--color-accent)" />
        ))}
        <text x={357} y={166} fontSize={15} textAnchor="middle" fill="var(--color-ink-3)">
          ⋮
        </text>
        <text x={357} y={22} fontSize={13} fontWeight={600} textAnchor="middle" fill="var(--color-ink)">
          {camadas_ocultas[0]} ReLU
        </text>
        <text x={92} y={13} fontSize={13} fontWeight={600} textAnchor="middle" fill="var(--color-ink)">
          {entradas} colunas One-Hot
        </text>
        <circle cx={532} cy={130} r={20} fill="var(--color-ink)" />
        <text x={532} y={135} fontSize={14} fontWeight={700} textAnchor="middle" fill="#fff">
          1
        </text>
        <text x={532} y={94} fontSize={13} fontWeight={600} textAnchor="middle" fill="var(--color-ink)">
          Sigmoid
        </text>
        <rect x={600} y={84} width={152} height={92} rx={12} fill="var(--color-soft)" />
        <text x={676} y={110} fontSize={13} fontWeight={600} textAnchor="middle" fill="var(--color-ink)">
          Limiar 0,5
        </text>
        <text x={676} y={134} fontSize={13} textAnchor="middle" fill="var(--color-ink-2)">
          ≥ 0,5 → ROUBO
        </text>
        <text x={676} y={156} fontSize={13} textAnchor="middle" fill="var(--color-ink-2)">
          &lt; 0,5 → FURTO
        </text>
      </svg>
      <figcaption className="mt-2 text-[13px] text-ink-3">Representação esquemática: a camada oculta tem {camadas_ocultas[0]} neurônios e todas as conexões são densas.</figcaption>
    </figure>
  )
}
