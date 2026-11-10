/** Espelho dos contratos publicados pela API (web/backend/app/schemas.py). */
export interface Mensagem {
  campo: string
  codigo: string
  mensagem: string
}

export interface EntradaClassificacao {
  mes: number
  dia_semana: number
  tipo_local: string | null
  bairro: string | null
}

export interface ClassificacaoOk {
  status: 'ok'
  classe_estimada: 'FURTO' | 'ROUBO'
  codigo_classe: 0 | 1
  scores_sigmoid: { furto: number; roubo: number }
  versao_modelo: string
  versao_contrato: string
  probabilidades_calibradas: false
  avisos: Mensagem[]
  erros: Mensagem[]
  grupos: Record<string, string>
  interpretacao_scores: string
}

export interface OpcaoNumerica {
  valor: number
  rotulo: string
}

export interface OpcaoBairro {
  valor: string
  grupo: 'frequente' | 'raro'
}

export interface Opcoes {
  versao_contrato: string
  versao_modelo: string
  meses: OpcaoNumerica[]
  dias_semana: OpcaoNumerica[]
  tipos_local: string[]
  bairros: OpcaoBairro[]
  ausencia_permitida: string[]
}

export interface ModeloPublico {
  versao_modelo: string
  versao_contrato: string
  arquitetura: {
    entradas: number
    camadas_ocultas: number[]
    ativacoes: string[]
    parametros_treinaveis: number
  }
  limiar: number
  rotulos: Record<string, string>
  atributos: string[]
  colunas_por_atributo: Record<string, number>
  funcao_perda: string
  otimizador: string
  taxa_aprendizado: number
  epocas: number
  tamanho_lote: number
  linhas_ajuste_2023: number
  frequencia_minima_bairro: number
  bairros_com_coluna_propria: number
}

export interface Contagem {
  furtos: number
  roubos: number
}

export interface CategoriaLocal extends Contagem {
  categoria: string
  tipo: 'categoria' | 'outros' | 'ausente' | 'demais'
}

export interface Estatisticas {
  fonte: { nome: string; url: string; recorte: string }
  periodo: { inicio: string; fim: string }
  total: Contagem
  por_ano: (Contagem & { ano: number })[]
  por_mes: (Contagem & { ano: number; mes: number })[]
  por_tipo_local: { ano: number; categorias: CategoriaLocal[] }[]
  limiar_demais_categorias: number
}

export interface Metricas {
  n: number
  furtos: number
  roubos: number
  tn: number
  fp: number
  fn: number
  tp: number
  accuracy: number
  macro_f1: number
  balanced_accuracy: number
  precision_roubo: number
  recall_roubo: number
  f1_roubo: number
  precision_furto: number
  recall_furto: number
  f1_furto: number
  brier: number
  log_loss: number
  ece10: number
  auc: number
}

export interface Referencia {
  accuracy: number
  macro_f1: number
  auc?: number
  recall_roubo?: number
}

export interface ArquiteturaExperimento {
  id: string
  nome: string
  camadas: string
  parametros: number
  semente_42: {
    accuracy: number
    macro_f1: number
    balanced_accuracy: number
    precision_roubo: number
    recall_roubo: number
    brier: number
    log_loss: number
  }
  n_sementes: number
  sementes: string
  macro_f1_media: number
  macro_f1_dp: number | null
  recall_roubo_media: number
}

export interface Metodologia {
  conjuntos: { papel: string; ano: number; boletins: number }[]
  arquiteturas: ArquiteturaExperimento[]
  desempenho: { validacao_2024: Metricas; teste_2025: Metricas }
  referencias_2025: { classe_majoritaria: Referencia; tabela_frequencias: Referencia; mlp: Referencia }
  referencias_2024: { tabela_frequencias: Referencia; mlp: Referencia }
  nivel_scores: { ano: number; prevalencia_roubo: number; score_medio_roubo: number }[]
}
