import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'

export type Recurso<T> =
  | { estado: 'carregando' }
  | { estado: 'ok'; dados: T }
  | { estado: 'erro'; erro: ApiError }

export function useResource<T>(buscar: (signal: AbortSignal) => Promise<T>) {
  const [recurso, setRecurso] = useState<Recurso<T>>({ estado: 'carregando' })
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    setRecurso({ estado: 'carregando' })
    buscar(controle.signal).then(
      (dados) => setRecurso({ estado: 'ok', dados }),
      (erro: unknown) => {
        if (controle.signal.aborted) return
        setRecurso({
          estado: 'erro',
          erro: erro instanceof ApiError ? erro : new ApiError('servidor', 'Ocorreu um erro inesperado.'),
        })
      },
    )
    return () => controle.abort()
  }, [buscar, tentativa])

  const recarregar = useCallback(() => setTentativa((n) => n + 1), [])
  return { recurso, recarregar }
}
