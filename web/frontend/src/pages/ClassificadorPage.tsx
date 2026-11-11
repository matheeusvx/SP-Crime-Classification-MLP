import { useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, classificar, obterEstatisticas, obterMetodologia, obterOpcoes } from '../api/client'
import type { ClassificacaoOk, EntradaClassificacao, Estatisticas, Metodologia, Opcoes } from '../api/types'
import { Cenarios, ContextoHistorico, DesempenhoGrupo } from '../components/Contexto'
import type { Cenario } from '../components/Contexto'
import { MedidorVazio, Resultado } from '../components/Resultado'
import { percentual, rotuloCategoria } from '../format'
import { useResource } from '../hooks/useResource'
import { Cabecalho, Carregando, MensagemErro, Revelar } from '../ui/base'
import { Combobox } from '../ui/Combobox'
import type { ItemOpcao, ValorOpcao } from '../ui/Combobox'

interface Formulario {
  mes?: number
  dia?: number
  local: ValorOpcao
  bairro: ValorOpcao
}

type Saida =
  | { estado: 'vazio' }
  | { estado: 'enviando' }
  | { estado: 'ok'; resultado: ClassificacaoOk; entrada: EntradaClassificacao }
  | { estado: 'erro'; erro: ApiError }

const VAZIO: Formulario = { local: undefined, bairro: undefined }
const NAO_INFORMADO: ItemOpcao = { valor: null, rotulo: 'Não informado' }
const MAX_CENARIOS = 8

function Chips(props: { legenda: string; nome: string; colunas: string; opcoes: { valor: number; rotulo: string }[]; valor?: number; erro?: string; aoMudar: (v: number) => void }) {
  return (
    <fieldset aria-describedby={props.erro ? `${props.nome}-erro` : undefined}>
      <legend className="mb-1.5 text-sm font-medium">{props.legenda}</legend>
      <div className={`grid gap-1.5 ${props.colunas}`}>
        {props.opcoes.map((o) => (
          <label key={o.valor} className="chip">
            <input type="radio" className="sr-only" name={props.nome} aria-label={o.rotulo} checked={props.valor === o.valor} onChange={() => props.aoMudar(o.valor)} />
            <span aria-hidden="true">{o.rotulo.slice(0, 3)}</span>
          </label>
        ))}
      </div>
      {props.erro && (
        <p id={`${props.nome}-erro`} className="mt-1 text-[13px] text-danger">
          {props.erro}
        </p>
      )}
    </fieldset>
  )
}

function Classificador({ opcoes, est, met }: { opcoes: Opcoes; est?: Estatisticas; met?: Metodologia }) {
  const [form, setForm] = useState<Formulario>(VAZIO)
  const [faltantes, setFaltantes] = useState<Partial<Record<keyof Formulario, string>>>({})
  const [saida, setSaida] = useState<Saida>({ estado: 'vazio' })
  const [cenarios, setCenarios] = useState<Cenario[]>([])
  const [ativo, setAtivo] = useState<number>()
  const proximoId = useRef(1)

  const locais = useMemo<ItemOpcao[]>(() => [...opcoes.tipos_local.map((t) => ({ valor: t, rotulo: rotuloCategoria(t) })).sort((a, b) => a.rotulo.localeCompare(b.rotulo, 'pt-BR')), NAO_INFORMADO], [opcoes])
  const bairros = useMemo<ItemOpcao[]>(
    () => [NAO_INFORMADO, ...[...opcoes.bairros].sort((a, b) => a.valor.localeCompare(b.valor, 'pt-BR')).map((b) => ({ valor: b.valor, rotulo: b.valor, tag: b.grupo === 'raro' ? 'grupo raro' : undefined }))],
    [opcoes],
  )
  const exemplo = opcoes.tipos_local.includes('VIA PÚBLICA') && opcoes.bairros.some((b) => b.valor === 'BELA VISTA')

  function alterar(parcial: Partial<Formulario>) {
    setForm((f) => ({ ...f, ...parcial }))
    setFaltantes({})
    setAtivo(undefined)
    setSaida({ estado: 'vazio' }) // Um resultado nunca fica ao lado de dados diferentes.
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const pendentes: typeof faltantes = {}
    if (form.mes === undefined) pendentes.mes = 'Selecione o mês.'
    if (form.dia === undefined) pendentes.dia = 'Selecione o dia da semana.'
    if (form.local === undefined) pendentes.local = 'Selecione um tipo de local da lista ou “Não informado”.'
    if (form.bairro === undefined) pendentes.bairro = 'Selecione um bairro da lista ou “Não informado”.'
    setFaltantes(pendentes)
    if (Object.keys(pendentes).length > 0) return

    const entrada: EntradaClassificacao = { mes: form.mes!, dia_semana: form.dia!, tipo_local: form.local ?? null, bairro: form.bairro ?? null }
    setSaida({ estado: 'enviando' })
    try {
      const resultado = await classificar(entrada)
      setSaida({ estado: 'ok', resultado, entrada })
      const id = proximoId.current++
      setCenarios((lista) => [...lista.filter((c) => JSON.stringify(c.entrada) !== JSON.stringify(entrada)), { id, entrada, resultado }].slice(-MAX_CENARIOS))
      setAtivo(id)
    } catch (erro) {
      setSaida({ estado: 'erro', erro: erro instanceof ApiError ? erro : new ApiError('servidor', 'Ocorreu um erro inesperado.') })
    }
  }

  function restaurar(id: number) {
    const c = cenarios.find((x) => x.id === id)
    if (!c) return
    setForm({ mes: c.entrada.mes, dia: c.entrada.dia_semana, local: c.entrada.tipo_local, bairro: c.entrada.bairro })
    setFaltantes({})
    setSaida({ estado: 'ok', resultado: c.resultado, entrada: c.entrada })
    setAtivo(id)
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]">
        <form onSubmit={enviar} noValidate className="card space-y-5 p-5 sm:p-6">
          <Chips legenda="Mês da ocorrência" nome="mes" colunas="grid-cols-6" opcoes={opcoes.meses} valor={form.mes} erro={faltantes.mes} aoMudar={(mes) => alterar({ mes })} />
          <Chips legenda="Dia da semana" nome="dia" colunas="grid-cols-7" opcoes={opcoes.dias_semana} valor={form.dia} erro={faltantes.dia} aoMudar={(dia) => alterar({ dia })} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Combobox rotulo="Tipo de local" itens={locais} valor={form.local} erro={faltantes.local} aoMudar={(local) => alterar({ local })} />
            <Combobox rotulo="Bairro" itens={bairros} valor={form.bairro} erro={faltantes.bairro} aoMudar={(bairro) => alterar({ bairro })} />
          </div>
          <p className="text-[13px] text-ink-3">
            A lista reúne as grafias observadas no treinamento de 2023 e não é um cadastro oficial. Grafias diferentes de um mesmo bairro podem ser categorias distintas para o modelo.
          </p>
          <div className="flex flex-wrap gap-2">
            <button type="submit" className="btn btn-primary" disabled={saida.estado === 'enviando'}>
              {saida.estado === 'enviando' ? 'Classificando…' : 'Classificar ocorrência'}
            </button>
            {exemplo && (
              <button type="button" className="btn btn-quiet" onClick={() => alterar({ mes: 5, dia: 2, local: 'VIA PÚBLICA', bairro: 'BELA VISTA' })}>
                Preencher exemplo hipotético
              </button>
            )}
          </div>
        </form>

        <section aria-labelledby="titulo-resultado" className="card p-5 sm:p-6">
          <h2 id="titulo-resultado" className="sr-only">
            Resultado
          </h2>
          <div aria-live="polite">
            {saida.estado === 'vazio' && (
              <div className="py-4 text-center">
                <MedidorVazio />
                <p className="mx-auto mt-4 max-w-xs text-sm text-ink-3">O resultado aparecerá aqui depois que você preencher os campos e solicitar a classificação.</p>
              </div>
            )}
            {saida.estado === 'enviando' && (
              <div role="status" className="py-4 text-center">
                <MedidorVazio carregando />
                <p className="mt-4 text-sm text-ink-3">Consultando o modelo…</p>
              </div>
            )}
            {saida.estado === 'erro' && <MensagemErro erro={saida.erro} />}
            {saida.estado === 'ok' && <Resultado key={JSON.stringify(saida.entrada)} resultado={saida.resultado} entrada={saida.entrada} />}
          </div>
        </section>
      </div>

      {cenarios.length > 0 && (
        <div className={saida.estado === 'ok' && met ? 'grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]' : ''}>
          <div className="subir">
            <Cenarios
              cenarios={cenarios}
              ativo={ativo}
              opcoes={opcoes}
              aoEscolher={restaurar}
              aoLimpar={() => {
                setCenarios([])
                setAtivo(undefined)
              }}
            />
          </div>
          {saida.estado === 'ok' && met && (
            <div className="subir">
              <DesempenhoGrupo met={met} resultado={saida.resultado} entrada={saida.entrada} />
            </div>
          )}
        </div>
      )}

      {est && (
        <Revelar>
          <h2 className="mb-0.5 mt-3 text-lg font-semibold tracking-tight">Contexto histórico da seleção</h2>
          <p className="mb-3 text-[13px] text-ink-3">Contagens registradas na base, de 2023 a 2025. Descrevem os dados e não explicam a classificação acima.</p>
          <ContextoHistorico est={est} mes={form.mes} dia={form.dia} local={form.local} />
        </Revelar>
      )}
    </div>
  )
}

export default function ClassificadorPage() {
  const { recurso, recarregar } = useResource(obterOpcoes)
  const estatisticas = useResource(obterEstatisticas)
  const metodologia = useResource(obterMetodologia)
  const met = metodologia.recurso.estado === 'ok' ? metodologia.recurso.dados : undefined
  return (
    <>
      <Cabecalho
        titulo="Classificador MLP"
        lateral={
          met && (
            <dl className="subir flex gap-5 rounded-xl bg-surface px-4 py-2.5 shadow-sm">
              <div>
                <dt className="text-xs text-ink-3">Accuracy em 2025</dt>
                <dd className="tabular text-[15px] font-bold">{percentual(met.desempenho.teste_2025.accuracy)}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-3">Macro F1</dt>
                <dd className="tabular text-[15px] font-bold">{percentual(met.desempenho.teste_2025.macro_f1)}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-3">Calibração</dt>
                <dd className="text-[15px] font-bold">Não calibrado</dd>
              </div>
            </dl>
          )
        }
      >
        Informe as características de uma ocorrência já registrada ou hipotética de celular subtraído na capital paulista. A rede indica se elas são mais compatíveis com o padrão de furto ou de roubo.
      </Cabecalho>
      {recurso.estado === 'carregando' && <Carregando texto="Carregando opções do modelo…" />}
      {recurso.estado === 'erro' && <MensagemErro erro={recurso.erro} aoTentar={recarregar} />}
      {recurso.estado === 'ok' && <Classificador opcoes={recurso.dados} est={estatisticas.recurso.estado === 'ok' ? estatisticas.recurso.dados : undefined} met={met} />}
    </>
  )
}
