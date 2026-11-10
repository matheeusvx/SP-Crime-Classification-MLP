import { useCallback } from 'react'
import type { ReactNode } from 'react'
import { obterMetodologia, obterModelo } from '../api/client'
import type { Metricas, Metodologia, ModeloPublico, Referencia } from '../api/types'
import { DiagramaArquitetura, MatrizConfusao } from '../components/Metodologia'
import { Cabecalho, Carregando, MensagemErro, Nota } from '../components/Status'
import { decimal, inteiro, percentual } from '../format'
import { useResource } from '../hooks/useResource'

function Secao({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="panel scroll-mt-4 space-y-4 p-5 sm:p-6">
      <h2 id={`${id}-t`} className="text-lg font-semibold tracking-tight">
        {titulo}
      </h2>
      {children}
    </section>
  )
}

function Rolavel({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Tabela com rolagem horizontal">
      {children}
    </div>
  )
}

function Detalhes({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <details className="rounded-md border border-line px-3.5 py-2.5 text-sm">
      <summary className="cursor-pointer font-medium text-accent">{titulo}</summary>
      <div className="prose-block mt-2 text-ink-2">{children}</div>
    </details>
  )
}

function ComoFunciona({ modelo }: { modelo: ModeloPublico }) {
  const oculta = modelo.arquitetura.camadas_ocultas[0]
  const entradas = modelo.arquitetura.entradas
  return (
    <>
      <DiagramaArquitetura modelo={modelo} />
      <div className="prose-block max-w-3xl text-[15px] text-ink-2">
        <p>
          Uma <strong className="text-ink">Multilayer Perceptron</strong> é uma rede neural organizada em camadas. Cada camada combina os valores da
          anterior e, durante o treinamento, ajusta seus pesos para errar menos nos exemplos históricos.
        </p>
        <p>
          A rede recebe quatro informações: <strong className="text-ink">mês, dia da semana, tipo de local e bairro</strong>. Como são categorias, e não
          quantidades, cada valor vira uma coluna própria: “Via Pública” liga a coluna desse local e desliga as demais. Isso se chama One-Hot.
        </p>
        <p>
          A saída é um único número entre 0 e 1. Quando esse <strong className="text-ink">score</strong> alcança o{' '}
          <strong className="text-ink">limiar de decisão de 0,5</strong>, o registro é classificado como ROUBO; abaixo disso, como FURTO. O score não é a
          chance real de um crime ocorrer.
        </p>
      </div>
      <Detalhes titulo="Detalhes técnicos">
        <p>
          Parâmetros treináveis: {inteiro(modelo.arquitetura.parametros_treinaveis)}, sendo {inteiro(entradas * oculta)} pesos e {oculta} vieses na camada
          oculta, mais {oculta} pesos e 1 viés na saída.
        </p>
        <p>
          Treino com {modelo.otimizador} (taxa {decimal(modelo.taxa_aprendizado, 3)}), perda {modelo.funcao_perda}, lotes de {modelo.tamanho_lote} e{' '}
          {modelo.epocas} épocas fixas, em {inteiro(modelo.linhas_ajuste_2023)} boletins de 2023.
        </p>
        <p>
          Dos bairros observados em 2023, {modelo.bairros_com_coluna_propria} têm coluna própria por alcançarem {modelo.frequencia_minima_bairro} registros.
          Os demais dividem uma única coluna de “bairros raros”. O vocabulário e os pesos estão congelados na versão {modelo.versao_modelo}.
        </p>
      </Detalhes>
    </>
  )
}

const LINHAS_METRICAS: [string, keyof Metricas, 'pct' | 'dec'][] = [
  ['Accuracy', 'accuracy', 'pct'],
  ['Macro F1', 'macro_f1', 'pct'],
  ['Precision de roubo', 'precision_roubo', 'pct'],
  ['Recall de roubo', 'recall_roubo', 'pct'],
  ['Balanced accuracy', 'balanced_accuracy', 'pct'],
  ['AUC', 'auc', 'dec'],
  ['ECE (10 faixas)', 'ece10', 'pct'],
]

function Desempenho({ met }: { met: Metodologia }) {
  const { validacao_2024: val, teste_2025: teste } = met.desempenho
  const fmt = (v: number, t: 'pct' | 'dec') => (t === 'pct' ? percentual(v) : decimal(v, 4))
  return (
    <>
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <Rolavel>
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Métrica</th>
                  <th scope="col">Validação 2024</th>
                  <th scope="col">Teste 2025</th>
                </tr>
              </thead>
              <tbody>
                {LINHAS_METRICAS.map(([nome, chave, tipo]) => (
                  <tr key={chave}>
                    <th scope="row" className="font-normal">
                      {nome}
                    </th>
                    <td>{fmt(val[chave], tipo)}</td>
                    <td className="font-semibold">{fmt(teste[chave], tipo)}</td>
                  </tr>
                ))}
                <tr>
                  <th scope="row" className="font-normal">
                    Boletins
                  </th>
                  <td>{inteiro(val.n)}</td>
                  <td className="font-semibold">{inteiro(teste.n)}</td>
                </tr>
              </tbody>
            </table>
          </Rolavel>
          <p className="mt-3 text-[13px] text-ink-3">
            2024 foi usado durante o desenvolvimento para comparar alternativas. 2025 foi reservado à avaliação final do modelo já congelado. O ano também
            foi consultado em estatísticas exploratórias e na auditoria, portanto não serve como teste independente de uma versão futura.
          </p>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Matriz de confusão — teste 2025</h3>
          <MatrizConfusao m={teste} />
          <dl className="mt-3 space-y-2 text-sm text-ink-2">
            <div>
              <dt className="inline font-medium text-ink">Falsos positivos: </dt>
              <dd className="inline">furtos registrados que o modelo classificou como roubo ({inteiro(teste.fp)}).</dd>
            </div>
            <div>
              <dt className="inline font-medium text-ink">Falsos negativos: </dt>
              <dd className="inline">roubos registrados que o modelo classificou como furto ({inteiro(teste.fn)}).</dd>
            </div>
          </dl>
        </div>
      </div>
    </>
  )
}

function Arquiteturas({ met }: { met: Metodologia }) {
  return (
    <>
      <Rolavel>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Arquitetura</th>
              <th scope="col">Parâmetros</th>
              <th scope="col">Accuracy</th>
              <th scope="col">Macro F1</th>
              <th scope="col">Precision roubo</th>
              <th scope="col">Recall roubo</th>
              <th scope="col">Macro F1 médio</th>
            </tr>
          </thead>
          <tbody>
            {met.arquiteturas.map((a) => (
              <tr key={a.id}>
                <th scope="row" className={a.id === 'B64' ? 'font-semibold' : 'font-normal'}>
                  {a.nome}
                  {a.id === 'B64' ? ' (selecionada)' : ''}
                </th>
                <td>{inteiro(a.parametros)}</td>
                <td>{percentual(a.semente_42.accuracy)}</td>
                <td>{percentual(a.semente_42.macro_f1)}</td>
                <td>{percentual(a.semente_42.precision_roubo)}</td>
                <td>{percentual(a.semente_42.recall_roubo)}</td>
                <td>
                  {percentual(a.macro_f1_media)} <span className="text-ink-3">({a.n_sementes === 1 ? '1 semente' : `${a.n_sementes} sementes`})</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Rolavel>
      <p className="text-[13px] text-ink-3">Validação em 2024 ({inteiro(met.conjuntos[1].boletins)} boletins), semente 42, salvo na última coluna.</p>
      <div className="prose-block max-w-3xl text-[15px] text-ink-2">
        <p>
          As três arquiteturas ficaram praticamente empatadas, e a diferença não sustenta que uma seja superior. A Dense32 teve Macro F1 nominalmente maior,
          mas foi reajustada em uma só semente. A Dense64 → Dense32 alcançou mais recall de roubo, ao custo de mais falsos positivos.
        </p>
        <p>
          A Dense64 foi escolhida antes do teste de 2025 por decisão explícita do projeto, considerando a estabilidade em três sementes e a falta de ganho
          consistente com maior profundidade. Nenhuma alternativa foi comparada em 2025.
        </p>
      </div>
    </>
  )
}

function Referencias({ met }: { met: Metodologia }) {
  const { classe_majoritaria: maj, tabela_frequencias: tab, mlp } = met.referencias_2025
  const linhas: [string, Referencia][] = [
    ['Classe majoritária (sempre FURTO)', maj],
    ['Tabela de frequências (retrospectiva)', tab],
    ['MLP Dense64', mlp],
  ]
  return (
    <>
      <Rolavel>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Referência — teste 2025</th>
              <th scope="col">Accuracy</th>
              <th scope="col">Macro F1</th>
              <th scope="col">AUC</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map(([nome, r]) => (
              <tr key={nome}>
                <th scope="row" className="font-normal">
                  {nome}
                </th>
                <td>{percentual(r.accuracy)}</td>
                <td>{percentual(r.macro_f1)}</td>
                <td>{r.auc === undefined ? '—' : decimal(r.auc, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Rolavel>
      <p className="max-w-3xl text-[15px] text-ink-2">
        A MLP superou a classe majoritária, mas <strong className="text-ink">não demonstrou vantagem consistente</strong> sobre a tabela de frequências de
        roubo por tipo de local e bairro. Essa tabela foi construída retrospectivamente, como diagnóstico da auditoria posterior ao teste; não é um candidato
        validado previamente nem substitui o modelo.
      </p>
    </>
  )
}

function Limitacoes({ met }: { met: Metodologia }) {
  const n2025 = met.nivel_scores.find((n) => n.ano === 2025)!
  const itens: [string, string][] = [
    ['Scores não calibrados', `Em 2025, o score médio de roubo foi ${percentual(n2025.score_medio_roubo)}, enquanto ${percentual(n2025.prevalencia_roubo)} dos boletins eram roubos. Os valores superestimam a classe e não são chances.`],
    ['Mudanças ao longo do tempo', 'A proporção de roubos caiu de 44% em 2023 para 36% em 2025. O modelo foi treinado apenas com 2023, e os padrões de registro mudam.'],
    ['Possíveis proxies administrativos', '“OUTROS” e local ausente se relacionam com a Delegacia Eletrônica e podem indicar como o boletim foi preenchido, não onde o fato ocorreu.'],
    ['Bairros raros agrupados', 'Mais de mil bairros pouco frequentes dividem uma única coluna. Em via pública, esse grupo recebeu sempre a classe ROUBO em 2025, o que concentra falsos positivos.'],
    ['Grafia histórica dos bairros', 'Acentos e abreviações podem criar categorias diferentes para o mesmo bairro, com respostas diferentes. A aplicação não unifica essas grafias.'],
    ['Viés de seleção', 'Boletins com outras naturezas associadas foram excluídos, removendo proporcionalmente mais roubos. Fatos de 2025 registrados apenas em 2026 não estão cobertos.'],
    ['Sem validação para uso real', 'O modelo não foi validado para decisões policiais ou operacionais e não determina a natureza jurídica de um fato.'],
    ['Domínio restrito', 'Abrange apenas celulares subtraídos na capital paulista, e não todas as ocorrências criminais.'],
    ['Não prevê crimes', 'O modelo classifica características de um registro. Não prevê crimes futuros e não mede a segurança de lugares.'],
  ]
  return (
    <>
      <ul className="grid gap-x-8 gap-y-4 md:grid-cols-2">
        {itens.map(([t, d]) => (
          <li key={t}>
            <p className="text-[15px] font-semibold">{t}</p>
            <p className="text-sm text-ink-2">{d}</p>
          </li>
        ))}
      </ul>
      <Nota>
        Esta é uma demonstração acadêmica e não um sistema oficial da SSP-SP. Fonte pública original:{' '}
        <a className="text-accent underline" href="https://www.ssp.sp.gov.br/estatistica/consultas" target="_blank" rel="noreferrer">
          Consultas estatísticas da SSP-SP
        </a>
        .
      </Nota>
    </>
  )
}

export default function SobrePage() {
  const buscarMetodologia = useCallback((s: AbortSignal) => obterMetodologia(s), [])
  const metodologia = useResource(buscarMetodologia)
  const modelo = useResource(obterModelo)
  return (
    <>
      <Cabecalho titulo="Sobre o modelo">
        Como a rede neural funciona, como foi avaliada e o que ela não é capaz de fazer. A rede foi treinada com dados de 2023 e congelada antes do teste final.
      </Cabecalho>
      <div className="space-y-5">
        <Secao id="funcionamento" titulo="Como a MLP funciona">
          {modelo.recurso.estado === 'carregando' && <Carregando texto="Carregando arquitetura…" />}
          {modelo.recurso.estado === 'erro' && <MensagemErro erro={modelo.recurso.erro} aoTentar={modelo.recarregar} />}
          {modelo.recurso.estado === 'ok' && <ComoFunciona modelo={modelo.recurso.dados} />}
        </Secao>
        {metodologia.recurso.estado === 'carregando' && <Carregando texto="Carregando métricas…" />}
        {metodologia.recurso.estado === 'erro' && <MensagemErro erro={metodologia.recurso.erro} aoTentar={metodologia.recarregar} />}
        {metodologia.recurso.estado === 'ok' && (
          <>
            <Secao id="desempenho" titulo="Desempenho">
              <Desempenho met={metodologia.recurso.dados} />
            </Secao>
            <Secao id="arquiteturas" titulo="Arquiteturas experimentadas">
              <Arquiteturas met={metodologia.recurso.dados} />
            </Secao>
            <Secao id="referencias" titulo="Comparação com referências simples">
              <Referencias met={metodologia.recurso.dados} />
            </Secao>
            <Secao id="limitacoes" titulo="Limitações">
              <Limitacoes met={metodologia.recurso.dados} />
            </Secao>
          </>
        )}
      </div>
    </>
  )
}
