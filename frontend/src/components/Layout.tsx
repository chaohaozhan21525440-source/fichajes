import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/',               label: '🏠 Inicio' },
  { to: '/checkins',       label: '🕐 Fichajes' },
  { to: '/late-arrivals',  label: '⏰ Retrasos' },
  { to: '/workers',        label: '👥 Trabajadores' },
  { to: '/audit',          label: '📋 Auditoría' },
]

export default function Layout() {
  const { logout } = useAuth()
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">Fichajes NFC</div>
        <nav>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              {l.label}
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
