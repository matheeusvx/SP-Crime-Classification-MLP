import type { ClassificacaoOk, EntradaClassificacao } from '../api/types'
import { decimal } from '../format'
import { Medidor, Versus } from '../viz/basicos'
import { Nota, atraso } from '../ui/base'

export const EXPLICACAO =
  'Esta classificação identifica qual categoria é mais compatível com as características informadas. Não representa uma previsão de que um crime acontecerá.'

const COR = { FURTO: 'var(--color-furto)', ROUBO: 'var(--color-roubo)' }

export function MedidorVazio({ carregando }: { carregando?: boolean }) {
  return (
    <div className={carregando ? 'opacity-60' : ''}>
      <Medidor segmentos={[]} marca="0,5" descricao="Medidor aguardando classificação">
        <p className="text-2xl font-bold tracking-tight text-ink-3">{carregando ? '…' : '—'}</p>
      </Medidor>
    </div>
  )
}

export function Resultado({ resultado, entrada }: { resultado: ClassificacaoOk; entrada: EntradaClassificacao }) {
  const { furto, roubo } = resultado.scores_sigmoid
  const localAdministrativo = entrada.tipo_local === 'OUTROS' || entrada.tipo_local === null
  return (
    <div className="space-y-4">
      <div className="surgir">
        <p className="text-center text-sm text-ink-3">Classificação estimada</p>
        <Medidor
          segmentos={[
            { nome: 'furto', valor: furto, cor: COR.FURTO },
            { nome: 'roubo', valor: roubo, cor: COR.ROUBO },
          ]}
          marca="0,5"
          descricao={`Score de furto ${decimal(furto)}, score de roubo ${decimal(roubo)}; marca central no limiar 0,5`}
        >
          <p className="text-[32px] font-bold leading-none tracking-tight">{resultado.classe_estimada}</p>
        </Medidor>
      </div>

      <p className="subir text-center text-sm text-ink-2" style={atraso(120)}>
        {EXPLICACAO}
      </p>

      <section aria-label="Scores do modelo" className="subir rounded-xl bg-soft p-4" style={atraso(200)}>
        <h3 className="mb-3 text-[13px] font-semibold">Saídas não calibradas do modelo</h3>
        <Versus
          esquerda={{ nome: 'Score estimado para furto', valor: decimal(furto), fracao: furto, cor: COR.FURTO }}
          direita={{ nome: 'Score estimado para roubo', valor: decimal(roubo), fracao: roubo, cor: COR.ROUBO }}
        />
        <p className="mt-3 text-xs text-ink-3">
          A marca no topo do medidor indica o limiar de decisão (0,500). {resultado.interpretacao_scores}
        </p>
      </section>

      {(resultado.avisos.length > 0 || localAdministrativo) && (
        <section aria-label="Avisos" className="subir space-y-2" style={atraso(280)}>
          {resultado.avisos.map((a) => (
            <Nota key={`${a.campo}-${a.codigo}`} titulo={a.codigo === 'bairro_raro' ? 'Bairro com representação limitada' : 'Campo não informado'}>
              {a.mensagem}
            </Nota>
          ))}
          {localAdministrativo && (
            <Nota titulo="Tipo de local com ressalva">
              Parte dos registros sem local ou em “OUTROS” está associada ao preenchimento administrativo da Delegacia Eletrônica. Esse sinal pode refletir o canal de registro, e não o lugar do fato.
            </Nota>
          )}
        </section>
      )}

      <p className="break-words text-center text-xs text-ink-3">
        Modelo {resultado.versao_modelo} · Contrato {resultado.versao_contrato}
      </p>
    </div>
  )
}
