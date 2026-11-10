/** Dados de teste unitário: estrutura do contrato, sem relação com resultados reais. */
import { vi } from 'vitest'
import type { ClassificacaoOk, Estatisticas, Metodologia, ModeloPublico, Opcoes } from '../api/types'

export const opcoes: Opcoes = {
  versao_contrato: '1.1.0',
  versao_modelo: 'modelo-de-teste',
  meses: [
    { valor: 1, rotulo: 'Janeiro' },
    { valor: 5, rotulo: 'Maio' },
  ],
  dias_semana: [
    { valor: 0, rotulo: 'Segunda-feira' },
    { valor: 2, rotulo: 'Quarta-feira' },
  ],
  tipos_local: ['OUTROS', 'VIA PÚBLICA'],
  bairros: [
    { valor: 'BELA VISTA', grupo: 'frequente' },
    { valor: 'BRÁS DE TESTE', grupo: 'raro' },
    { valor: 'TATUAPE', grupo: 'frequente' },
    { valor: 'TATUAPÉ', grupo: 'frequente' },
  ],
  ausencia_permitida: ['tipo_local', 'bairro'],
}

export const sucesso: ClassificacaoOk = {
  status: 'ok',
  classe_estimada: 'FURTO',
  codigo_classe: 0,
  scores_sigmoid: { furto: 0.75, roubo: 0.25 },
  versao_modelo: 'modelo-de-teste',
  versao_contrato: '1.1.0',
  probabilidades_calibradas: false,
  avisos: [],
  erros: [],
  grupos: { tipo_local: 'reconhecido', bairro: 'reconhecido' },
  interpretacao_scores: 'Estimativas não calibradas de classificação; não são chance de crime futuro.',
}

const contagem = { furtos: 60, roubos: 40 }
export const estatisticas: Estatisticas = {
  fonte: { nome: 'SSP-SP teste', url: 'https://www.ssp.sp.gov.br/estatistica/consultas', recorte: 'Recorte.' },
  periodo: { inicio: '2023-01', fim: '2025-12' },
  total: { furtos: 120, roubos: 80 },
  por_ano: [
    { ano: 2023, ...contagem },
    { ano: 2024, ...contagem },
  ],
  por_mes: [
    { ano: 2023, mes: 1, ...contagem },
    { ano: 2024, mes: 1, ...contagem },
  ],
  por_tipo_local: [
    { ano: 2023, categorias: [{ categoria: 'VIA PÚBLICA', tipo: 'categoria', ...contagem }, { categoria: 'OUTROS', tipo: 'outros', furtos: 0, roubos: 0 }] },
    { ano: 2024, categorias: [{ categoria: 'VIA PÚBLICA', tipo: 'categoria', ...contagem }, { categoria: 'OUTROS', tipo: 'outros', furtos: 0, roubos: 0 }] },
  ],
  limiar_demais_categorias: 1000,
}

export const modelo: ModeloPublico = {
  versao_modelo: 'modelo-de-teste',
  versao_contrato: '1.1.0',
  arquitetura: { entradas: 299, camadas_ocultas: [64], ativacoes: ['relu', 'sigmoid'], parametros_treinaveis: 19265 },
  limiar: 0.5,
  rotulos: { '0': 'FURTO', '1': 'ROUBO' },
  atributos: ['mes', 'dia_semana', 'tipo_local', 'bairro'],
  colunas_por_atributo: { mes: 13, dia_semana: 8, tipo_local: 29, bairro: 249 },
  funcao_perda: 'binary_crossentropy',
  otimizador: 'Adam',
  taxa_aprendizado: 0.001,
  epocas: 3,
  tamanho_lote: 256,
  linhas_ajuste_2023: 100,
  frequencia_minima_bairro: 50,
  bairros_com_coluna_propria: 247,
}

const m = {
  n: 100, furtos: 60, roubos: 40, tn: 50, fp: 10, fn: 15, tp: 25, accuracy: 0.75, macro_f1: 0.7, balanced_accuracy: 0.7,
  precision_roubo: 0.7, recall_roubo: 0.6, f1_roubo: 0.6, precision_furto: 0.8, recall_furto: 0.8, f1_furto: 0.8,
  brier: 0.2, log_loss: 0.5, ece10: 0.08, auc: 0.74,
}
const ref = { accuracy: 0.7, macro_f1: 0.6, auc: 0.73 }
const arq = (id: string, nome: string) => ({
  id, nome, camadas: id, parametros: 10, n_sementes: 1, sementes: '42', macro_f1_media: 0.7, macro_f1_dp: null, recall_roubo_media: 0.6,
  semente_42: { accuracy: 0.7, macro_f1: 0.7, balanced_accuracy: 0.7, precision_roubo: 0.6, recall_roubo: 0.6, brier: 0.2, log_loss: 0.5 },
})
export const metodologia: Metodologia = {
  conjuntos: [
    { papel: 'Treino', ano: 2023, boletins: 1 },
    { papel: 'Validação', ano: 2024, boletins: 2 },
    { papel: 'Teste', ano: 2025, boletins: 3 },
  ],
  arquiteturas: [arq('B32', 'Dense32'), arq('B64', 'Dense64'), arq('B64_32', 'Dense64 → Dense32')],
  desempenho: { validacao_2024: m, teste_2025: m },
  referencias_2025: { classe_majoritaria: { accuracy: 0.6, macro_f1: 0.4 }, tabela_frequencias: ref, mlp: ref },
  referencias_2024: { tabela_frequencias: ref, mlp: ref },
  nivel_scores: [{ ano: 2025, prevalencia_roubo: 0.36, score_medio_roubo: 0.44 }],
}

export const resposta = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })

/** Falso `fetch` roteado por caminho; `rotas` substitui respostas específicas. */
export function simularApi(rotas: Record<string, () => Response | Promise<Response>> = {}) {
  const padrao: Record<string, () => Response> = {
    '/api/options': () => resposta(opcoes),
    '/api/statistics': () => resposta(estatisticas),
    '/api/model': () => resposta(modelo),
    '/api/methodology': () => resposta(metodologia),
    '/api/classify': () => resposta(sucesso),
  }
  const falso = vi.fn(async (url: RequestInfo | URL) => {
    const rota = { ...padrao, ...rotas }[String(url)]
    if (!rota) throw new TypeError('rota não simulada')
    return rota()
  })
  vi.stubGlobal('fetch', falso)
  return falso
}
