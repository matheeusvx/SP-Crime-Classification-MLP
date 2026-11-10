import type { ReactNode } from 'react'
import type { ApiError } from '../api/client'

export function Carregando({ texto }: { texto: string }) {
  return (
    <p role="status" className="py-10 text-center text-sm text-ink-2">
      {texto}
    </p>
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
    <div role="alert" className="rounded-md border border-danger-line bg-danger-soft p-4 text-sm">
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
        <button type="button" className="btn btn-quiet mt-3" onClick={aoTentar}>
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export function Nota({ titulo, children }: { titulo?: string; children: ReactNode }) {
  return (
    <div className="rounded-md border border-note-line bg-note px-3.5 py-3 text-[13px] leading-relaxed text-ink-2">
      {titulo && <p className="font-semibold text-ink">{titulo}</p>}
      <div>{children}</div>
    </div>
  )
}

export function Cabecalho({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="mb-6 max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">{titulo}</h1>
      <p className="mt-2 text-[15px] text-ink-2">{children}</p>
    </div>
  )
}
