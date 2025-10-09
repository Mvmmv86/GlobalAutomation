import React, { createContext, useContext, useState, ReactNode } from 'react'

interface NavbarContextType {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
  toggleNavbar: () => void
}

const NavbarContext = createContext<NavbarContextType | undefined>(undefined)

interface NavbarProviderProps {
  children: ReactNode
}

export const NavbarProvider: React.FC<NavbarProviderProps> = ({ children }) => {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const toggleNavbar = () => {
    setIsCollapsed(prev => !prev)
  }

  return (
    <NavbarContext.Provider value={{
      isCollapsed,
      setIsCollapsed,
      toggleNavbar
    }}>
      {children}
    </NavbarContext.Provider>
  )
}

export const useNavbar = (): NavbarContextType => {
  const context = useContext(NavbarContext)
  if (context === undefined) {
    throw new Error('useNavbar must be used within a NavbarProvider')
  }
  return context
}