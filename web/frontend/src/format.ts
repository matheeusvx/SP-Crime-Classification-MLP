const inteiroBR = new Intl.NumberFormat('pt-BR')
const compactoBR = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

export const inteiro = (n: number) => inteiroBR.format(n)
export const compacto = (n: number) => compactoBR.format(n)
export const percentual = (fracao: number, casas = 2) =>
  `${new Intl.NumberFormat('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(fracao * 100)}%`
export const decimal = (n: number, casas = 3) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(n)

const MINUSCULAS = new Set(['e', 'de', 'do', 'da', 'das', 'dos'])

/**
 * Somente apresentação de tipo de local: o valor enviado à API não é alterado.
 * Bairros seguem como no vocabulário, pois a grafia distingue categorias.
 */
export function rotuloCategoria(valor: string): string {
  if (valor === 'OUTROS') return valor
  if (valor !== valor.toUpperCase()) return valor
  return valor
    .toLocaleLowerCase('pt-BR')
    .split(' ')
    .map((palavra, i) =>
      i > 0 && MINUSCULAS.has(palavra)
        ? palavra
        : palavra.replace(/(^|\/)(\p{L})/gu, (_, sep: string, letra: string) => sep + letra.toLocaleUpperCase('pt-BR')),
    )
    .join(' ')
}

export const MESES_CURTOS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

/** Busca na lista de opções, tolerante a acentos. Nunca altera o valor selecionado. */
export function chaveBusca(texto: string): string {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLocaleUpperCase('pt-BR').trim()
}
