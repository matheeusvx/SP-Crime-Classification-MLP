import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { OpcaoBairro } from '../api/types'
import { chaveBusca } from '../format'

/** undefined = nada escolhido; null = "não informado" explícito. */
export type ValorBairro = string | null | undefined

const LIMITE_VISIVEL = 60
const NAO_INFORMADO = 'Não informado'

interface Item {
  valor: string | null
  rotulo: string
  raro: boolean
  chave: string
}

interface Props {
  rotulo: string
  opcoes: OpcaoBairro[]
  valor: ValorBairro
  erro?: string
  aoMudar: (valor: ValorBairro) => void
}

export function BairroCombobox({ rotulo, opcoes, valor, erro, aoMudar }: Props) {
  const id = useId()
  const listaId = `${id}-lista`
  const erroId = `${id}-erro`
  const [texto, setTexto] = useState('')
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(0)
  const listaRef = useRef<HTMLUListElement>(null)

  const itens = useMemo<Item[]>(() => {
    const ordenados = [...opcoes].sort((a, b) => a.valor.localeCompare(b.valor, 'pt-BR'))
    return [
      { valor: null, rotulo: NAO_INFORMADO, raro: false, chave: chaveBusca(NAO_INFORMADO) },
      ...ordenados.map((o) => ({ valor: o.valor, rotulo: o.valor, raro: o.grupo === 'raro', chave: chaveBusca(o.valor) })),
    ]
  }, [opcoes])

  // Mantém o texto alinhado a seleções externas (ex.: exemplo hipotético, limpar).
  useEffect(() => {
    if (valor === undefined) return
    setTexto(valor === null ? NAO_INFORMADO : valor)
  }, [valor])

  const { visiveis, total } = useMemo(() => {
    const busca = chaveBusca(valor === undefined ? texto : '')
    const achados = busca
      ? [...itens.filter((i) => i.chave.startsWith(busca)), ...itens.filter((i) => !i.chave.startsWith(busca) && i.chave.includes(busca))]
      : itens
    return { visiveis: achados.slice(0, LIMITE_VISIVEL), total: achados.length }
  }, [itens, texto, valor])

  useEffect(() => {
    if (aberto) listaRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView?.({ block: 'nearest' })
  }, [ativo, aberto])

  function escolher(item: Item) {
    aoMudar(item.valor)
    setTexto(item.rotulo)
    setAberto(false)
  }

  function aoTeclar(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!aberto) setAberto(true)
      else setAtivo((n) => Math.min(n + 1, visiveis.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setAtivo((n) => Math.max(n - 1, 0))
    } else if (e.key === 'Enter' && aberto) {
      e.preventDefault()
      if (visiveis[ativo]) escolher(visiveis[ativo])
    } else if (e.key === 'Escape' && aberto) {
      e.preventDefault()
      setAberto(false)
    }
  }

  return (
    <div className="relative">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {rotulo}
      </label>
      <input
        id={id}
        className="field-control"
        role="combobox"
        aria-expanded={aberto}
        aria-controls={listaId}
        aria-autocomplete="list"
        aria-activedescendant={aberto && visiveis[ativo] ? `${id}-op-${ativo}` : undefined}
        aria-invalid={Boolean(erro)}
        aria-describedby={erro ? erroId : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder="Digite para buscar"
        value={texto}
        onFocus={() => setAberto(true)}
        onClick={() => setAberto(true)}
        onBlur={() => setAberto(false)}
        onKeyDown={aoTeclar}
        onChange={(e) => {
          setTexto(e.target.value)
          setAtivo(0)
          setAberto(true)
          aoMudar(undefined) // Texto digitado nunca é enviado: exige escolha na lista.
        }}
      />
      {erro && (
        <p id={erroId} className="mt-1 text-[13px] text-danger">
          {erro}
        </p>
      )}
      <ul
        id={listaId}
        ref={listaRef}
        role="listbox"
        aria-label={rotulo}
        hidden={!aberto}
        onMouseDown={(e) => e.preventDefault()}
        className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-md border border-line-strong bg-surface py-1 shadow-md"
      >
        {visiveis.map((item, i) => (
          <li
            key={item.rotulo}
            id={`${id}-op-${i}`}
            role="option"
            aria-selected={i === ativo}
            onMouseEnter={() => setAtivo(i)}
            onClick={() => escolher(item)}
            className={`flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm ${i === ativo ? 'bg-accent-soft' : ''}`}
          >
            <span>{item.rotulo}</span>
            {item.raro && <span className="shrink-0 text-xs text-ink-3">grupo raro</span>}
          </li>
        ))}
        {visiveis.length === 0 && <li className="px-3 py-2 text-sm text-ink-2">Nenhum bairro do vocabulário corresponde à busca.</li>}
        {total > visiveis.length && (
          <li className="px-3 py-2 text-xs text-ink-3">
            Mostrando {visiveis.length} de {total}. Continue digitando para refinar.
          </li>
        )}
      </ul>
    </div>
  )
}
