import { useMemo, useState } from 'react'
import { obterEstatisticas } from '../api/client'
import type { CategoriaLocal, Contagem, Estatisticas } from '../api/types'
import { BarrasAnuais, Cartao, LinhasMensais, SERIES } from '../components/Graficos'
import type { Serie } from '../components/Graficos'
import { Cabecalho, Carregando, MensagemErro, Nota } from '../components/Status'
import { compacto, inteiro, MESES_CURTOS, percentual, rotuloCategoria } from '../format'
import { useResource } from '../hooks/useResource'

type FiltroAno = 'todos' | number
type FiltroTipo = 'ambos' | Serie

function Opcoes<T extends string | number>(props: { legenda: string; nome: string; opcoes: { valor: T; rotulo: string }[]; valor: T; aoMudar: (v: T) => void }) {
  return (
    <fieldset>
      <legend className="mb-1 text-[13px] font-medium text-ink-2">{props.legenda}</legend>
      <div className="inline-flex flex-wrap rounded-md border border-line-strong bg-surface p-0.5">
        {props.opcoes.map((o) => (
          <label
            key={o.valor}
            className={`cursor-pointer rounded px-3 py-1.5 text-sm has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
              o.valor === props.valor ? 'bg-accent-soft font-medium text-accent-dark' : 'text-ink-2'
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

function Indicador({ rotulo, valor, detalhe }: { rotulo: string; valor: string; detalhe?: string }) {
  return (
    <div className="panel p-4">
      <p className="text-[13px] text-ink-2">{rotulo}</p>
      <p className="tabular mt-0.5 text-2xl font-semibold tracking-tight">{valor}</p>
      {detalhe && <p className="tabular text-[13px] text-ink-3">{detalhe}</p>}
    </div>
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

function Proporcao({ total }: { total: Contagem }) {
  const soma = total.furtos + total.roubos
  const furto = total.furtos / soma
  return (
    <div>
      <div className="flex h-5 gap-0.5" role="img" aria-label={`Furtos ${percentual(furto, 1)}, roubos ${percentual(1 - furto, 1)}`}>
        <div className="rounded-l" style={{ width: `${furto * 100}%`, background: SERIES.furtos.cor }} />
        <div className="rounded-r" style={{ width: `${(1 - furto) * 100}%`, background: SERIES.roubos.cor }} />
      </div>
      <dl className="tabular mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-ink-2">Furtos</dt>
          <dd className="text-xl font-semibold">{percentual(furto, 1)}</dd>
        </div>
        <div>
          <dt className="text-ink-2">Roubos</dt>
          <dd className="text-xl font-semibold">{percentual(1 - furto, 1)}</dd>
        </div>
      </dl>
    </div>
  )
}

function agregarLocais(est: Estatisticas, ano: FiltroAno): CategoriaLocal[] {
  const fontes = est.por_tipo_local.filter((a) => ano === 'todos' || a.ano === ano)
  const mapa = new Map<string, CategoriaLocal>()
  for (const f of fontes)
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
    <ul className="space-y-2.5">
      {ordenadas.map((c) => (
        <li key={c.categoria} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 text-sm sm:grid-cols-[13rem_minmax(0,1fr)_4.5rem]">
          <span className="text-ink-2">
            {rotuloCategoria(c.categoria)}
            {(c.tipo === 'outros' || c.tipo === 'ausente') && (
              <span aria-label="com ressalva" title="Ver ressalva abaixo">
                {' '}
                *
              </span>
            )}
          </span>
          <span className="tabular text-right font-medium sm:order-last">{compacto(valor(c))}</span>
          <div className="col-span-2 flex h-2.5 gap-0.5 sm:col-span-1" title={series.map((s) => `${SERIES[s].nome}: ${inteiro(c[s])}`).join(' · ')}>
            {series.map((s) => (
              <div key={s} className="min-w-px rounded-[2px]" style={{ width: `${(c[s] / maximo) * 100}%`, background: SERIES[s].cor }} />
            ))}
          </div>
        </li>
      ))}
    </ul>
  )
}

function Painel({ est }: { est: Estatisticas }) {
  const [ano, setAno] = useState<FiltroAno>('todos')
  const [tipo, setTipo] = useState<FiltroTipo>('ambos')
  const series: Serie[] = tipo === 'ambos' ? ['furtos', 'roubos'] : [tipo]

  const totalPeriodo = useMemo<Contagem>(
    () => (ano === 'todos' ? est.total : est.por_ano.find((a) => a.ano === ano)!),
    [ano, est],
  )
  const soma = totalPeriodo.furtos + totalPeriodo.roubos
  const anuais = est.por_ano.map((a) => ({ rotulo: String(a.ano), furtos: a.furtos, roubos: a.roubos }))
  const mensais = est.por_mes
    .filter((m) => ano === 'todos' || m.ano === ano)
    .map((m) => ({ rotulo: `${MESES_CURTOS[m.mes - 1]}/${String(m.ano).slice(2)}`, furtos: m.furtos, roubos: m.roubos }))
  const locais = useMemo(() => agregarLocais(est, ano), [est, ano])
  const nomePeriodo = ano === 'todos' ? '2023 a 2025' : String(ano)
  const dadosSerie = (d: { rotulo: string; furtos: number; roubos: number }[]) =>
    d.map((x) => ({ rotulo: x.rotulo, ...Object.fromEntries(series.map((s) => [s, x[s]])) }))

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-x-6 gap-y-3">
        <Opcoes legenda="Ano" nome="ano" valor={ano} aoMudar={setAno}
          opcoes={[{ valor: 'todos' as FiltroAno, rotulo: 'Todos' }, ...est.por_ano.map((a) => ({ valor: a.ano as FiltroAno, rotulo: String(a.ano) }))]} />
        <Opcoes legenda="Tipo de ocorrência" nome="tipo" valor={tipo} aoMudar={setTipo}
          opcoes={[{ valor: 'ambos' as FiltroTipo, rotulo: 'Ambos' }, { valor: 'furtos' as FiltroTipo, rotulo: 'Furtos' }, { valor: 'roubos' as FiltroTipo, rotulo: 'Roubos' }]} />
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Indicador rotulo="Boletins elegíveis" valor={inteiro(soma)} detalhe={nomePeriodo} />
        <Indicador rotulo="Furtos" valor={inteiro(totalPeriodo.furtos)} detalhe={percentual(totalPeriodo.furtos / soma, 1)} />
        <Indicador rotulo="Roubos" valor={inteiro(totalPeriodo.roubos)} detalhe={percentual(totalPeriodo.roubos / soma, 1)} />
        <div className="panel col-span-2 p-4 lg:col-span-1">
          <p className="text-[13px] text-ink-2">Período coberto</p>
          <p className="mt-0.5 font-semibold">Janeiro de 2023 a dezembro de 2025</p>
          <a className="text-[13px] text-accent underline" href={est.fonte.url} target="_blank" rel="noreferrer">
            Fonte: SSP-SP
          </a>
        </div>
      </div>

      <Nota>Os gráficos mostram quantidades históricas registradas, por ano do fato. Não são previsões de criminalidade nem indicam risco.</Nota>

      <div className="grid gap-5 lg:grid-cols-3">
        <Cartao className="lg:col-span-2" titulo="Evolução anual" subtitulo="Sempre compara os três anos; não é afetado pelo filtro de ano." series={series}
          tabela={<TabelaContagem primeira="Ano" linhas={anuais} />}>
          <BarrasAnuais dados={dadosSerie(anuais)} series={series} descricao={`Barras por ano: ${anuais.map((a) => `${a.rotulo}, ${inteiro(a.furtos)} furtos e ${inteiro(a.roubos)} roubos`).join('; ')}.`} />
        </Cartao>
        <Cartao titulo="Distribuição das classes" subtitulo={`${nomePeriodo}. Compara sempre furtos e roubos; não é afetada pelo filtro de tipo.`}>
          <Proporcao total={totalPeriodo} />
          <div className="mt-5 border-t border-line pt-3">
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
      </div>

      <Cartao titulo="Evolução mensal" subtitulo={`Registros por mês do fato, ${nomePeriodo}.`} series={series} tabela={<TabelaContagem primeira="Mês" linhas={mensais} />}>
        <LinhasMensais dados={dadosSerie(mensais)} series={series} descricao={`Série mensal de ${nomePeriodo}. Os valores estão disponíveis na tabela abaixo do gráfico.`} />
      </Cartao>

      <Cartao titulo="Distribuição por tipo de local" subtitulo={`${nomePeriodo}. Barras na mesma escala.`} series={series}
        tabela={<TabelaContagem primeira="Tipo de local" linhas={locais.map((c) => ({ ...c, rotulo: rotuloCategoria(c.categoria) }))} />}>
        <BarrasLocal categorias={locais} series={series} />
        <div className="mt-4 space-y-2">
          <Nota titulo="* Ressalva sobre “OUTROS” e “Não informado”">
            Parte desses registros está associada ao preenchimento administrativo da Delegacia Eletrônica. Em 2024, os registros sem local deram lugar a
            “OUTROS”, o que sugere mudança de preenchimento, e não mudança nos lugares dos fatos.
          </Nota>
          <p className="text-[13px] text-ink-3">“Demais categorias” soma os tipos de local com menos de {inteiro(est.limiar_demais_categorias)} boletins nos três anos.</p>
        </div>
      </Cartao>

      <p className="text-[13px] text-ink-3">
        {est.fonte.nome}. {est.fonte.recorte} Fatos de 2025 registrados apenas em 2026 não estão incluídos. Boletins com outras naturezas associadas foram
        excluídos, o que remove proporcionalmente mais roubos.
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
