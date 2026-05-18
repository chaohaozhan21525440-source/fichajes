import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/',               label: 'Inicio',         icon: '🏠' },
  { to: '/checkins',       label: 'Fichajes',       icon: '🕐' },
  { to: '/late-arrivals',  label: 'Retrasos',       icon: '⏰' },
  { to: '/workers',        label: 'Trabajadores',   icon: '👥' },
  { to: '/audit',          label: 'Auditoría',      icon: '📋' },
  { to: '/settings',       label: 'Configuración',  icon: '⚙️' },
]

export default function Layout() {
  const { logout } = useAuth()
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <img src="/logo.svg" alt="Logo" />
          <div className="sidebar-brand-text">
            <strong>Fichajes</strong>
            <small>NFC</small>
          </div>
        </div>
        <nav>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              <span>{l.icon}</span>
              <span>{l.label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="btn btn-outline sidebar-logout" onClick={logout}>
          Cerrar sesión
        </button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
