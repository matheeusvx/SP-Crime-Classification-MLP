import { useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { ApiError, classificar, obterOpcoes } from '../api/client'
import type { ClassificacaoOk, EntradaClassificacao, Opcoes } from '../api/types'
import { BairroCombobox } from '../components/BairroCombobox'
import type { ValorBairro } from '../components/BairroCombobox'
import { Resultado } from '../components/Resultado'
import { Cabecalho, Carregando, MensagemErro, Nota } from '../components/Status'
import { rotuloCategoria } from '../format'
import { useResource } from '../hooks/useResource'

const NAO_INFORMADO = 'nao-informado'

interface Formulario {
  mes: string
  dia: string
  local: string
  bairro: ValorBairro
}

type Saida =
  | { estado: 'vazio' }
  | { estado: 'enviando' }
  | { estado: 'ok'; resultado: ClassificacaoOk; entrada: EntradaClassificacao }
  | { estado: 'erro'; erro: ApiError }

const VAZIO: Formulario = { mes: '', dia: '', local: '', bairro: undefined }

function Selecao(props: { rotulo: string; valor: string; erro?: string; aoMudar: (v: string) => void; children: ReactNode }) {
  const id = `campo-${props.rotulo.toLowerCase().replace(/\W+/g, '-')}`
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {props.rotulo}
      </label>
      <select
        id={id}
        className="field-control"
        value={props.valor}
        aria-invalid={Boolean(props.erro)}
        aria-describedby={props.erro ? `${id}-erro` : undefined}
        onChange={(e) => props.aoMudar(e.target.value)}
      >
        {props.children}
      </select>
      {props.erro && (
        <p id={`${id}-erro`} className="mt-1 text-[13px] text-danger">
          {props.erro}
        </p>
      )}
    </div>
  )
}

function Formulario({ opcoes }: { opcoes: Opcoes }) {
  const [form, setForm] = useState<Formulario>(VAZIO)
  const [faltantes, setFaltantes] = useState<Partial<Record<keyof Formulario, string>>>({})
  const [saida, setSaida] = useState<Saida>({ estado: 'vazio' })
  const exemplo = opcoes.tipos_local.includes('VIA PÚBLICA') && opcoes.bairros.some((b) => b.valor === 'BELA VISTA')

  function alterar(parcial: Partial<Formulario>) {
    setForm((f) => ({ ...f, ...parcial }))
    setFaltantes({})
    setSaida({ estado: 'vazio' }) // Um resultado nunca fica ao lado de dados diferentes.
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    const pendentes: typeof faltantes = {}
    if (!form.mes) pendentes.mes = 'Selecione o mês.'
    if (!form.dia) pendentes.dia = 'Selecione o dia da semana.'
    if (!form.local) pendentes.local = 'Selecione o tipo de local.'
    if (form.bairro === undefined) pendentes.bairro = 'Selecione um bairro da lista ou “Não informado”.'
    setFaltantes(pendentes)
    if (Object.keys(pendentes).length > 0) return

    const entrada: EntradaClassificacao = {
      mes: Number(form.mes),
      dia_semana: Number(form.dia),
      tipo_local: form.local === NAO_INFORMADO ? null : form.local,
      bairro: form.bairro ?? null,
    }
    setSaida({ estado: 'enviando' })
    try {
      setSaida({ estado: 'ok', resultado: await classificar(entrada), entrada })
    } catch (erro) {
      setSaida({ estado: 'erro', erro: erro instanceof ApiError ? erro : new ApiError('servidor', 'Ocorreu um erro inesperado.') })
    }
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
      <form onSubmit={enviar} noValidate className="panel space-y-4 p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Selecao rotulo="Mês da ocorrência" valor={form.mes} erro={faltantes.mes} aoMudar={(mes) => alterar({ mes })}>
            <option value="">Selecione</option>
            {opcoes.meses.map((m) => (
              <option key={m.valor} value={m.valor}>
                {m.rotulo}
              </option>
            ))}
          </Selecao>
          <Selecao rotulo="Dia da semana" valor={form.dia} erro={faltantes.dia} aoMudar={(dia) => alterar({ dia })}>
            <option value="">Selecione</option>
            {opcoes.dias_semana.map((d) => (
              <option key={d.valor} value={d.valor}>
                {d.rotulo}
              </option>
            ))}
          </Selecao>
        </div>
        <Selecao rotulo="Tipo de local" valor={form.local} erro={faltantes.local} aoMudar={(local) => alterar({ local })}>
          <option value="">Selecione</option>
          {opcoes.tipos_local.map((t) => (
            <option key={t} value={t}>
              {rotuloCategoria(t)}
            </option>
          ))}
          <option value={NAO_INFORMADO}>Não informado</option>
        </Selecao>
        <BairroCombobox rotulo="Bairro" opcoes={opcoes.bairros} valor={form.bairro} erro={faltantes.bairro} aoMudar={(bairro) => alterar({ bairro })} />
        <p className="text-[13px] text-ink-3">
          A lista reúne as grafias observadas no treinamento de 2023 e não é um cadastro oficial. Grafias diferentes de um mesmo bairro podem ser
          categorias distintas para o modelo.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <button type="submit" className="btn btn-primary" disabled={saida.estado === 'enviando'}>
            {saida.estado === 'enviando' ? 'Classificando…' : 'Classificar ocorrência'}
          </button>
          {exemplo && (
            <button type="button" className="btn btn-quiet" onClick={() => alterar({ mes: '5', dia: '2', local: 'VIA PÚBLICA', bairro: 'BELA VISTA' })}>
              Preencher exemplo hipotético
            </button>
          )}
        </div>
      </form>

      <section aria-labelledby="titulo-resultado" className="panel p-5 sm:p-6">
        <h2 id="titulo-resultado" className="sr-only">
          Resultado
        </h2>
        <div aria-live="polite">
          {saida.estado === 'vazio' && (
            <p className="py-8 text-center text-sm text-ink-2">O resultado aparecerá aqui depois que você preencher os campos e solicitar a classificação.</p>
          )}
          {saida.estado === 'enviando' && <Carregando texto="Consultando o modelo…" />}
          {saida.estado === 'erro' && <MensagemErro erro={saida.erro} />}
          {saida.estado === 'ok' && <Resultado resultado={saida.resultado} entrada={saida.entrada} />}
        </div>
      </section>
    </div>
  )
}

export default function ClassificadorPage() {
  const { recurso, recarregar } = useResource(obterOpcoes)
  return (
    <>
      <Cabecalho titulo="Classificador MLP">
        Informe as características de uma ocorrência já registrada ou hipotética de celular subtraído na capital paulista. A rede indica se elas são
        mais compatíveis com o padrão de furto ou de roubo.
      </Cabecalho>
      {recurso.estado === 'carregando' && <Carregando texto="Carregando opções do modelo…" />}
      {recurso.estado === 'erro' && <MensagemErro erro={recurso.erro} aoTentar={recarregar} />}
      {recurso.estado === 'ok' && <Formulario opcoes={recurso.dados} />}
      <div className="mt-6 max-w-3xl">
        <Nota>
          O modelo não prevê crimes futuros, não determina a natureza jurídica de um fato e não mede a segurança de bairros. Em 2025, acertou 68,82% dos
          boletins de teste.
        </Nota>
      </div>
    </>
  )
}
