import { Outlet } from 'react-router-dom'
import Sidebar from '@/components/Sidebar'
import { useState } from 'react'

export default function DashboardLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-white">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      
      {/* Main content */}
      <div className={`transition-all duration-200 ${
        sidebarCollapsed ? 'pl-16' : 'pl-64'
      }`}>
        <main className="min-h-screen">
          <Outlet />
        </main>
      </div>
    </div>
  )
}