import { useState } from 'react'
import type { ReactNode } from 'react'
import { obterMetodologia, obterModelo } from '../api/client'
import type { ArquiteturaExperimento, Metodologia, Metricas, ModeloPublico, Referencia } from '../api/types'
import { decimal, inteiro, percentual } from '../format'
import { useResource } from '../hooks/useResource'
import { Cabecalho, Carregando, Cartao, MensagemErro, Numero, Revelar, Rotulo, Segmentado, atraso } from '../ui/base'
import { Rede } from '../viz/Rede'

const fmtInt = (n: number) => inteiro(Math.round(n))
const COR_2024 = 'var(--color-furto-soft)'
const COR_2025 = 'var(--color-accent)'

function Rolavel({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Tabela com rolagem horizontal">
      {children}
    </div>
  )
}

function ComoFunciona({ modelo }: { modelo: ModeloPublico }) {
  const oculta = modelo.arquitetura.camadas_ocultas[0]
  const entradas = modelo.arquitetura.entradas
  return (
    <>
      <Rede modelo={modelo} />
      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {[
          ['O que é', <>Uma <strong className="font-semibold text-ink">Multilayer Perceptron</strong> é uma rede organizada em camadas. No treinamento, ajusta seus pesos para errar menos nos exemplos históricos.</>],
          ['O que recebe', <>Quatro informações: <strong className="font-semibold text-ink">mês, dia da semana, tipo de local e bairro</strong>. Cada categoria vira uma coluna própria (One-Hot): “Via Pública” liga a coluna desse local e desliga as demais.</>],
          ['Como decide', <>A saída é um <strong className="font-semibold text-ink">score</strong> entre 0 e 1. A partir do <strong className="font-semibold text-ink">limiar de decisão de 0,5</strong>, o registro é classificado como ROUBO; abaixo, como FURTO. O score não é a chance real de um crime ocorrer.</>],
        ].map(([t, d], i) => (
          <div key={String(t)} className="rounded-xl bg-soft p-4">
            <p className="tabular text-xs font-semibold text-accent">0{i + 1}</p>
            <h3 className="text-[15px] font-semibold">{t}</h3>
            <p className="mt-1 text-sm text-ink-2">{d}</p>
          </div>
        ))}
      </div>
      <details className="mt-4 rounded-xl border border-line px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-accent">Detalhes técnicos</summary>
        <div className="prose-block mt-2 text-ink-2">
          <p>
            Parâmetros treináveis: {inteiro(modelo.arquitetura.parametros_treinaveis)}, sendo {inteiro(entradas * oculta)} pesos e {oculta} vieses na camada oculta, mais {oculta} pesos e 1 viés na saída.
          </p>
          <p>
            Treino com {modelo.otimizador} (taxa {decimal(modelo.taxa_aprendizado, 3)}), perda {modelo.funcao_perda}, lotes de {modelo.tamanho_lote} e {modelo.epocas} épocas fixas, em {inteiro(modelo.linhas_ajuste_2023)} boletins de 2023.
          </p>
          <p>
            Dos bairros observados em 2023, {modelo.bairros_com_coluna_propria} têm coluna própria por alcançarem {modelo.frequencia_minima_bairro} registros. Os demais dividem uma única coluna de “bairros raros”. O vocabulário e os pesos estão congelados na versão {modelo.versao_modelo}.
          </p>
        </div>
      </details>
    </>
  )
}

function Matriz({ m, ano }: { m: Metricas; ano: string }) {
  const furtos = m.tn + m.fp
  const roubos = m.fn + m.tp
  const celula = (rotulo: string, n: number, total: number, certo: boolean) => (
    <td className={`rounded-xl p-3 text-center transition-colors sm:p-4 ${certo ? 'bg-accent-soft' : 'bg-soft'}`}>
      <p className="tabular text-xl font-bold tracking-tight">
        <Numero valor={n} formato={fmtInt} />
      </p>
      <p className="tabular text-xs text-ink-2">{percentual(n / total, 1)} da linha</p>
      <p className="text-xs text-ink-3">{rotulo}</p>
    </td>
  )
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[19rem] border-separate border-spacing-1 text-[13px]">
        <caption className="sr-only">Matriz de confusão de {ano}</caption>
        <thead>
          <tr>
            <td />
            <th scope="col" className="pb-1 font-medium text-ink-2">Classificado como FURTO</th>
            <th scope="col" className="pb-1 font-medium text-ink-2">Classificado como ROUBO</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row" className="pr-2 text-left font-medium text-ink-2">Registrado como FURTO</th>
            {celula('acertos', m.tn, furtos, true)}
            {celula('falsos positivos', m.fp, furtos, false)}
          </tr>
          <tr>
            <th scope="row" className="pr-2 text-left font-medium text-ink-2">Registrado como ROUBO</th>
            {celula('falsos negativos', m.fn, roubos, false)}
            {celula('acertos', m.tp, roubos, true)}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

const METRICAS: [string, keyof Metricas][] = [
  ['Accuracy', 'accuracy'],
  ['Macro F1', 'macro_f1'],
  ['Precision de roubo', 'precision_roubo'],
  ['Recall de roubo', 'recall_roubo'],
  ['Balanced accuracy', 'balanced_accuracy'],
]

function BarraDupla({ a, b }: { a: number; b: number }) {
  return (
    <div className="space-y-1" aria-hidden="true">
      <div className="h-1.5 rounded-full bg-soft">
        <div className="barra-h h-1.5 rounded-full" style={{ width: `${a * 100}%`, background: COR_2024 }} />
      </div>
      <div className="h-1.5 rounded-full bg-soft">
        <div className="barra-h h-1.5 rounded-full" style={{ width: `${b * 100}%`, background: COR_2025, ...atraso(80) }} />
      </div>
    </div>
  )
}

function Desempenho({ met }: { met: Metodologia }) {
  const { validacao_2024: val, teste_2025: teste } = met.desempenho
  const [ano, setAno] = useState<2025 | 2024>(2025)
  const matriz = ano === 2025 ? teste : val
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Cartao titulo="Métricas" subtitulo="Validação de 2024 × teste final de 2025" acao={<div className="flex gap-3"><Rotulo cor={COR_2024}>2024</Rotulo><Rotulo cor={COR_2025}>2025</Rotulo></div>}>
        <Rolavel>
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Métrica</th>
                <th scope="col" className="w-[28%]"><span className="sr-only">Comparação visual</span></th>
                <th scope="col">Validação 2024</th>
                <th scope="col">Teste 2025</th>
              </tr>
            </thead>
            <tbody>
              {METRICAS.map(([nome, chave]) => (
                <tr key={chave}>
                  <th scope="row" className="font-normal">{nome}</th>
                  <td><BarraDupla a={val[chave]} b={teste[chave]} /></td>
                  <td>{percentual(val[chave])}</td>
                  <td className="font-semibold">{percentual(teste[chave])}</td>
                </tr>
              ))}
              <tr>
                <th scope="row" className="font-normal">AUC</th>
                <td />
                <td>{decimal(val.auc, 4)}</td>
                <td className="font-semibold">{decimal(teste.auc, 4)}</td>
              </tr>
              <tr>
                <th scope="row" className="font-normal">ECE (10 faixas)</th>
                <td />
                <td>{percentual(val.ece10)}</td>
                <td className="font-semibold">{percentual(teste.ece10)}</td>
              </tr>
              <tr>
                <th scope="row" className="font-normal">Boletins</th>
                <td />
                <td>{inteiro(val.n)}</td>
                <td className="font-semibold">{inteiro(teste.n)}</td>
              </tr>
            </tbody>
          </table>
        </Rolavel>
        <p className="mt-3 text-[13px] text-ink-3">
          2024 foi usado durante o desenvolvimento para comparar alternativas. 2025 foi reservado à avaliação final do modelo já congelado. O ano também foi consultado em estatísticas exploratórias e na auditoria, portanto não serve como teste independente de uma versão futura.
        </p>
      </Cartao>
      <Cartao titulo="Matriz de confusão" subtitulo={ano === 2025 ? 'Teste final de 2025' : 'Validação de 2024'} acao={<Segmentado legenda="Conjunto" nome="matriz" valor={ano} aoMudar={setAno} opcoes={[{ valor: 2025 as const, rotulo: '2025' }, { valor: 2024 as const, rotulo: '2024' }]} />}>
        <Matriz m={matriz} ano={String(ano)} />
        <dl className="mt-3 space-y-2 text-sm text-ink-2">
          <div>
            <dt className="inline font-medium text-ink">Falsos positivos: </dt>
            <dd className="inline">furtos registrados que o modelo classificou como roubo ({inteiro(matriz.fp)}).</dd>
          </div>
          <div>
            <dt className="inline font-medium text-ink">Falsos negativos: </dt>
            <dd className="inline">roubos registrados que o modelo classificou como furto ({inteiro(matriz.fn)}).</dd>
          </div>
        </dl>
      </Cartao>
    </div>
  )
}

function CartaoArquitetura({ a, ativo, aoEscolher }: { a: ArquiteturaExperimento; ativo: boolean; aoEscolher: () => void }) {
  return (
    <button type="button" aria-pressed={ativo} onClick={aoEscolher} className={`rounded-xl p-4 text-left transition-colors ${ativo ? 'bg-accent-soft ring-2 ring-accent' : 'bg-soft hover:bg-line'}`}>
      <p className="text-[15px] font-semibold">{a.nome}</p>
      <p className="tabular text-xs text-ink-3">{inteiro(a.parametros)} parâmetros</p>
      <p className="tabular mt-2 text-2xl font-bold tracking-tight">{percentual(a.semente_42.macro_f1)}</p>
      <p className="text-xs text-ink-3">Macro F1, semente 42</p>
    </button>
  )
}

function Arquiteturas({ met }: { met: Metodologia }) {
  const [id, setId] = useState('B64')
  const a = met.arquiteturas.find((x) => x.id === id)!
  return (
    <Cartao titulo="Arquiteturas experimentadas" subtitulo={`Validação em 2024, ${inteiro(met.conjuntos[1].boletins)} boletins. Selecione para detalhar.`}>
      <div className="grid gap-3 sm:grid-cols-3">
        {met.arquiteturas.map((x) => (
          <CartaoArquitetura key={x.id} a={x} ativo={x.id === id} aoEscolher={() => setId(x.id)} />
        ))}
      </div>
      <dl key={id} className="subir tabular mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ['Accuracy', percentual(a.semente_42.accuracy)],
          ['Precision de roubo', percentual(a.semente_42.precision_roubo)],
          ['Recall de roubo', percentual(a.semente_42.recall_roubo)],
          [`Macro F1 médio (${a.n_sementes === 1 ? '1 semente' : `${a.n_sementes} sementes`})`, percentual(a.macro_f1_media)],
        ].map(([r, v]) => (
          <div key={r}>
            <dt className="text-xs text-ink-3">{r}</dt>
            <dd className="text-lg font-bold">{v}</dd>
          </div>
        ))}
      </dl>
      <div className="prose-block mt-4 text-[15px] text-ink-2">
        <p>As três arquiteturas ficaram praticamente empatadas, e a diferença não sustenta que uma seja superior. A Dense32 teve Macro F1 nominalmente maior, mas foi reajustada em uma só semente. A Dense64 → Dense32 alcançou mais recall de roubo, ao custo de mais falsos positivos.</p>
        <p>A Dense64 foi escolhida antes do teste de 2025 por decisão explícita do projeto, considerando a estabilidade em três sementes e a falta de ganho consistente com maior profundidade. Nenhuma alternativa foi comparada em 2025.</p>
      </div>
    </Cartao>
  )
}

function Referencias({ met }: { met: Metodologia }) {
  const { classe_majoritaria: maj, tabela_frequencias: tab, mlp } = met.referencias_2025
  const linhas: [string, Referencia, boolean][] = [
    ['Classe majoritária (sempre FURTO)', maj, false],
    ['Tabela de frequências (retrospectiva)', tab, false],
    ['MLP Dense64', mlp, true],
  ]
  return (
    <Cartao titulo="Comparação com referências simples" subtitulo="Teste de 2025">
      <div className="space-y-3">
        {linhas.map(([nome, r, destaque], i) => (
          <div key={nome}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
              <span className={destaque ? 'font-semibold' : 'text-ink-2'}>{nome}</span>
              <span className="tabular text-ink-2">
                <strong className="font-semibold text-ink">{percentual(r.accuracy)}</strong> · F1 {percentual(r.macro_f1)} · AUC {r.auc === undefined ? '—' : decimal(r.auc, 4)}
              </span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-soft" aria-hidden="true">
              <div className="barra-h h-2 rounded-full" style={{ width: `${r.accuracy * 100}%`, background: destaque ? 'var(--color-accent)' : 'var(--color-line-strong)', ...atraso(i * 90) }} />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-[15px] text-ink-2">
        A MLP superou a classe majoritária, mas <strong className="font-semibold text-ink">não demonstrou vantagem consistente</strong> sobre a tabela de frequências de roubo por tipo de local e bairro. Essa tabela foi construída retrospectivamente, como diagnóstico da auditoria posterior ao teste; não é um candidato validado previamente nem substitui o modelo.
      </p>
    </Cartao>
  )
}

function FonteDados() {
  return (
    <p className="text-[13px] text-ink-3">
      Fonte pública original:{' '}
      <a className="font-medium text-accent hover:underline" href="https://www.ssp.sp.gov.br/estatistica/consultas" target="_blank" rel="noreferrer">
        Consultas estatísticas da SSP-SP
      </a>
    </p>
  )
}

export default function SobrePage() {
  const metodologia = useResource(obterMetodologia)
  const modelo = useResource(obterModelo)
  return (
    <>
      <Cabecalho titulo="Sobre o modelo">Como a rede neural funciona, como foi avaliada e o que ela não é capaz de fazer. A rede foi treinada com dados de 2023 e congelada antes do teste final.</Cabecalho>
      <div className="space-y-4">
        <Cartao titulo="Como a MLP funciona">
          {modelo.recurso.estado === 'carregando' && <Carregando texto="Carregando arquitetura…" />}
          {modelo.recurso.estado === 'erro' && <MensagemErro erro={modelo.recurso.erro} aoTentar={modelo.recarregar} />}
          {modelo.recurso.estado === 'ok' && <ComoFunciona modelo={modelo.recurso.dados} />}
        </Cartao>
        {metodologia.recurso.estado === 'carregando' && <Carregando texto="Carregando métricas…" />}
        {metodologia.recurso.estado === 'erro' && <MensagemErro erro={metodologia.recurso.erro} aoTentar={metodologia.recarregar} />}
        {metodologia.recurso.estado === 'ok' && (
          <>
            <Revelar>
              <Desempenho met={metodologia.recurso.dados} />
            </Revelar>
            <Revelar className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
              <Arquiteturas met={metodologia.recurso.dados} />
              <Referencias met={metodologia.recurso.dados} />
            </Revelar>
            <Revelar>
              <FonteDados />
            </Revelar>
          </>
        )}
      </div>
    </>
  )
}
