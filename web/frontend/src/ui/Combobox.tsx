import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { chaveBusca } from '../format'

/** undefined = nada escolhido; null = "não informado" explícito. */
export type ValorOpcao = string | null | undefined

export interface ItemOpcao {
  valor: string | null
  rotulo: string
  tag?: string
}

const LIMITE_VISIVEL = 60

interface Props {
  rotulo: string
  itens: ItemOpcao[]
  valor: ValorOpcao
  erro?: string
  dica?: string
  aoMudar: (valor: ValorOpcao) => void
}

export function Combobox({ rotulo, itens, valor, erro, dica, aoMudar }: Props) {
  const id = useId()
  const listaId = `${id}-lista`
  const erroId = `${id}-erro`
  const [texto, setTexto] = useState('')
  const [aberto, setAberto] = useState(false)
  const [ativo, setAtivo] = useState(0)
  const listaRef = useRef<HTMLUListElement>(null)

  const comChave = useMemo(() => itens.map((i) => ({ ...i, chave: chaveBusca(i.rotulo) })), [itens])

  // Mantém o texto alinhado a seleções externas (ex.: exemplo ou cenário restaurado).
  useEffect(() => {
    if (valor === undefined) return
    setTexto(itens.find((i) => i.valor === valor)?.rotulo ?? '')
  }, [valor, itens])

  const { visiveis, total } = useMemo(() => {
    const busca = chaveBusca(valor === undefined ? texto : '')
    const achados = busca
      ? [...comChave.filter((i) => i.chave.startsWith(busca)), ...comChave.filter((i) => !i.chave.startsWith(busca) && i.chave.includes(busca))]
      : comChave
    return { visiveis: achados.slice(0, LIMITE_VISIVEL), total: achados.length }
  }, [comChave, texto, valor])

  useEffect(() => {
    if (aberto) listaRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView?.({ block: 'nearest' })
  }, [ativo, aberto])

  function escolher(item: ItemOpcao) {
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
        placeholder={dica ?? 'Digite para buscar'}
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
        className="surgir absolute z-30 mt-1.5 max-h-72 w-full origin-top overflow-auto rounded-xl bg-surface p-1 shadow-xl ring-1 ring-line"
      >
        {visiveis.map((item, i) => (
          <li
            key={item.rotulo}
            id={`${id}-op-${i}`}
            role="option"
            aria-selected={i === ativo}
            onMouseEnter={() => setAtivo(i)}
            onClick={() => escolher(item)}
            className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${i === ativo ? 'bg-accent-soft' : ''}`}
          >
            <span>{item.rotulo}</span>
            {item.tag && <span className="shrink-0 text-xs text-ink-3">{item.tag}</span>}
          </li>
        ))}
        {visiveis.length === 0 && <li className="px-3 py-2 text-sm text-ink-2">Nenhuma opção do vocabulário corresponde à busca.</li>}
        {total > visiveis.length && (
          <li className="px-3 py-2 text-xs text-ink-3">
            Mostrando {visiveis.length} de {total}. Continue digitando para refinar.
          </li>
        )}
      </ul>
    </div>
  )
}
