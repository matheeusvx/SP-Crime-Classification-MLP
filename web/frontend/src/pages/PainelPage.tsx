import { useMemo, useState } from 'react'
import { obterEstatisticas } from '../api/client'
import type { CategoriaLocal, Contagem, Estatisticas } from '../api/types'
import { compacto, inteiro, MESES_CURTOS, percentual, rotuloCategoria } from '../format'
import { useResource } from '../hooks/useResource'
import { Cabecalho, Carregando, Cartao, MensagemErro, Nota, Numero, Revelar, Rotulo, Segmentado, atraso } from '../ui/base'
import { Faisca, MapaCalor, Medidor } from '../viz/basicos'
import { AreaMensal, BarrasAnuais, SERIES } from '../viz/Graficos'
import type { Serie } from '../viz/Graficos'

type FiltroAno = 'todos' | number
type FiltroTipo = 'ambos' | Serie

const fmtPct1 = (n: number) => percentual(n, 1)
const fmtInt = (n: number) => inteiro(Math.round(n))

function Legenda({ series }: { series: Serie[] }) {
  if (series.length < 2) return null
  return (
    <div className="flex gap-4">
      {series.map((s) => (
        <Rotulo key={s} cor={SERIES[s].cor}>
          {SERIES[s].nome}
        </Rotulo>
      ))}
    </div>
  )
}

function Variacao({ atual, anterior, ano }: { atual: number; anterior?: number; ano: FiltroAno }) {
  if (ano === 'todos' || !anterior) return null
  const v = atual / anterior - 1
  return (
    <span className="tabular rounded-md bg-soft px-1.5 py-0.5 text-xs font-medium text-ink-2" title={`Em relação a ${ano - 1}`}>
      {v >= 0 ? '↑' : '↓'} {percentual(Math.abs(v), 1)} <span className="font-normal text-ink-3">vs {ano - 1}</span>
    </span>
  )
}

function TabelaContagem({ primeira, linhas }: { primeira: string; linhas: ({ rotulo: string } & Contagem)[] }) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th scope="col">{primeira}</th>
          <th scope="col">Furtos</th>
          <th scope="col">Roubos</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l) => (
          <tr key={l.rotulo}>
            <th scope="row" className="font-normal">
              {l.rotulo}
            </th>
            <td>{inteiro(l.furtos)}</td>
            <td>{inteiro(l.roubos)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function agregarLocais(est: Estatisticas, ano: FiltroAno): CategoriaLocal[] {
  const mapa = new Map<string, CategoriaLocal>()
  for (const f of est.por_tipo_local.filter((a) => ano === 'todos' || a.ano === ano))
    for (const c of f.categorias) {
      const atual = mapa.get(c.categoria) ?? { ...c, furtos: 0, roubos: 0 }
      mapa.set(c.categoria, { ...atual, furtos: atual.furtos + c.furtos, roubos: atual.roubos + c.roubos })
    }
  return [...mapa.values()]
}

function BarrasLocal({ categorias, series }: { categorias: CategoriaLocal[]; series: Serie[] }) {
  const valor = (c: CategoriaLocal) => series.reduce((s, k) => s + c[k], 0)
  const ordenadas = [...categorias].sort((a, b) => Number(a.tipo === 'demais') - Number(b.tipo === 'demais') || valor(b) - valor(a))
  const maximo = Math.max(...ordenadas.map(valor), 1)
  return (
    <ul className="space-y-1">
      {ordenadas.map((c, i) => (
        <li key={c.categoria} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-soft sm:grid-cols-[11.5rem_minmax(0,1fr)_4.5rem]">
          <span className="truncate text-ink-2">
            {rotuloCategoria(c.categoria)}
            {(c.tipo === 'outros' || c.tipo === 'ausente') && (
              <span aria-label="com ressalva" title="Ver ressalva abaixo">
                {' '}
                *
              </span>
            )}
          </span>
          <span className="tabular text-right font-semibold sm:order-last">{compacto(valor(c))}</span>
          <div className="col-span-2 mt-1 flex h-2 gap-0.5 sm:col-span-1 sm:mt-0" title={series.map((s) => `${SERIES[s].nome}: ${inteiro(c[s])}`).join(' · ')}>
            {series.map((s) => (
              <div key={s} className="barra-h transicao-largura min-w-px rounded-full" style={{ width: `${(c[s] / maximo) * 100}%`, background: SERIES[s].cor, ...atraso(i * 40) }} />
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Mini(props: { rotulo: string; serie: Serie; total: Contagem; valores: number[]; anterior?: number; ano: FiltroAno }) {
  const soma = props.total.furtos + props.total.roubos
  const valor = props.total[props.serie]
  return (
    <section className="card flex-1 p-5">
      <p className="text-sm text-ink-2">{props.rotulo}</p>
      <div className="mt-0.5 flex flex-wrap items-center gap-2">
        <p className="tabular text-[26px] font-bold tracking-tight">
          <Numero valor={valor} formato={fmtInt} />
        </p>
        <Variacao atual={valor} anterior={props.anterior} ano={props.ano} />
      </div>
      <p className="tabular text-[13px] text-ink-3">
        <Numero valor={valor / soma} formato={fmtPct1} /> dos boletins
      </p>
      <div className="mt-2">
        <Faisca valores={props.valores} cor={SERIES[props.serie].cor} />
      </div>
    </section>
  )
}

function Painel({ est }: { est: Estatisticas }) {
  const [ano, setAno] = useState<FiltroAno>('todos')
  const [tipo, setTipo] = useState<FiltroTipo>('ambos')
  const series: Serie[] = tipo === 'ambos' ? ['furtos', 'roubos'] : [tipo]

  const total = useMemo<Contagem>(() => (ano === 'todos' ? est.total : est.por_ano.find((a) => a.ano === ano)!), [ano, est])
  const anterior = ano === 'todos' ? undefined : est.por_ano.find((a) => a.ano === ano - 1)
  const soma = total.furtos + total.roubos
  const anuais = est.por_ano.map((a) => ({ rotulo: String(a.ano), furtos: a.furtos, roubos: a.roubos }))
  const meses = est.por_mes.filter((m) => ano === 'todos' || m.ano === ano)
  const mensais = meses.map((m) => ({ rotulo: `${MESES_CURTOS[m.mes - 1]}/${String(m.ano).slice(2)}`, furtos: m.furtos, roubos: m.roubos }))
  const locais = useMemo(() => agregarLocais(est, ano), [est, ano])
  const nomePeriodo = ano === 'todos' ? '2023 a 2025' : String(ano)
  const unidade = tipo === 'ambos' ? 'boletins' : SERIES[tipo].nome.toLowerCase()

  const matriz = useMemo(() => {
    const m = Array.from({ length: 7 }, () => Array.from({ length: 12 }, () => 0))
    for (const d of est.por_dia_mes) if (ano === 'todos' || d.ano === ano) m[d.dia_semana][d.mes - 1] += series.reduce((s, k) => s + d[k], 0)
    return m
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est, ano, tipo])

  const dadosSerie = (d: { rotulo: string; furtos: number; roubos: number }[]) => d.map((x) => ({ rotulo: x.rotulo, ...Object.fromEntries(series.map((s) => [s, x[s]])) }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
        <Segmentado legenda="Ano" nome="ano" valor={ano} aoMudar={setAno} opcoes={[{ valor: 'todos' as FiltroAno, rotulo: 'Todos' }, ...est.por_ano.map((a) => ({ valor: a.ano as FiltroAno, rotulo: String(a.ano) }))]} />
        <Segmentado legenda="Tipo de ocorrência" nome="tipo" valor={tipo} aoMudar={setTipo} opcoes={[{ valor: 'ambos' as FiltroTipo, rotulo: 'Ambos' }, { valor: 'furtos' as FiltroTipo, rotulo: 'Furtos' }, { valor: 'roubos' as FiltroTipo, rotulo: 'Roubos' }]} />
        <p className="ml-auto text-right text-[13px] text-ink-3">
          Janeiro de 2023 a dezembro de 2025 ·{' '}
          <a className="font-medium text-accent hover:underline" href={est.fonte.url} target="_blank" rel="noreferrer">
            Fonte: SSP-SP
          </a>
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="card p-5 sm:p-6 lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm text-ink-2">Boletins elegíveis</p>
              <div className="flex flex-wrap items-center gap-2">
                <p className="tabular text-[32px] font-bold leading-tight tracking-tight">
                  <Numero valor={soma} formato={fmtInt} />
                </p>
                <Variacao atual={soma} anterior={anterior && anterior.furtos + anterior.roubos} ano={ano} />
              </div>
              <p className="text-[13px] text-ink-3">Registros por mês do fato, {nomePeriodo}</p>
            </div>
            <Legenda series={series} />
          </div>
          <div className="mt-3">
            <AreaMensal dados={dadosSerie(mensais)} series={series} descricao={`Série mensal de ${nomePeriodo}. Os valores estão disponíveis na tabela abaixo do gráfico.`} />
          </div>
          <details className="mt-2 text-[13px]">
            <summary className="cursor-pointer font-medium text-accent">Ver dados em tabela</summary>
            <div className="mt-2 max-h-72 overflow-auto">
              <TabelaContagem primeira="Mês" linhas={mensais} />
            </div>
          </details>
        </section>
        <div className="flex flex-col gap-4">
          <Mini rotulo="Furtos" serie="furtos" total={total} valores={meses.map((m) => m.furtos)} anterior={anterior?.furtos} ano={ano} />
          <Mini rotulo="Roubos" serie="roubos" total={total} valores={meses.map((m) => m.roubos)} anterior={anterior?.roubos} ano={ano} />
        </div>
      </div>

      <Nota>Os gráficos mostram quantidades históricas registradas, por ano do fato. Não são previsões de criminalidade nem indicam risco.</Nota>

      <Revelar className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Cartao titulo="Distribuição das classes" subtitulo={`${nomePeriodo}. Não é afetada pelo filtro de tipo.`}>
          <Medidor
            segmentos={[
              { nome: 'furtos', valor: total.furtos, cor: SERIES.furtos.cor },
              { nome: 'roubos', valor: total.roubos, cor: SERIES.roubos.cor },
            ]}
            descricao={`Furtos ${percentual(total.furtos / soma, 1)}, roubos ${percentual(total.roubos / soma, 1)}`}
          >
            <p className="text-xs text-ink-3">Roubos</p>
            <p className="tabular text-2xl font-bold tracking-tight">
              <Numero valor={total.roubos / soma} formato={fmtPct1} />
            </p>
          </Medidor>
          <div className="mt-3 flex justify-center gap-4">
            <Rotulo cor={SERIES.furtos.cor}>Furtos {percentual(total.furtos / soma, 1)}</Rotulo>
            <Rotulo cor={SERIES.roubos.cor}>Roubos {percentual(total.roubos / soma, 1)}</Rotulo>
          </div>
          <div className="mt-4 border-t border-line pt-3">
            <h3 className="mb-1 text-[13px] font-medium text-ink-2">Participação de roubos por ano</h3>
            <dl className="tabular space-y-1 text-sm">
              {est.por_ano.map((a) => (
                <div key={a.ano} className="flex justify-between">
                  <dt className="text-ink-2">{a.ano}</dt>
                  <dd className="font-medium">{percentual(a.roubos / (a.furtos + a.roubos), 1)}</dd>
                </div>
              ))}
            </dl>
          </div>
        </Cartao>
        <Cartao
          className="lg:col-span-2"
          titulo="Mês e dia da semana"
          subtitulo={`${inteiro(matriz.flat().reduce((a, b) => a + b, 0))} ${unidade}, ${nomePeriodo}. Cores mais fortes indicam mais registros.`}
          tabela={
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Dia</th>
                  {MESES_CURTOS.map((m) => (
                    <th key={m} scope="col">
                      {m}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matriz.map((l, d) => (
                  <tr key={d}>
                    <th scope="row" className="font-normal">
                      {['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][d]}
                    </th>
                    {l.map((v, m) => (
                      <td key={m}>{inteiro(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          <MapaCalor key={`${ano}-${tipo}`} valores={matriz} unidade={unidade} />
          <p className="mt-2 text-xs text-ink-3">O total de cada célula depende de quantas vezes aquele dia ocorreu no mês. Volume de registros não indica risco.</p>
        </Cartao>
      </Revelar>

      <Revelar className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <Cartao className="lg:col-span-2" titulo="Evolução anual" subtitulo="Compara sempre os três anos; não é afetada pelo filtro de ano." acao={<Legenda series={series} />}>
          <BarrasAnuais dados={dadosSerie(anuais)} series={series} descricao={`Barras por ano: ${anuais.map((a) => `${a.rotulo}, ${inteiro(a.furtos)} furtos e ${inteiro(a.roubos)} roubos`).join('; ')}.`} />
          <div className="mt-4 flex-1 border-t border-line pt-2">
            <TabelaContagem primeira="Ano" linhas={anuais} />
          </div>
        </Cartao>
        <Cartao className="lg:col-span-3" titulo="Distribuição por tipo de local" subtitulo={`${nomePeriodo}. Barras na mesma escala.`} acao={<Legenda series={series} />} tabela={<TabelaContagem primeira="Tipo de local" linhas={locais.map((c) => ({ ...c, rotulo: rotuloCategoria(c.categoria) }))} />}>
          <BarrasLocal categorias={locais} series={series} />
          <div className="mt-3 space-y-2">
            <Nota titulo="* Ressalva sobre “OUTROS” e “Não informado”">
              Parte desses registros está associada ao preenchimento administrativo da Delegacia Eletrônica. Em 2024, os registros sem local deram lugar a “OUTROS”, o que sugere mudança de preenchimento, e não mudança nos lugares dos fatos.
            </Nota>
            <p className="text-[13px] text-ink-3">“Demais categorias” soma os tipos de local com menos de {inteiro(est.limiar_demais_categorias)} boletins nos três anos.</p>
          </div>
        </Cartao>
      </Revelar>

      <p className="text-[13px] text-ink-3">
        {est.fonte.nome}. {est.fonte.recorte} Fatos de 2025 registrados apenas em 2026 não estão incluídos. Boletins com outras naturezas associadas foram excluídos, o que remove proporcionalmente mais roubos.
      </p>
    </div>
  )
}

export default function PainelPage() {
  const { recurso, recarregar } = useResource(obterEstatisticas)
  return (
    <>
      <Cabecalho titulo="Painel histórico">Distribuição dos boletins elegíveis de celulares subtraídos no município de São Paulo, usados no projeto.</Cabecalho>
      {recurso.estado === 'carregando' && <Carregando texto="Carregando estatísticas…" />}
      {recurso.estado === 'erro' && <MensagemErro erro={recurso.erro} aoTentar={recarregar} />}
      {recurso.estado === 'ok' && <Painel est={recurso.dados} />}
    </>
  )
}
