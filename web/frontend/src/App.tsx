import { lazy } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import ClassificadorPage from './pages/ClassificadorPage'

const PainelPage = lazy(() => import('./pages/PainelPage'))
const SobrePage = lazy(() => import('./pages/SobrePage'))

function NaoEncontrada() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-xl font-semibold">Página não encontrada</h1>
      <Link className="mt-2 inline-block text-accent underline" to="/">
        Voltar ao classificador
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<ClassificadorPage />} />
        <Route path="painel" element={<PainelPage />} />
        <Route path="sobre" element={<SobrePage />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  )
}
