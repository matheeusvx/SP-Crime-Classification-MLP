import type { ClassificacaoOk, EntradaClassificacao, Estatisticas, Mensagem, Metodologia, ModeloPublico, Opcoes } from './types'

export type TipoErro = 'validacao' | 'indisponivel' | 'limite' | 'rede' | 'servidor'

export class ApiError extends Error {
  readonly tipo: TipoErro
  readonly erros: Mensagem[]

  constructor(tipo: TipoErro, mensagem: string, erros: Mensagem[] = []) {
    super(mensagem)
    this.tipo = tipo
    this.erros = erros
  }
}

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const TEMPO_LIMITE_MS = 20000

const MSG_REDE = 'Não foi possível comunicar com o servidor. Verifique a conexão e tente novamente.'
const MSG_INDISPONIVEL = 'O serviço está temporariamente indisponível. Nenhum resultado foi gerado.'
const MSG_SERVIDOR = 'O servidor respondeu de forma inesperada. Tente novamente em instantes.'

async function requisitar<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const tempo = AbortSignal.timeout(TEMPO_LIMITE_MS)
  const sinal = init.signal ? AbortSignal.any([init.signal, tempo]) : tempo
  let resposta: Response
  try {
    resposta = await fetch(`${BASE}${caminho}`, { ...init, signal: sinal })
  } catch (erro) {
    if (init.signal?.aborted) throw erro
    throw new ApiError('rede', MSG_REDE)
  }
  let corpo: unknown = null
  try {
    corpo = await resposta.json()
  } catch {
    throw new ApiError(resposta.status === 503 ? 'indisponivel' : 'servidor', resposta.status === 503 ? MSG_INDISPONIVEL : MSG_SERVIDOR)
  }
  if (resposta.ok) return corpo as T
  const dados = corpo as { erros?: Mensagem[]; mensagem?: string }
  if (resposta.status === 422 && dados.erros?.length) throw new ApiError('validacao', 'Revise os campos informados.', dados.erros)
  if (resposta.status === 429) throw new ApiError('limite', dados.mensagem ?? MSG_INDISPONIVEL)
  if (resposta.status === 503) throw new ApiError('indisponivel', dados.mensagem ?? MSG_INDISPONIVEL)
  throw new ApiError('servidor', MSG_SERVIDOR)
}

export const obterOpcoes = (signal?: AbortSignal) => requisitar<Opcoes>('/api/options', { signal })
export const obterModelo = (signal?: AbortSignal) => requisitar<ModeloPublico>('/api/model', { signal })
export const obterEstatisticas = (signal?: AbortSignal) => requisitar<Estatisticas>('/api/statistics', { signal })
export const obterMetodologia = (signal?: AbortSignal) => requisitar<Metodologia>('/api/methodology', { signal })

export const classificar = (entrada: EntradaClassificacao) =>
  requisitar<ClassificacaoOk>('/api/classify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entrada),
  })
