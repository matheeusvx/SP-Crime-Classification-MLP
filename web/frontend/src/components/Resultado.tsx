import type { ClassificacaoOk, EntradaClassificacao } from '../api/types'
import { decimal } from '../format'
import { Nota } from './Status'

export const EXPLICACAO =
  'Esta classificação identifica qual categoria é mais compatível com as características informadas. Não representa uma previsão de que um crime acontecerá.'

function BarraScore({ rotulo, valor, cor }: { rotulo: string; valor: number; cor: string }) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-ink-2">{rotulo}</span>
        <span className="tabular font-semibold">{decimal(valor)}</span>
      </div>
      <div className="relative mt-1 h-2 rounded-full bg-paper" aria-hidden="true">
        <div className="h-2 rounded-full" style={{ width: `${valor * 100}%`, background: cor }} />
        <div className="absolute -top-0.5 left-1/2 h-3 w-px bg-ink-3" />
      </div>
    </div>
  )
}

export function Resultado({ resultado, entrada }: { resultado: ClassificacaoOk; entrada: EntradaClassificacao }) {
  const roubo = resultado.classe_estimada === 'ROUBO'
  const localAdministrativo = entrada.tipo_local === 'OUTROS' || entrada.tipo_local === null
  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm text-ink-2">Classificação estimada</p>
        <p className="mt-0.5 flex items-center gap-2.5 text-3xl font-semibold tracking-tight">
          <span aria-hidden="true" className="inline-block size-3 rounded-sm" style={{ background: roubo ? 'var(--color-roubo)' : 'var(--color-furto)' }} />
          {resultado.classe_estimada}
        </p>
      </div>

      <p className="text-sm text-ink-2">{EXPLICACAO}</p>

      <section aria-label="Scores do modelo" className="space-y-3 border-t border-line pt-4">
        <h3 className="text-sm font-semibold">Saídas não calibradas do modelo</h3>
        <BarraScore rotulo="Score estimado para furto" valor={resultado.scores_sigmoid.furto} cor="var(--color-furto)" />
        <BarraScore rotulo="Score estimado para roubo" valor={resultado.scores_sigmoid.roubo} cor="var(--color-roubo)" />
        <p className="text-[13px] text-ink-3">
          A marca central indica o limiar de decisão (0,500). {resultado.interpretacao_scores}
        </p>
      </section>

      {(resultado.avisos.length > 0 || localAdministrativo) && (
        <section aria-label="Avisos" className="space-y-2">
          {resultado.avisos.map((a) => (
            <Nota key={`${a.campo}-${a.codigo}`} titulo={a.codigo === 'bairro_raro' ? 'Bairro com representação limitada' : 'Campo não informado'}>
              {a.mensagem}
            </Nota>
          ))}
          {localAdministrativo && (
            <Nota titulo="Tipo de local com ressalva">
              Parte dos registros sem local ou em “OUTROS” está associada ao preenchimento administrativo da Delegacia Eletrônica. Esse sinal pode
              refletir o canal de registro, e não o lugar do fato.
            </Nota>
          )}
        </section>
      )}

      <p className="break-words border-t border-line pt-3 text-xs text-ink-3">
        Modelo {resultado.versao_modelo} · Contrato {resultado.versao_contrato}
      </p>
    </div>
  )
}
