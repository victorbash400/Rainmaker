import { Outlet } from 'react-router-dom'
import { Circle } from 'lucide-react'

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-cover bg-center bg-no-repeat relative"
         style={{
           backgroundImage: 'url(/assets/before.jpg)'
         }}>
      {/* Soft overlay for better text readability */}
      <div className="absolute inset-0 bg-black/20 pointer-events-none"></div>
      
      {/* Top left logo */}
      <div className="absolute top-6 left-6 z-20 flex items-center space-x-2">
        <Circle className="h-6 w-6 fill-white text-white" />
        <span className="text-white text-lg font-medium">Rainmaker</span>
      </div>
      
      <div className="relative z-10 min-h-screen flex items-center justify-center px-6">
        {/* Content */}
        <Outlet />
      </div>
    </div>
  )
}