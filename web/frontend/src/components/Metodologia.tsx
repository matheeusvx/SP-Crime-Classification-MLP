import type { ModeloPublico, Metricas } from '../api/types'
import { inteiro, percentual } from '../format'

const NOMES: Record<string, string> = { mes: 'Mês', dia_semana: 'Dia da semana', tipo_local: 'Tipo de local', bairro: 'Bairro' }

function Etapa({ titulo, valor, detalhe }: { titulo: string; valor: string; detalhe: string }) {
  return (
    <div className="flex-1 rounded-md border border-line bg-paper p-3.5 text-center">
      <p className="text-[13px] text-ink-2">{titulo}</p>
      <p className="tabular text-2xl font-semibold tracking-tight">{valor}</p>
      <p className="text-[13px] text-ink-3">{detalhe}</p>
    </div>
  )
}

function Seta() {
  return (
    <span aria-hidden="true" className="self-center text-lg text-ink-3 max-sm:rotate-90">
      →
    </span>
  )
}

export function DiagramaArquitetura({ modelo }: { modelo: ModeloPublico }) {
  const { entradas, camadas_ocultas } = modelo.arquitetura
  const colunas = modelo.atributos.map((a) => `${NOMES[a]} ${modelo.colunas_por_atributo[a]}`).join(' · ')
  return (
    <figure>
      <div
        className="flex flex-col gap-2 sm:flex-row"
        role="img"
        aria-label={`Arquitetura: ${entradas} entradas, ${camadas_ocultas[0]} neurônios ReLU, 1 saída sigmoid e limiar 0,5`}
      >
        <Etapa titulo="Entradas One-Hot" valor={String(entradas)} detalhe="uma coluna por categoria" />
        <Seta />
        <Etapa titulo="Camada oculta" valor={String(camadas_ocultas[0])} detalhe="neurônios ReLU" />
        <Seta />
        <Etapa titulo="Saída sigmoid" valor="1" detalhe="score de roubo, de 0 a 1" />
        <Seta />
        <Etapa titulo="Limiar" valor="0,5" detalhe="≥ 0,5 ROUBO · < 0,5 FURTO" />
      </div>
      <figcaption className="mt-2 text-[13px] text-ink-3">Colunas por atributo: {colunas}.</figcaption>
    </figure>
  )
}

export function MatrizConfusao({ m }: { m: Metricas }) {
  const celula = (rotulo: string, n: number, totalLinha: number, certo: boolean) => (
    <td className={`p-3 text-center sm:p-4 ${certo ? 'bg-accent-soft' : 'bg-paper'}`}>
      <p className="tabular text-lg font-semibold">{inteiro(n)}</p>
      <p className="tabular text-xs text-ink-2">{percentual(n / totalLinha, 1)} da linha</p>
      <p className="text-xs text-ink-3">{rotulo}</p>
    </td>
  )
  const furtos = m.tn + m.fp
  const roubos = m.fn + m.tp
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[20rem] border-separate border-spacing-1 text-sm">
        <caption className="sr-only">Matriz de confusão do teste final de 2025</caption>
        <thead>
          <tr>
            <td />
            <th scope="col" className="pb-1 font-medium text-ink-2">
              Classificado como FURTO
            </th>
            <th scope="col" className="pb-1 font-medium text-ink-2">
              Classificado como ROUBO
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row" className="pr-2 text-left font-medium text-ink-2">
              Registrado como FURTO
            </th>
            {celula('acertos', m.tn, furtos, true)}
            {celula('falsos positivos', m.fp, furtos, false)}
          </tr>
          <tr>
            <th scope="row" className="pr-2 text-left font-medium text-ink-2">
              Registrado como ROUBO
            </th>
            {celula('falsos negativos', m.fn, roubos, false)}
            {celula('acertos', m.tp, roubos, true)}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
