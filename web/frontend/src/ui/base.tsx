import { useEffect, useRef } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import type { ApiError } from '../api/client'
import { useContagem } from '../hooks/useMotion'

export const atraso = (ms: number) => ({ '--atraso': `${ms}ms` }) as CSSProperties

/** Revela o conteúdo ao entrar na área visível. */
export function Revelar({ children, ms = 0, className = '' }: { children: ReactNode; ms?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current!
    if (typeof IntersectionObserver !== 'function') return el.classList.add('visivel')
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.classList.add('visivel')
          obs.disconnect()
        }
      },
      { rootMargin: '0px 0px -5% 0px' },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return (
    <div ref={ref} className={`revelar ${className}`} style={atraso(ms)}>
      {children}
    </div>
  )
}

export function Numero({ valor, formato }: { valor: number; formato: (n: number) => string }) {
  return <>{formato(useContagem(valor))}</>
}

export function Cartao(props: { titulo?: string; subtitulo?: string; acao?: ReactNode; children: ReactNode; className?: string; tabela?: ReactNode }) {
  return (
    <section className={`card flex flex-col p-5 sm:p-6 ${props.className ?? ''}`}>
      {(props.titulo || props.acao) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div>
            {props.titulo && <h2 className="text-[17px] font-semibold tracking-tight">{props.titulo}</h2>}
            {props.subtitulo && <p className="mt-0.5 text-[13px] text-ink-3">{props.subtitulo}</p>}
          </div>
          {props.acao}
        </div>
      )}
      {props.children}
      {props.tabela && (
        <details className="mt-3 text-[13px]">
          <summary className="cursor-pointer font-medium text-accent">Ver dados em tabela</summary>
          <div className="mt-2 max-h-72 overflow-auto">{props.tabela}</div>
        </details>
      )}
    </section>
  )
}

export function Segmentado<T extends string | number>(props: {
  legenda: string
  nome: string
  opcoes: { valor: T; rotulo: string }[]
  valor: T
  aoMudar: (v: T) => void
}) {
  const n = props.opcoes.length
  const i = props.opcoes.findIndex((o) => o.valor === props.valor)
  return (
    <fieldset>
      <legend className="mb-1.5 text-[13px] font-medium text-ink-3">{props.legenda}</legend>
      <div className="relative grid rounded-xl bg-surface p-1 shadow-sm" style={{ gridTemplateColumns: `repeat(${n}, minmax(3.75rem, 1fr))` }}>
        <span
          aria-hidden="true"
          className="transicao-pilula absolute inset-y-1 left-1 rounded-lg bg-accent"
          style={{ width: `calc((100% - 0.5rem) / ${n})`, transform: `translateX(${i * 100}%)` }}
        />
        {props.opcoes.map((o) => (
          <label
            key={o.valor}
            className={`relative z-[1] cursor-pointer rounded-lg px-3 py-1.5 text-center text-sm font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${
              o.valor === props.valor ? 'text-white' : 'text-ink-2 hover:text-ink'
            }`}
          >
            <input type="radio" className="sr-only" name={props.nome} checked={o.valor === props.valor} onChange={() => props.aoMudar(o.valor)} />
            {o.rotulo}
          </label>
        ))}
      </div>
    </fieldset>
  )
}

export function Carregando({ texto }: { texto: string }) {
  return (
    <div role="status" className="py-10">
      <div className="esqueleto mx-auto h-2 w-40 rounded-full" />
      <p className="mt-3 text-center text-sm text-ink-3">{texto}</p>
    </div>
  )
}

const TITULOS: Record<ApiError['tipo'], string> = {
  validacao: 'Revise os campos',
  indisponivel: 'Serviço indisponível',
  limite: 'Limite de uso atingido',
  rede: 'Falha de comunicação',
  servidor: 'Erro no servidor',
}

export function MensagemErro({ erro, aoTentar }: { erro: ApiError; aoTentar?: () => void }) {
  return (
    <div role="alert" className="subir rounded-xl border border-danger-line bg-danger-soft p-4 text-sm">
      <p className="font-semibold text-danger">{TITULOS[erro.tipo]}</p>
      <p className="mt-1 text-ink-2">{erro.message}</p>
      {erro.erros.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-2">
          {erro.erros.map((e) => (
            <li key={`${e.campo}-${e.codigo}`}>{e.mensagem}</li>
          ))}
        </ul>
      )}
      {aoTentar && (
        <button type="button" className="btn btn-quiet mt-3 bg-surface" onClick={aoTentar}>
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export function Nota({ titulo, children }: { titulo?: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-note-line bg-note px-3.5 py-3 text-[13px] leading-relaxed text-ink-2">
      {titulo && <p className="font-semibold text-ink">{titulo}</p>}
      <div>{children}</div>
    </div>
  )
}

export function Cabecalho({ titulo, children, lateral }: { titulo: string; children: ReactNode; lateral?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-[26px] font-bold tracking-tight sm:text-[30px]">{titulo}</h1>
        <p className="mt-1.5 text-[15px] text-ink-2">{children}</p>
      </div>
      {lateral}
    </div>
  )
}

export function Rotulo({ cor, children }: { cor: string; children: ReactNode }) {
  return (
    <span className="flex items-center gap-1.5 text-[13px] text-ink-2">
      <span aria-hidden="true" className="inline-block size-2 rounded-full" style={{ background: cor }} />
      {children}
    </span>
  )
}
