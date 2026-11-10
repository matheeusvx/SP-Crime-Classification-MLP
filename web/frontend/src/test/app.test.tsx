import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from '../App'
import { rotuloCategoria } from '../format'
import { EXPLICACAO } from '../components/Resultado'
import { opcoes, resposta, simularApi, sucesso } from './fixtures'

const indicador = (rotulo: string) => screen.getByText(rotulo).closest('.panel') as HTMLElement

const abrir = (rota = '/') =>
  render(
    <MemoryRouter initialEntries={[rota]}>
      <App />
    </MemoryRouter>,
  )

async function preencher(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(await screen.findByLabelText('Mês da ocorrência'), 'Maio')
  await user.selectOptions(screen.getByLabelText('Dia da semana'), 'Quarta-feira')
  await user.selectOptions(screen.getByLabelText('Tipo de local'), 'VIA PÚBLICA')
  await user.type(screen.getByRole('combobox', { name: 'Bairro' }), 'bela')
  await user.click(screen.getByRole('option', { name: 'BELA VISTA' }))
}

const corpoEnviado = (falso: ReturnType<typeof simularApi>) => {
  const chamada = falso.mock.calls.find((c) => String(c[0]) === '/api/classify') as unknown as [string, RequestInit]
  return JSON.parse(String(chamada[1].body))
}

describe('navegação', () => {
  it('renderiza as três páginas', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir()
    expect(await screen.findByRole('heading', { level: 1, name: 'Classificador MLP' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Painel histórico' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Painel histórico' })).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Sobre o modelo' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Sobre o modelo' })).toBeInTheDocument()
  })

  it('mostra identificação acadêmica no rodapé', async () => {
    simularApi()
    abrir()
    expect(await screen.findByText(/Não é um sistema oficial da SSP-SP/)).toBeInTheDocument()
  })

  it('trata rota inexistente', async () => {
    simularApi()
    abrir('/nao-existe')
    expect(await screen.findByText('Página não encontrada')).toBeInTheDocument()
  })
})

describe('classificador', () => {
  it('carrega opções reais do contrato nos campos', async () => {
    simularApi()
    abrir()
    expect(await screen.findByRole('option', { name: 'Maio' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Via Pública' })).toHaveValue('VIA PÚBLICA')
  })

  it('mostra estado de carregamento', async () => {
    simularApi({ '/api/options': () => new Promise(() => {}) })
    abrir()
    expect(await screen.findByText('Carregando opções do modelo…')).toBeInTheDocument()
  })

  it('exige todos os campos antes de chamar a API', async () => {
    const falso = simularApi()
    const user = userEvent.setup()
    abrir()
    await user.click(await screen.findByRole('button', { name: 'Classificar ocorrência' }))
    expect(screen.getByText('Selecione o mês.')).toBeInTheDocument()
    expect(falso.mock.calls.some((c) => String(c[0]) === '/api/classify')).toBe(false)
  })

  it('envia valores do contrato e exibe resultado, scores e versão', async () => {
    const falso = simularApi()
    const user = userEvent.setup()
    abrir()
    await preencher(user)
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    expect(await screen.findByText('FURTO')).toBeInTheDocument()
    expect(corpoEnviado(falso)).toEqual({ mes: 5, dia_semana: 2, tipo_local: 'VIA PÚBLICA', bairro: 'BELA VISTA' })
    expect(screen.getByText('Saídas não calibradas do modelo')).toBeInTheDocument()
    expect(screen.getByText('0,750')).toBeInTheDocument()
    expect(screen.getByText('0,250')).toBeInTheDocument()
    expect(screen.getByText(EXPLICACAO)).toBeInTheDocument()
    expect(screen.getByText(/Modelo modelo-de-teste/)).toBeInTheDocument()
  })

  it('não aceita texto livre como bairro', async () => {
    const falso = simularApi()
    const user = userEvent.setup()
    abrir()
    await user.selectOptions(await screen.findByLabelText('Mês da ocorrência'), 'Maio')
    await user.selectOptions(screen.getByLabelText('Dia da semana'), 'Quarta-feira')
    await user.selectOptions(screen.getByLabelText('Tipo de local'), 'VIA PÚBLICA')
    await user.type(screen.getByRole('combobox', { name: 'Bairro' }), 'BAIRRO INVENTADO')
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    expect(screen.getByText(/Selecione um bairro da lista/)).toBeInTheDocument()
    expect(falso.mock.calls.some((c) => String(c[0]) === '/api/classify')).toBe(false)
  })

  it('envia null para ausência explícita', async () => {
    const falso = simularApi()
    const user = userEvent.setup()
    abrir()
    await user.selectOptions(await screen.findByLabelText('Mês da ocorrência'), 'Maio')
    await user.selectOptions(screen.getByLabelText('Dia da semana'), 'Quarta-feira')
    await user.selectOptions(screen.getByLabelText('Tipo de local'), 'Não informado')
    await user.click(screen.getByRole('combobox', { name: 'Bairro' }))
    await user.click(within(screen.getByRole('listbox', { name: 'Bairro' })).getByRole('option', { name: 'Não informado' }))
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    await screen.findByText('FURTO')
    expect(corpoEnviado(falso)).toEqual({ mes: 5, dia_semana: 2, tipo_local: null, bairro: null })
    expect(screen.getByText('Tipo de local com ressalva')).toBeInTheDocument()
  })

  it('preserva grafias distintas na lista de bairros', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir()
    await user.type(await screen.findByRole('combobox', { name: 'Bairro' }), 'tatua')
    expect(screen.getByRole('option', { name: 'TATUAPE' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'TATUAPÉ' })).toBeInTheDocument()
  })

  it('exibe avisos do contrato para bairro raro', async () => {
    simularApi({
      '/api/classify': () =>
        resposta({ ...sucesso, grupos: { bairro: 'raro' }, avisos: [{ campo: 'bairro', codigo: 'bairro_raro', mensagem: 'Representado pelo grupo de raros.' }] }),
    })
    const user = userEvent.setup()
    abrir()
    await preencher(user)
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    expect(await screen.findByText('Bairro com representação limitada')).toBeInTheDocument()
    expect(screen.getByText('Representado pelo grupo de raros.')).toBeInTheDocument()
  })

  it('limpa o resultado quando a entrada muda', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir()
    await preencher(user)
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    await screen.findByText('FURTO')
    await user.selectOptions(screen.getByLabelText('Mês da ocorrência'), 'Janeiro')
    expect(screen.queryByText('FURTO')).not.toBeInTheDocument()
  })

  it('exibe erro de validação do backend', async () => {
    simularApi({
      '/api/classify': () => resposta({ status: 'erro_validacao', erros: [{ campo: 'bairro', codigo: 'categoria_desconhecida', mensagem: 'Categoria não reconhecida.' }], avisos: [], grupos: {} }, 422),
    })
    const user = userEvent.setup()
    abrir()
    await preencher(user)
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    const alerta = await screen.findByRole('alert')
    expect(within(alerta).getByText('Categoria não reconhecida.')).toBeInTheDocument()
    expect(screen.queryByText('Classificação estimada')).not.toBeInTheDocument()
  })

  it('trata falha de rede', async () => {
    simularApi({ '/api/classify': () => Promise.reject(new TypeError('falha')) })
    const user = userEvent.setup()
    abrir()
    await preencher(user)
    await user.click(screen.getByRole('button', { name: 'Classificar ocorrência' }))
    expect(await screen.findByText('Falha de comunicação')).toBeInTheDocument()
  })

  it('trata serviço indisponível sem mostrar resultado', async () => {
    simularApi({ '/api/options': () => resposta({ status: 'servico_indisponivel', mensagem: 'Classificador indisponível.' }, 503) })
    abrir()
    expect(await screen.findByText('Serviço indisponível')).toBeInTheDocument()
    expect(screen.getByText('Classificador indisponível.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Classificar ocorrência' })).not.toBeInTheDocument()
  })

  it('permite tentar novamente após falha', async () => {
    let chamadas = 0
    simularApi({ '/api/options': () => (++chamadas <= 2 ? Promise.reject(new TypeError('x')) : resposta(opcoes)) })
    const user = userEvent.setup()
    abrir()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    await waitFor(async () => {
      if (screen.queryByRole('button', { name: 'Tentar novamente' })) await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
      expect(screen.getByRole('button', { name: 'Classificar ocorrência' })).toBeInTheDocument()
    })
  })

  it('opera o campo de bairro somente pelo teclado', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir()
    const campo = await screen.findByRole('combobox', { name: 'Bairro' })
    campo.focus()
    await user.keyboard('bel')
    await waitFor(() => expect(campo).toHaveAttribute('aria-expanded', 'true'))
    await user.keyboard('{Enter}')
    expect(campo).toHaveValue('BELA VISTA')
    expect(campo).toHaveAttribute('aria-expanded', 'false')
  })

  it('percorre os controles com Tab', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir()
    await screen.findByLabelText('Mês da ocorrência')
    for (let i = 0; i < 12 && document.activeElement !== screen.getByLabelText('Mês da ocorrência'); i++) await user.tab()
    expect(screen.getByLabelText('Mês da ocorrência')).toHaveFocus()
    await user.tab()
    expect(screen.getByLabelText('Dia da semana')).toHaveFocus()
    await user.tab()
    expect(screen.getByLabelText('Tipo de local')).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('combobox', { name: 'Bairro' })).toHaveFocus()
  })
})

describe('painel histórico', () => {
  it('apresenta indicadores e ressalvas', async () => {
    simularApi()
    abrir('/painel')
    expect(await screen.findByText('Boletins elegíveis')).toBeInTheDocument()
    expect(within(indicador('Boletins elegíveis')).getByText('200')).toBeInTheDocument()
    expect(screen.getByText(/associada ao preenchimento administrativo/)).toBeInTheDocument()
    expect(screen.getByText(/não são previsões de criminalidade/i)).toBeInTheDocument()
  })

  it('filtra indicadores por ano', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir('/painel')
    await screen.findByText('Boletins elegíveis')
    await user.click(screen.getByRole('radio', { name: '2024' }))
    expect(within(indicador('Boletins elegíveis')).getByText('100')).toBeInTheDocument()
  })

  it('mantém os indicadores das duas classes ao filtrar tipo', async () => {
    simularApi()
    const user = userEvent.setup()
    abrir('/painel')
    await screen.findByText('Boletins elegíveis')
    await user.click(screen.getByRole('radio', { name: 'Roubos' }))
    expect(within(indicador('Boletins elegíveis')).getByText('200')).toBeInTheDocument()
  })

  it('não oferece informações de bairro', async () => {
    simularApi()
    abrir('/painel')
    await screen.findByText('Boletins elegíveis')
    expect(document.body.textContent).not.toMatch(/bairros mais|ranking|perigos/i)
  })

  it('trata indisponibilidade', async () => {
    simularApi({ '/api/statistics': () => resposta({ status: 'servico_indisponivel', mensagem: 'Sem dados.' }, 503) })
    abrir('/painel')
    expect(await screen.findByText('Sem dados.')).toBeInTheDocument()
  })
})

describe('sobre o modelo', () => {
  it('apresenta arquitetura, comparações e limitações', async () => {
    simularApi()
    abrir('/sobre')
    expect(await screen.findByRole('img', { name: /299 entradas, 64 neurônios ReLU, 1 saída sigmoid/ })).toBeInTheDocument()
    expect(await screen.findByText('Dense64 → Dense32')).toBeInTheDocument()
    expect(screen.getByText(/não demonstrou vantagem consistente/)).toBeInTheDocument()
    expect(screen.getByText('Scores não calibrados')).toBeInTheDocument()
    expect(screen.getByText('Não prevê crimes')).toBeInTheDocument()
    expect(screen.getByText('Validação 2024')).toBeInTheDocument()
    expect(screen.getByText('Teste 2025')).toBeInTheDocument()
    expect(screen.getByText('Matriz de confusão — teste 2025')).toBeInTheDocument()
  })
})

describe('formatação', () => {
  it('apresenta categorias sem alterar OUTROS', () => {
    expect(rotuloCategoria('VIA PÚBLICA')).toBe('Via Pública')
    expect(rotuloCategoria('LAZER E RECREAÇÃO')).toBe('Lazer e Recreação')
    expect(rotuloCategoria('TERMINAL/ESTAÇÃO')).toBe('Terminal/Estação')
    expect(rotuloCategoria('OUTROS')).toBe('OUTROS')
    expect(rotuloCategoria('Não informado')).toBe('Não informado')
  })
})
