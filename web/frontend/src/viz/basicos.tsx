import { useId, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { inteiro } from '../format'
import { useAposMontar } from '../hooks/useMotion'
import { atraso } from '../ui/base'

/** Semicírculo proporcional; a marca superior indica o ponto médio do arco. */
export function Medidor(props: { segmentos: { valor: number; cor: string; nome: string }[]; marca?: string; descricao: string; children?: ReactNode }) {
  const soma = props.segmentos.reduce((s, x) => s + x.valor, 0) || 1
  const fracoes = useMemo(() => props.segmentos.map((s) => s.valor / soma), [props.segmentos, soma])
  const zeros = useMemo(() => fracoes.map(() => 0), [fracoes])
  const animadas = useAposMontar(zeros, fracoes)
  const folga = 0.008
  let inicio = 0
  return (
    <div className="relative mx-auto w-full max-w-[17rem]" role="img" aria-label={props.descricao}>
      <svg viewBox="0 0 240 134" className="w-full">
        <path d="M20 124 A100 100 0 0 1 220 124" pathLength={1} fill="none" stroke="var(--color-track)" strokeWidth={22} />
        {props.segmentos.map((s, i) => {
          const f = animadas[i] ?? 0
          const el = (
            <path
              key={s.nome}
              className="transicao-arco"
              d="M20 124 A100 100 0 0 1 220 124"
              pathLength={1}
              fill="none"
              stroke={s.cor}
              strokeWidth={22}
              strokeDasharray={`${Math.max(f - folga, 0)} 2`}
              strokeDashoffset={-inicio}
            />
          )
          inicio += f
          return el
        })}
        {props.marca && (
          <>
            <line x1={120} y1={9} x2={120} y2={38} stroke="var(--color-ink)" strokeWidth={2} strokeLinecap="round" />
          </>
        )}
      </svg>
      {props.children && <div className="absolute inset-x-0 bottom-0 text-center">{props.children}</div>}
    </div>
  )
}

/** Duas parcelas lado a lado, com "VS" central. */
export function Versus(props: { esquerda: { nome: string; valor: string; fracao: number; detalhe?: string; cor: string }; direita: { nome: string; valor: string; fracao: number; detalhe?: string; cor: string } }) {
  const { esquerda: e, direita: d } = props
  const f = useAposMontar(0.5, e.fracao / (e.fracao + d.fracao || 1))
  return (
    <div>
      <div className="relative grid grid-cols-2">
        <div>
          <p className="flex items-center gap-1.5 text-[13px] text-ink-2">
            <span aria-hidden="true" className="h-3.5 w-1 rounded-full" style={{ background: e.cor }} />
            {e.nome}
          </p>
          <p className="tabular text-2xl font-bold tracking-tight">{e.valor}</p>
          {e.detalhe && <p className="tabular text-[13px] text-ink-3">{e.detalhe}</p>}
        </div>
        <div className="text-right">
          <p className="flex items-center justify-end gap-1.5 text-[13px] text-ink-2">
            {d.nome}
            <span aria-hidden="true" className="h-3.5 w-1 rounded-full" style={{ background: d.cor }} />
          </p>
          <p className="tabular text-2xl font-bold tracking-tight">{d.valor}</p>
          {d.detalhe && <p className="tabular text-[13px] text-ink-3">{d.detalhe}</p>}
        </div>
        <span aria-hidden="true" className="absolute left-1/2 top-1/2 flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-surface text-[10px] font-semibold text-ink-3 ring-1 ring-line">
          VS
        </span>
      </div>
      <div className="mt-3 flex h-2.5 gap-1" aria-hidden="true">
        <div className="transicao-largura rounded-full" style={{ width: `${f * 100}%`, background: e.cor }} />
        <div className="flex-1 rounded-full" style={{ background: d.cor }} />
      </div>
    </div>
  )
}

export interface ItemBarra {
  chave: string
  rotulo: string
  valor: number
  tag?: string
  cor?: string
  corSuave?: string
  descricao?: string
}

/** Barras neutras com a selecionada destacada; a linha opcional marca um limiar. */
export function BarrasDestaque(props: {
  itens: ItemBarra[]
  selecionado?: string
  maximo?: number
  limiar?: { valor: number; rotulo: string }
  altura?: string
  aoEscolher?: (chave: string) => void
  descricao: string
}) {
  const [foco, setFoco] = useState<string>()
  const max = props.maximo ?? Math.max(...props.itens.map((i) => i.valor), 1)
  const mostrado = foco ?? props.selecionado
  return (
    <div role={props.aoEscolher ? 'group' : 'img'} aria-label={props.descricao}>
      <div className={`relative flex items-end gap-1 pt-7 sm:gap-1.5 ${props.altura ?? 'h-36'}`} onMouseLeave={() => setFoco(undefined)}>
        {props.limiar && (
          <div className="pointer-events-none absolute inset-x-0 z-10 border-t border-dashed border-ink-3" style={{ bottom: `calc(${(props.limiar.valor / max) * 100}% - ${(props.limiar.valor / max) * 1.75}rem)` }}>
            <span className="absolute -top-2.5 left-0 rounded bg-ink px-1.5 py-px text-[10px] font-medium text-white">{props.limiar.rotulo}</span>
          </div>
        )}
        {props.itens.map((item, i) => {
          const ativo = item.chave === props.selecionado
          const realce = item.chave === mostrado
          const cor = ativo || realce ? (item.cor ?? 'var(--color-accent)') : (item.corSuave ?? 'var(--color-track)')
          const conteudo = (
            <>
              {realce && item.tag && (
                <span className="surgir absolute bottom-full left-1/2 z-20 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md bg-ink px-1.5 py-0.5 text-[11px] font-semibold text-white tabular">
                  {item.tag}
                </span>
              )}
              <span className="barra-v transicao-altura block w-full rounded-t-[5px]" style={{ height: '100%', background: cor, ...atraso(i * 25) }} />
            </>
          )
          const altura = `${Math.max((item.valor / max) * 100, 1.5)}%`
          return props.aoEscolher ? (
            <button
              key={item.chave}
              type="button"
              aria-pressed={ativo}
              aria-label={item.descricao ?? item.rotulo}
              className="transicao-altura relative flex-1 cursor-pointer"
              style={{ height: altura }}
              onMouseEnter={() => setFoco(item.chave)}
              onClick={() => props.aoEscolher?.(item.chave)}
            >
              {conteudo}
            </button>
          ) : (
            <div key={item.chave} className="transicao-altura relative flex-1" style={{ height: altura }} onMouseEnter={() => setFoco(item.chave)}>
              {conteudo}
            </div>
          )
        })}
      </div>
      <div className="mt-1.5 flex gap-1 sm:gap-1.5" aria-hidden="true">
        {props.itens.map((item) => (
          <span key={item.chave} className={`flex-1 truncate text-center text-[11px] ${item.chave === props.selecionado ? 'font-semibold text-ink' : 'text-ink-3'}`}>
            {item.rotulo}
          </span>
        ))}
      </div>
    </div>
  )
}

export function Faisca({ valores, cor }: { valores: number[]; cor: string }) {
  const grad = useId()
  if (valores.length < 2) return null
  const min = Math.min(...valores)
  const faixa = Math.max(...valores) - min || 1
  const pontos = valores.map((v, i) => `${(i / (valores.length - 1)) * 100},${34 - ((v - min) / faixa) * 30}`)
  return (
    <svg viewBox="0 0 100 36" preserveAspectRatio="none" className="h-12 w-full" aria-hidden="true">
      <defs>
        <linearGradient id={grad} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={cor} stopOpacity={0.22} />
          <stop offset="1" stopColor={cor} stopOpacity={0} />
        </linearGradient>
      </defs>
      <polygon points={`0,36 ${pontos.join(' ')} 100,36`} fill={`url(#${grad})`} />
      <polyline key={valores.join()} className="tracado" pathLength={1} points={pontos.join(' ')} fill="none" stroke={cor} strokeWidth={2} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

/** Mapa mês × dia da semana de contagens; `valores[dia][mes]`. */
export function MapaCalor({ valores, unidade }: { valores: number[][]; unidade: string }) {
  const [foco, setFoco] = useState<[number, number]>()
  const planos = valores.flat()
  const min = Math.min(...planos)
  const max = Math.max(...planos)
  const intensidade = (v: number) => (max === min ? 0.5 : (v - min) / (max - min))
  const cor = (v: number) => `color-mix(in srgb, var(--color-accent) ${Math.round(8 + intensidade(v) * 82)}%, var(--color-soft))`
  return (
    <div>
      <p className="tabular mb-2 h-5 text-[13px] text-ink-2" aria-live="off">
        {foco ? (
          <>
            <strong className="font-semibold text-ink">{inteiro(valores[foco[0]][foco[1]])}</strong> {unidade} · {DIAS[foco[0]]}, {MESES[foco[1]]}
          </>
        ) : (
          'Passe o cursor sobre uma célula para ver o valor.'
        )}
      </p>
      <div role="img" aria-label={`Mapa de calor de ${unidade} por dia da semana e mês; os valores estão na tabela disponível abaixo.`} className="grid gap-[3px]" style={{ gridTemplateColumns: '2rem repeat(12, minmax(0, 1fr))' }} onMouseLeave={() => setFoco(undefined)}>
        {valores.map((linha, d) => (
          <div key={DIAS[d]} className="contents">
            <span className="self-center text-[11px] text-ink-3">{DIAS[d]}</span>
            {linha.map((v, m) => (
              <div
                key={MESES[m]}
                className={`celula h-7 rounded-[5px] transition-shadow sm:h-8 ${foco?.[0] === d && foco?.[1] === m ? 'ring-2 ring-ink' : ''}`}
                style={{ background: cor(v), ...atraso((d + m) * 18) }}
                onMouseEnter={() => setFoco([d, m])}
              />
            ))}
          </div>
        ))}
        <span />
        {MESES.map((m) => (
          <span key={m} className="pt-1 text-center text-[11px] text-ink-3">
            {m}
          </span>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-end gap-2 text-[11px] text-ink-3" aria-hidden="true">
        <span className="tabular">{inteiro(min)}</span>
        <span className="h-2 w-28 rounded-full" style={{ background: 'linear-gradient(90deg, color-mix(in srgb, var(--color-accent) 8%, var(--color-soft)), color-mix(in srgb, var(--color-accent) 90%, var(--color-soft)))' }} />
        <span className="tabular">{inteiro(max)}</span>
      </div>
    </div>
  )
}
