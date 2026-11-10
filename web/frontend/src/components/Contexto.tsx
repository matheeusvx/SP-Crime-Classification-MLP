import { useMemo } from 'react'
import type { ClassificacaoOk, EntradaClassificacao, Estatisticas, Metodologia, Opcoes } from '../api/types'
import { compacto, decimal, inteiro, percentual, rotuloCategoria } from '../format'
import { Cartao, Nota } from '../ui/base'
import { BarrasDestaque, Versus } from '../viz/basicos'

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
const DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const COR_FURTO = 'var(--color-furto)'
const COR_ROUBO = 'var(--color-roubo)'
const MINIMO_REGISTROS = 200

function somar<T extends { furtos: number; roubos: number }>(linhas: T[]) {
  return linhas.reduce((a, l) => ({ furtos: a.furtos + l.furtos, roubos: a.roubos + l.roubos }), { furtos: 0, roubos: 0 })
}

function resumo(c: { furtos: number; roubos: number }) {
  const t = c.furtos + c.roubos
  return `${inteiro(t)} boletins · ${percentual(c.roubos / t, 1)} roubos`
}

export function ContextoHistorico({ est, mes, dia, local }: { est: Estatisticas; mes?: number; dia?: number; local?: string | null }) {
  const porMes = useMemo(() => MESES.map((_, i) => somar(est.por_mes.filter((m) => m.mes === i + 1))), [est])
  const porDia = useMemo(() => DIAS.map((_, i) => somar(est.por_dia_mes.filter((d) => d.dia_semana === i))), [est])
  const categorias = useMemo(() => {
    const mapa = new Map<string, { furtos: number; roubos: number }>()
    for (const a of est.por_tipo_local)
      for (const c of a.categorias) {
        const atual = mapa.get(c.categoria) ?? { furtos: 0, roubos: 0 }
        mapa.set(c.categoria, { furtos: atual.furtos + c.furtos, roubos: atual.roubos + c.roubos })
      }
    return mapa
  }, [est])
  const nomeLocal = local === null ? 'Não informado' : local
  const dadosLocal = nomeLocal ? categorias.get(nomeLocal) : undefined

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Cartao titulo="Mês" subtitulo={mes ? resumo(porMes[mes - 1]) : 'Boletins por mês do fato, 2023 a 2025'}>
        <BarrasDestaque
          descricao="Boletins históricos por mês, com o mês selecionado em destaque"
          selecionado={mes ? String(mes) : undefined}
          itens={MESES.map((m, i) => ({ chave: String(i + 1), rotulo: m[0], valor: porMes[i].furtos + porMes[i].roubos, tag: compacto(porMes[i].furtos + porMes[i].roubos) }))}
        />
      </Cartao>
      <Cartao titulo="Dia da semana" subtitulo={dia !== undefined ? resumo(porDia[dia]) : 'Boletins por dia da semana, 2023 a 2025'}>
        <BarrasDestaque
          descricao="Boletins históricos por dia da semana, com o dia selecionado em destaque"
          selecionado={dia !== undefined ? String(dia) : undefined}
          itens={DIAS.map((d, i) => ({ chave: String(i), rotulo: d, valor: porDia[i].furtos + porDia[i].roubos, tag: compacto(porDia[i].furtos + porDia[i].roubos) }))}
        />
      </Cartao>
      <Cartao titulo="Tipo de local" subtitulo={nomeLocal ? rotuloCategoria(nomeLocal) : 'Composição dos boletins do local escolhido'}>
        <div className="flex flex-1 flex-col justify-center">
          {dadosLocal ? (
            <Versus
              key={nomeLocal}
              esquerda={{ nome: 'Furtos', valor: percentual(dadosLocal.furtos / (dadosLocal.furtos + dadosLocal.roubos), 1), detalhe: inteiro(dadosLocal.furtos), fracao: dadosLocal.furtos, cor: COR_FURTO }}
              direita={{ nome: 'Roubos', valor: percentual(dadosLocal.roubos / (dadosLocal.furtos + dadosLocal.roubos), 1), detalhe: inteiro(dadosLocal.roubos), fracao: dadosLocal.roubos, cor: COR_ROUBO }}
            />
          ) : (
            <p className="py-6 text-center text-sm text-ink-3">{nomeLocal ? 'Este local tem poucos boletins e aparece somado em “Demais categorias” no painel.' : 'Selecione um tipo de local para ver a composição.'}</p>
          )}
        </div>
      </Cartao>
    </div>
  )
}

function LinhaGrupo({ nome, grupo, geral }: { nome: string; grupo?: { n: number; accuracy: number }; geral: number }) {
  if (!grupo || grupo.n < MINIMO_REGISTROS)
    return (
      <div>
        <p className="text-sm font-medium">{nome}</p>
        <p className="text-[13px] text-ink-3">Poucos registros no teste de 2025 para uma leitura útil{grupo ? ` (${inteiro(grupo.n)})` : ''}.</p>
      </div>
    )
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-medium">{nome}</p>
        <p className="tabular text-sm font-semibold">{percentual(grupo.accuracy, 1)}</p>
      </div>
      <div className="relative mt-1.5 h-2 rounded-full bg-track" aria-hidden="true">
        <div className="barra-h h-2 rounded-full bg-accent" style={{ width: `${grupo.accuracy * 100}%` }} />
        <div className="absolute -top-1 h-4 w-0.5 rounded bg-ink" style={{ left: `${geral * 100}%` }} />
      </div>
      <p className="tabular mt-1 text-xs text-ink-3">{inteiro(grupo.n)} boletins de teste</p>
    </div>
  )
}

const GRUPO_BAIRRO: Record<string, [string, string]> = {
  reconhecido: ['frequente', 'Bairros frequentes'],
  raro: ['raro_conhecido', 'Bairros do grupo raro'],
  ausente: ['ausente', 'Bairro não informado'],
}

export function DesempenhoGrupo({ met, resultado, entrada }: { met: Metodologia; resultado: ClassificacaoOk; entrada: EntradaClassificacao }) {
  const geral = met.desempenho.teste_2025.accuracy
  const local = met.grupos_2025.tipo_local[entrada.tipo_local ?? '(AUSENTE)']
  const [chave, nomeBairro] = GRUPO_BAIRRO[resultado.grupos.bairro] ?? GRUPO_BAIRRO.reconhecido
  const administrativo = entrada.tipo_local === 'OUTROS' || entrada.tipo_local === null
  return (
    <Cartao titulo="Acurácia publicada em grupos semelhantes" subtitulo="Teste final de 2025. A marca vertical é a acurácia geral do modelo.">
      <div className="space-y-4">
        <LinhaGrupo nome={entrada.tipo_local ? rotuloCategoria(entrada.tipo_local) : 'Local não informado'} grupo={local} geral={geral} />
        <LinhaGrupo nome={nomeBairro} grupo={met.grupos_2025.condicao_bairro[chave]} geral={geral} />
      </div>
      <p className="mt-4 text-xs text-ink-3">Acurácia geral: {percentual(geral)}. Descreve o desempenho do grupo, não a confiança desta classificação específica.</p>
      {administrativo && (
        <div className="mt-3">
          <Nota>A auditoria indica que o resultado em “OUTROS” decorre da estrutura do modelo, com só 12 exemplos no treino; não é robustez demonstrada.</Nota>
        </div>
      )}
    </Cartao>
  )
}

export interface Cenario {
  id: number
  entrada: EntradaClassificacao
  resultado: ClassificacaoOk
}

export function descreverCenario(c: Cenario, opcoes: Opcoes) {
  const mes = opcoes.meses.find((m) => m.valor === c.entrada.mes)?.rotulo.slice(0, 3)
  const dia = opcoes.dias_semana.find((d) => d.valor === c.entrada.dia_semana)?.rotulo.slice(0, 3)
  const local = c.entrada.tipo_local ? rotuloCategoria(c.entrada.tipo_local) : 'Local não informado'
  return { titulo: `${c.entrada.bairro ?? 'Bairro não informado'}`, detalhe: `${mes} · ${dia} · ${local}` }
}

export function Cenarios(props: { cenarios: Cenario[]; ativo?: number; opcoes: Opcoes; aoEscolher: (id: number) => void; aoLimpar: () => void }) {
  const { cenarios, ativo, opcoes } = props
  return (
    <Cartao
      titulo="Comparar cenários"
      subtitulo="Classificações feitas nesta visita. Selecione uma para restaurar os campos."
      acao={
        <button type="button" className="text-[13px] font-medium text-accent hover:underline" onClick={props.aoLimpar}>
          Limpar
        </button>
      }
    >
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <BarrasDestaque
          altura="h-44"
          maximo={1}
          limiar={{ valor: 0.5, rotulo: 'Limiar 0,5' }}
          selecionado={ativo !== undefined ? String(ativo) : undefined}
          aoEscolher={(id) => props.aoEscolher(Number(id))}
          descricao="Score de roubo de cada cenário"
          itens={cenarios.map((c, i) => {
            const roubo = c.resultado.classe_estimada === 'ROUBO'
            return {
              chave: String(c.id),
              rotulo: `${i + 1}`,
              valor: c.resultado.scores_sigmoid.roubo,
              tag: decimal(c.resultado.scores_sigmoid.roubo),
              cor: roubo ? COR_ROUBO : COR_FURTO,
              corSuave: roubo ? 'var(--color-roubo-soft)' : 'var(--color-furto-soft)',
              descricao: `Cenário ${i + 1}: score de roubo ${decimal(c.resultado.scores_sigmoid.roubo)}`,
            }
          })}
        />
        <ol className="divide-y divide-line">
          {cenarios.map((c, i) => {
            const d = descreverCenario(c, opcoes)
            return (
              <li key={c.id}>
                <button type="button" onClick={() => props.aoEscolher(c.id)} className={`flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-soft ${c.id === ativo ? 'bg-accent-soft' : ''}`}>
                  <span className="tabular w-4 text-[13px] text-ink-3">{i + 1}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{d.titulo}</span>
                    <span className="block truncate text-xs text-ink-3">{d.detalhe}</span>
                  </span>
                  <span className="text-right">
                    <span className="block text-[13px] font-semibold">{c.resultado.classe_estimada}</span>
                    <span className="tabular block text-xs text-ink-3">roubo {decimal(c.resultado.scores_sigmoid.roubo)}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      </div>
      <p className="mt-3 text-xs text-ink-3">Scores não calibrados. Os cenários ficam só nesta aba e não são enviados nem armazenados.</p>
    </Cartao>
  )
}
