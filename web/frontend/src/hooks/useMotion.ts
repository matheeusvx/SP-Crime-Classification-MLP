import { useEffect, useRef, useState } from 'react'

/** Sem suporte a matchMedia (ex.: testes), considera movimento reduzido. */
export function movimentoReduzido(): boolean {
  return typeof window.matchMedia !== 'function' || window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Interpola até `alvo`; o valor final é sempre exato. */
export function useContagem(alvo: number, duracao = 800): number {
  const [valor, setValor] = useState(() => (movimentoReduzido() ? alvo : 0))
  const atual = useRef(valor)

  useEffect(() => {
    if (movimentoReduzido()) {
      atual.current = alvo
      setValor(alvo)
      return
    }
    const inicio = atual.current
    const t0 = performance.now()
    let quadro = 0
    const passo = (t: number) => {
      const p = Math.min((t - t0) / duracao, 1)
      const proximo = p === 1 ? alvo : inicio + (alvo - inicio) * (1 - (1 - p) ** 3)
      atual.current = proximo
      setValor(proximo)
      if (p < 1) quadro = requestAnimationFrame(passo)
    }
    quadro = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(quadro)
  }, [alvo, duracao])

  return valor
}

/** Devolve `alvo` no quadro seguinte à montagem, para acionar transições CSS. */
export function useAposMontar<T>(inicial: T, alvo: T): T {
  const [valor, setValor] = useState<T>(() => (movimentoReduzido() ? alvo : inicial))
  useEffect(() => {
    if (movimentoReduzido()) return setValor(alvo)
    const q = requestAnimationFrame(() => setValor(alvo))
    return () => cancelAnimationFrame(q)
  }, [alvo])
  return valor
}
