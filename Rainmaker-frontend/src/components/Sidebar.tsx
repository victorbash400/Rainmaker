import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useState } from 'react'
import {
  Target,
  MessageSquare,
  FileText,
  Calendar,
  Activity,
  LogOut,
  ChevronLeft,
  Menu,
  Circle,
} from 'lucide-react'

const navigation = [
  { name: 'Rainmaker', href: '/', icon: Circle },
  { name: 'Workflows', href: '/workflows', icon: Activity },
  { name: 'Prospects', href: '/prospects', icon: Target },
  { name: 'Conversations', href: '/conversations', icon: MessageSquare },
  { name: 'Proposals', href: '/proposals', icon: FileText },
  { name: 'Meetings', href: '/meetings', icon: Calendar },
]

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ')
}

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
}

export default function Sidebar({ collapsed, onToggleCollapse }: SidebarProps) {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  return (
    <div className={`fixed inset-y-0 left-0 z-50 bg-white border-r border-gray-200 transition-all duration-200 ${
      collapsed ? 'w-16' : 'w-64'
    }`}>
      <div className="flex h-16 items-center px-4 justify-between">
        {!collapsed && (
          <div className="flex items-center space-x-2">
            <Circle className="h-4 w-4 fill-current" />
            <h1 className="text-base font-semibold">Rainmaker</h1>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
        >
          {collapsed ? (
            <Menu className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>
      
      <nav className="mt-6 px-3">
        <ul className={`space-y-1 ${collapsed ? 'items-center' : ''}`}>
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  className={classNames(
                    isActive
                      ? 'bg-gray-100 text-black'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-black',
                    collapsed 
                      ? 'flex items-center justify-center p-2 rounded-lg transition-all duration-200'
                      : 'group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200'
                  )}
                  title={collapsed ? item.name : undefined}
                >
                  <item.icon
                    className={classNames(
                      isActive ? 'text-black' : 'text-gray-400 group-hover:text-gray-600',
                      item.name === 'Rainmaker' ? 'h-4 w-4 fill-current' : 'h-4 w-4',
                      !collapsed && 'mr-3'
                    )}
                    aria-hidden="true"
                  />
                  {!collapsed && item.name}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* User menu */}
      <div className="absolute bottom-0 left-0 right-0 p-3">
        {collapsed ? (
          <div className="flex flex-col items-center space-y-2">
            <div className="h-8 w-8 rounded-full bg-black flex items-center justify-center">
              <span className="text-sm font-medium text-white">
                {user?.name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-black transition-colors p-1 rounded"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="h-8 w-8 rounded-full bg-black flex items-center justify-center">
                <span className="text-sm font-medium text-white">
                  {user?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-black">{user?.name}</p>
                <p className="text-xs text-gray-500">{user?.role}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-black transition-colors p-1 rounded"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}