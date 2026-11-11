import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { compacto, inteiro } from '../format'
import { movimentoReduzido } from '../hooks/useMotion'

export type Serie = 'furtos' | 'roubos'

export const SERIES: Record<Serie, { nome: string; cor: string }> = {
  furtos: { nome: 'Furtos', cor: 'var(--color-furto)' },
  roubos: { nome: 'Roubos', cor: 'var(--color-roubo)' },
}

const EIXO = { fontSize: 12, fill: 'var(--color-ink-3)' }

interface DicaProps {
  active?: boolean
  label?: string | number
  payload?: readonly { dataKey?: unknown; value?: unknown }[]
}

function Dica({ active, payload, label }: DicaProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl bg-ink px-3 py-2 text-[13px] text-white shadow-lg">
      <p className="font-medium opacity-75">{label}</p>
      {payload.map((p) => {
        const s = SERIES[p.dataKey as Serie]
        return (
          <p key={s.nome} className="tabular flex items-center justify-between gap-5">
            <span className="flex items-center gap-1.5">
              <span className="inline-block size-2 rounded-full" style={{ background: s.cor }} />
              {s.nome}
            </span>
            <strong className="font-semibold">{inteiro(Number(p.value))}</strong>
          </p>
        )
      })}
    </div>
  )
}

interface Dados {
  dados: ({ rotulo: string } & Partial<Record<Serie, number>>)[]
  series: Serie[]
  descricao: string
}

export function AreaMensal({ dados, series, descricao }: Dados) {
  return (
    <div role="img" aria-label={descricao} className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={dados} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s} id={`grad-${s}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={SERIES[s].cor} stopOpacity={0.2} />
                <stop offset="1" stopColor={SERIES[s].cor} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid vertical={false} stroke="var(--color-line)" />
          <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={false} minTickGap={28} />
          <YAxis tick={EIXO} tickLine={false} axisLine={false} width={52} tickFormatter={compacto} domain={[0, 'auto']} />
          <Tooltip content={<Dica />} cursor={{ stroke: 'var(--color-accent)', strokeWidth: 26, strokeOpacity: 0.08 }} />
          {series.map((s) => (
            <Area
              key={s}
              dataKey={s}
              name={SERIES[s].nome}
              type="monotone"
              stroke={SERIES[s].cor}
              strokeWidth={2.25}
              fill={`url(#grad-${s})`}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
              isAnimationActive={!movimentoReduzido()}
              animationDuration={800}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
