import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ServerDetail from './pages/ServerDetail'
import Login from './pages/Login'

export default function App(){
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-white">
        <header className="p-4 border-b border-slate-700">
          <div className="container mx-auto flex justify-between">
            <h1 className="text-xl font-bold">The Observer</h1>
            <nav className="space-x-4">
              <Link to="/">Dashboard</Link>
              <Link to="/login">Login</Link>
            </nav>
          </div>
        </header>

        <main className="container mx-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard/>} />
            <Route path="/agent/:id" element={<ServerDetail/>} />
            <Route path="/login" element={<Login/>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
