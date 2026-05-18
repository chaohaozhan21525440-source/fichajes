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
          <div className="sidebar-brand-logo">
            <img src="/logo.png" alt="Logo" />
          </div>
          <div className="sidebar-brand-text">
            <strong>Fichajes</strong>
            <small>Panel admin</small>
          </div>
        </div>

        <div className="sidebar-section">Menú</div>
        <nav>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              <span className="nav-icon">{l.icon}</span>
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
