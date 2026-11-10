/** Integração real: navegador → build → FastAPI → SafeClassifier → Dense64 congelada. */
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

const raiz = resolve(import.meta.dirname, '../../..')
const python = [resolve(raiz, '.venv/Scripts/python.exe'), resolve(raiz, '.venv/bin/python')].find(existsSync)!
const capturas = resolve(raiz, 'reports/etapa6/capturas')
mkdirSync(capturas, { recursive: true })

// Exemplos hipotéticos com categorias do vocabulário; nenhum vem de boletins.
const CASOS = [
  { entrada: { mes: 5, dia_semana: 2, tipo_local: 'VIA PÚBLICA', bairro: 'BELA VISTA' }, mes: 'Maio', dia: 'Quarta-feira', local: 'Via Pública' },
  { entrada: { mes: 12, dia_semana: 6, tipo_local: 'TERMINAL/ESTAÇÃO', bairro: 'SANTANA' }, mes: 'Dezembro', dia: 'Domingo', local: 'Terminal/Estação' },
  { entrada: { mes: 1, dia_semana: 0, tipo_local: 'VIA PÚBLICA', bairro: 'CAPAO REDONDO' }, mes: 'Janeiro', dia: 'Segunda-feira', local: 'Via Pública' },
]
const TEXTO_OBRIGATORIO = 'Esta classificação identifica qual categoria é mais compatível com as características informadas. Não representa uma previsão de que um crime acontecerá.'

interface Referencia {
  classe_estimada: string
  scores_sigmoid: { furto: number; roubo: number }
  versao_modelo: string
}
let referencias: Referencia[]

test.beforeAll(() => {
  const saida = execFileSync(python, [resolve(import.meta.dirname, 'referencia.py')], {
    input: JSON.stringify(CASOS.map((c) => c.entrada)),
    encoding: 'utf-8',
    stdio: ['pipe', 'pipe', 'ignore'],
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  })
  referencias = JSON.parse(saida.trim().split('\n').pop()!)
})

const score = (n: number) => n.toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })

const escapar = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

async function escolher(page: Page, campo: string, nome: string) {
  await page.getByRole('combobox', { name: campo }).fill(nome)
  await page.getByRole('listbox', { name: campo }).getByRole('option', { name: new RegExp(`^${escapar(nome)}( grupo raro)?$`) }).click()
}

const chip = (page: Page, nome: string) => page.locator('label.chip', { has: page.getByRole('radio', { name: nome, exact: true }) }).click()

async function preencher(page: Page, c: (typeof CASOS)[number]) {
  await chip(page, c.mes)
  await chip(page, c.dia)
  await escolher(page, 'Tipo de local', c.local)
  await escolher(page, 'Bairro', c.entrada.bairro)
}

async function semRolagemHorizontal(page: Page) {
  const excesso = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(excesso).toBeLessThanOrEqual(0)
}

const captura = (page: Page, nome: string, projeto: string) =>
  page.screenshot({ path: resolve(capturas, `${projeto}-${nome}.png`), fullPage: true })

test('resultados na interface correspondem à interface Python segura', async ({ page }, info) => {
  await page.goto('/')
  await expect(page.getByRole('combobox', { name: 'Tipo de local' })).toBeVisible()
  await captura(page, '01-classificador-vazio', info.project.name)
  for (const [i, caso] of CASOS.entries()) {
    await preencher(page, caso)
    await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
    const ref = referencias[i]
    await expect(page.getByText('Classificação estimada')).toBeVisible()
    const painel = page.getByRole('region', { name: 'Resultado' })
    await expect(painel.getByText(ref.classe_estimada, { exact: true })).toBeVisible()
    const scores = page.getByRole('region', { name: 'Scores do modelo' })
    await expect(scores.getByText(score(ref.scores_sigmoid.furto), { exact: true })).toBeVisible()
    await expect(scores.getByText(score(ref.scores_sigmoid.roubo), { exact: true })).toBeVisible()
    await expect(painel.getByText(TEXTO_OBRIGATORIO)).toBeVisible()
    await expect(painel.getByText(`Modelo ${ref.versao_modelo}`, { exact: false })).toBeVisible()
    await expect(painel.getByText('Saídas não calibradas do modelo')).toBeVisible()
    if (i === 0) await captura(page, '02-classificador-resultado', info.project.name)
  }
  await expect(page.getByRole('button', { name: /^Cenário \d/ })).toHaveCount(3)
  await captura(page, '08-cenarios-e-contexto', info.project.name)
  await semRolagemHorizontal(page)
})

test('bairro raro exibe aviso real do contrato', async ({ page, request }, info) => {
  const opcoes = await (await request.get('/api/options')).json()
  const raro = opcoes.bairros.find((b: { grupo: string }) => b.grupo === 'raro').valor
  await page.goto('/')
  await preencher(page, CASOS[0])
  await escolher(page, 'Bairro', raro)
  await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
  await expect(page.getByText('Bairro com representação limitada')).toBeVisible()
  await captura(page, '03-aviso-bairro-raro', info.project.name)
})

test('ausência explícita gera avisos e não mês ou dia ausentes', async ({ page }) => {
  await page.goto('/')
  await escolher(page, 'Tipo de local', 'Não informado')
  await escolher(page, 'Bairro', 'Não informado')
  await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
  await expect(page.getByText('Selecione o mês.')).toBeVisible()
  await chip(page, 'Maio')
  await chip(page, 'Quarta-feira')
  await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
  await expect(page.getByText('Tipo de local com ressalva')).toBeVisible()
  await expect(page.getByText('Campo não informado')).toHaveCount(2)
})

test('API rejeita entradas fora do contrato', async ({ request }) => {
  const valido = CASOS[0].entrada
  for (const corpo of [{ ...valido, tipo_local: 'PRAIA' }, { ...valido, bairro: '123' }, { ...valido, mes: null }, { ...valido, extra: 1 }]) {
    const r = await request.post('/api/classify', { data: corpo })
    expect(r.status()).toBe(422)
    const b = await r.json()
    expect(b.status).toBe('erro_validacao')
    expect(b.scores_sigmoid).toBeUndefined()
  }
})

test('falha de rede e serviço indisponível são informados', async ({ page }, info) => {
  await page.goto('/')
  await preencher(page, CASOS[0])
  await page.route('**/api/classify', (r) => r.abort())
  await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
  await expect(page.getByText('Falha de comunicação')).toBeVisible()
  await captura(page, '04-erro-rede', info.project.name)
  await page.unroute('**/api/classify')
  await page.route('**/api/classify', (r) =>
    r.fulfill({ status: 503, json: { status: 'servico_indisponivel', mensagem: 'O classificador está temporariamente indisponível.' } }),
  )
  await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
  await expect(page.getByText('Serviço indisponível')).toBeVisible()
  await expect(page.getByText('Classificação estimada')).toHaveCount(0)
  await captura(page, '05-servico-indisponivel', info.project.name)
})

test('formulário funciona somente pelo teclado', async ({ page }, info) => {
  test.skip(info.project.name === 'mobile', 'teclado físico é cenário de desktop')
  await page.goto('/')
  await page.getByRole('radio', { name: 'Janeiro' }).focus()
  await page.keyboard.press('Space')
  await page.keyboard.press('Tab')
  await page.keyboard.press('Space')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('combobox', { name: 'Tipo de local' })).toBeFocused()
  await page.keyboard.type('via p')
  await page.keyboard.press('Enter')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('combobox', { name: 'Bairro' })).toBeFocused()
  await page.keyboard.type('bela vis')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('combobox', { name: 'Bairro' })).toHaveValue('BELA VISTA')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Classificar ocorrência' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Classificação estimada')).toBeVisible()
})

test('painel mostra dados históricos reais e filtra', async ({ page }, info) => {
  await page.goto('/painel')
  const tile = page.locator('.card', { hasText: 'Boletins elegíveis' }).first()
  await expect(tile).toContainText('505.187')
  await expect(page.locator('.card', { has: page.locator('p', { hasText: /^Furtos$/ }) }).first()).toContainText('298.083')
  await expect(page.locator('svg.recharts-surface').first()).toBeVisible()
  await page.waitForTimeout(300)
  await captura(page, '06-painel', info.project.name)
  await semRolagemHorizontal(page)
  await page.locator('label', { hasText: /^2024$/ }).click()
  await expect(tile).toContainText('158.895')
  await expect(page.getByText(/preenchimento administrativo da Delegacia Eletrônica/)).toBeVisible()
  await expect(page.getByText(/não são previsões de criminalidade/i)).toBeVisible()
  await semRolagemHorizontal(page)
})

test('metodologia apresenta as métricas publicadas', async ({ page }, info) => {
  await page.goto('/sobre')
  await expect(page.getByRole('cell', { name: '68,82%' }).first()).toBeVisible()
  await expect(page.getByRole('cell', { name: '67,09%' }).first()).toBeVisible()
  await expect(page.getByText('71.598')).toBeVisible()
  await expect(page.getByRole('button', { name: /Dense64 → Dense32/ })).toBeVisible()
  await expect(page.getByText(/não demonstrou vantagem consistente/)).toBeVisible()
  await expect(page.getByRole('link', { name: 'Consultas estatísticas da SSP-SP' })).toHaveAttribute('href', 'https://www.ssp.sp.gov.br/estatistica/consultas')
  await captura(page, '07-sobre', info.project.name)
  await semRolagemHorizontal(page)
})

test.describe('com animações ativas', () => {
  test.use({ contextOptions: { reducedMotion: 'no-preference' } })

  test('números terminam exatos e conteúdo é revelado ao rolar', async ({ page }) => {
    await page.goto('/painel')
    await expect(page.locator('.card', { hasText: 'Boletins elegíveis' }).first()).toContainText('505.187')
    await page.getByRole('heading', { name: 'Mês e dia da semana' }).scrollIntoViewIfNeeded()
    await expect(page.locator('.revelar.visivel').first()).toBeVisible()
    await page.goto('/')
    await preencher(page, CASOS[0])
    await page.getByRole('button', { name: 'Classificar ocorrência' }).click()
    const scores = page.getByRole('region', { name: 'Scores do modelo' })
    await expect(scores.getByText(score(referencias[0].scores_sigmoid.roubo), { exact: true })).toBeVisible()
    await expect(page.locator('path.transicao-arco').first()).toHaveAttribute('stroke-dasharray', /^0\.7/)
  })
})

test('sem erros de console nas páginas', async ({ page }) => {
  const erros: string[] = []
  page.on('console', (m) => m.type() === 'error' && erros.push(m.text()))
  page.on('pageerror', (e) => erros.push(e.message))
  for (const rota of ['/', '/painel', '/sobre']) {
    await page.goto(rota)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.waitForLoadState('networkidle')
  }
  expect(erros).toEqual([])
})

test('arquivos internos não são servidos', async ({ request }) => {
  for (const caminho of ['/models/final/modelo.keras', '/data/processed/base_modelagem.parquet', '/web/backend/data/estatisticas.json', '/api/docs']) {
    expect((await request.get(caminho)).status()).toBe(404)
  }
})
