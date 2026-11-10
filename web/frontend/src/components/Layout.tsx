import { Suspense, useEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Carregando } from './Status'

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
      <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-10 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Ir para o conteúdo
      </a>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <p className="text-[15px] font-semibold leading-tight">Celulares subtraídos em São Paulo</p>
            <p className="text-xs text-ink-3">Demonstração acadêmica · Global Solution FIAP</p>
          </div>
          <nav aria-label="Principal" className="-mx-1 flex gap-1 overflow-x-auto">
            {LINKS.map((l) => (
              <NavLink
                key={l.para}
                to={l.para}
                end={l.fim}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${
                    isActive ? 'bg-accent-soft text-accent-dark' : 'text-ink-2 hover:bg-paper hover:text-ink'
                  }`
                }
              >
                {l.rotulo}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="conteudo" ref={principal} tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 outline-none sm:px-6">
        <Suspense fallback={<Carregando texto="Carregando página…" />}>
          <Outlet />
        </Suspense>
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-6xl space-y-1 px-4 py-5 text-xs text-ink-3 sm:px-6">
          <p>
            Projeto acadêmico Global Solution FIAP 2026.2. Não é um sistema oficial da SSP-SP e não foi validado para decisões policiais ou
            operacionais.
          </p>
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
