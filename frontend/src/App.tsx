import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Home from './pages/Home'
import ContentDetail from './pages/ContentDetail'
import Review from './pages/Review'
import Settings from './pages/Settings'
import Pool from './pages/Pool'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-primary">
        <nav className="sticky top-0 z-50 bg-card border-b border-border px-4 py-3">
          <div className="max-w-2xl mx-auto flex items-center justify-between">
            <h1 className="text-accent font-bold text-lg">LangDive</h1>
            <div className="flex gap-4">
              <NavLink to="/" className={({isActive}) => isActive ? 'text-accent' : 'text-text-secondary hover:text-text-primary'}>Home</NavLink>
              <NavLink to="/review" className={({isActive}) => isActive ? 'text-accent' : 'text-text-secondary hover:text-text-primary'}>Review</NavLink>
              <NavLink to="/settings" className={({isActive}) => isActive ? 'text-accent' : 'text-text-secondary hover:text-text-primary'}>Settings</NavLink>
            </div>
          </div>
        </nav>
        <main className="max-w-2xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/content/:id" element={<ContentDetail />} />
            <Route path="/review" element={<Review />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/pool" element={<Pool />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
