import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ReactNode } from 'react'
import { compacto, inteiro } from '../format'

export type Serie = 'furtos' | 'roubos'

export const SERIES: Record<Serie, { nome: string; cor: string }> = {
  furtos: { nome: 'Furtos', cor: 'var(--color-furto)' },
  roubos: { nome: 'Roubos', cor: 'var(--color-roubo)' },
}

const EIXO = { fontSize: 12, fill: 'var(--color-ink-3)' }
const DICA = {
  contentStyle: { borderRadius: 6, border: '1px solid var(--color-line-strong)', fontSize: 13, padding: '6px 10px' },
  formatter: (valor: unknown) => inteiro(Number(valor)),
}

export function Legenda({ series }: { series: Serie[] }) {
  if (series.length < 2) return null
  return (
    <ul className="flex flex-wrap gap-4 text-[13px] text-ink-2">
      {series.map((s) => (
        <li key={s} className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block size-2.5 rounded-[3px]" style={{ background: SERIES[s].cor }} />
          {SERIES[s].nome}
        </li>
      ))}
    </ul>
  )
}

export function Cartao(props: { titulo: string; subtitulo?: string; series?: Serie[]; children: ReactNode; tabela?: ReactNode; className?: string }) {
  return (
    <section className={`panel p-4 sm:p-5 ${props.className ?? ''}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-semibold">{props.titulo}</h2>
          {props.subtitulo && <p className="text-[13px] text-ink-3">{props.subtitulo}</p>}
        </div>
        {props.series && <Legenda series={props.series} />}
      </div>
      {props.children}
      {props.tabela && (
        <details className="mt-3 text-[13px]">
          <summary className="cursor-pointer text-accent">Ver dados em tabela</summary>
          <div className="mt-2 max-h-72 overflow-auto">{props.tabela}</div>
        </details>
      )}
    </section>
  )
}

interface Dados {
  dados: ({ rotulo: string } & Partial<Record<Serie, number>>)[]
  series: Serie[]
  descricao: string
}

export function BarrasAnuais({ dados, series, descricao }: Dados) {
  return (
    <div role="img" aria-label={descricao} className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dados} barGap={2} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-line)" />
          <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={{ stroke: 'var(--color-line-strong)' }} />
          <YAxis tick={EIXO} tickLine={false} axisLine={false} width={52} tickFormatter={compacto} />
          <Tooltip {...DICA} cursor={{ fill: 'var(--color-paper)' }} />
          {series.map((s) => (
            <Bar key={s} dataKey={s} name={SERIES[s].nome} fill={SERIES[s].cor} radius={[4, 4, 0, 0]} maxBarSize={44} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function LinhasMensais({ dados, series, descricao }: Dados) {
  return (
    <div role="img" aria-label={descricao} className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dados} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-line)" />
          <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={{ stroke: 'var(--color-line-strong)' }} minTickGap={24} />
          <YAxis tick={EIXO} tickLine={false} axisLine={false} width={52} tickFormatter={compacto} domain={[0, 'auto']} />
          <Tooltip {...DICA} />
          {series.map((s) => (
            <Line key={s} dataKey={s} name={SERIES[s].nome} stroke={SERIES[s].cor} strokeWidth={2} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
