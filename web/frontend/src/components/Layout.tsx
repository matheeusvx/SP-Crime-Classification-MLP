import { Suspense, useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Carregando } from '../ui/base'

const LINKS = [
  { para: '/', rotulo: 'Classificador', fim: true },
  { para: '/painel', rotulo: 'Painel histórico', fim: false },
  { para: '/sobre', rotulo: 'Sobre o modelo', fim: false },
]

const TITULOS: Record<string, string> = {
  '/': 'Classificador MLP',
  '/painel': 'Painel histórico',
  '/sobre': 'Sobre o modelo',
}

export function Layout() {
  const { pathname } = useLocation()
  const principal = useRef<HTMLElement>(null)
  const primeiraCarga = useRef(true)
  const indice = LINKS.findIndex((l) => l.para === pathname)

  useEffect(() => {
    document.title = `${TITULOS[pathname] ?? 'Página não encontrada'} — Celulares subtraídos em SP`
    if (primeiraCarga.current) {
      primeiraCarga.current = false
      return
    }
    window.scrollTo?.(0, 0)
    principal.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
        Ir para o conteúdo
      </a>
      <header className="z-40 sm:sticky sm:top-0 border-b border-line/70 bg-surface/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[76rem] flex-col gap-2 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-2.5">
            <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-lg bg-ink">
              <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="#fff" strokeWidth={1.6}>
                <path d="M6 12 18 6M6 12l12 6" />
                <circle cx="6" cy="12" r="2.4" fill="#fff" />
                <circle cx="18" cy="6" r="2.4" fill="#fff" />
                <circle cx="18" cy="18" r="2.4" fill="#fff" />
              </svg>
            </span>
            <div>
              <p className="text-sm font-semibold leading-tight">Celulares subtraídos em São Paulo</p>
              <p className="text-xs text-ink-3">Demonstração acadêmica · Global Solution FIAP</p>
            </div>
          </div>
          <nav aria-label="Principal" className="relative grid grid-cols-3 rounded-xl bg-soft p-1 sm:w-[27rem]">
            {indice >= 0 && (
              <span aria-hidden="true" className="transicao-pilula absolute inset-y-1 left-1 w-[calc((100%-0.5rem)/3)] rounded-lg bg-surface shadow-sm" style={{ transform: `translateX(${indice * 100}%)` }} />
            )}
            {LINKS.map((l) => (
              <NavLink
                key={l.para}
                to={l.para}
                end={l.fim}
                className={({ isActive }) => `relative z-[1] whitespace-nowrap rounded-lg px-1 py-1.5 text-center text-[13px] font-medium transition-colors sm:text-sm ${isActive ? 'text-ink' : 'text-ink-3 hover:text-ink'}`}
              >
                {l.rotulo}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="conteudo" ref={principal} tabIndex={-1} className="mx-auto w-full max-w-[76rem] flex-1 px-4 py-7 outline-none sm:px-6">
        <Suspense fallback={<Carregando texto="Carregando página…" />}>
          <div key={pathname} className="pagina">
            <Outlet />
          </div>
        </Suspense>
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-[76rem] space-y-1 px-4 py-5 text-xs text-ink-3 sm:px-6">
          <p>Projeto acadêmico Global Solution FIAP 2026.2. Não é um sistema oficial da SSP-SP e não foi validado para decisões policiais ou operacionais.</p>
          <p>
            Fonte dos dados:{' '}
            <a className="underline hover:text-ink" href="https://www.ssp.sp.gov.br/estatistica/consultas" target="_blank" rel="noreferrer">
              Secretaria da Segurança Pública do Estado de São Paulo
            </a>
            .
          </p>
        </div>
      </footer>
    </div>
  )
}
