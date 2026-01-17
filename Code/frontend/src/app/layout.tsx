import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"

import { SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Bell, Search, User, Zap } from "lucide-react"
import { ExportPDFButton } from "@/components/layout/export-pdf-button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "SAED-LLM Visualization",
  description: "Semantic Annotation for Energy Data using LLMs - Visualization Dashboard",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div id="app-container" className="flex h-screen flex-col">
          {/* Top bar - spans full width */}
          <header className="flex h-14 shrink-0 items-center gap-4 border-b bg-background px-4">
            {/* Logo/Brand */}
            <div className="flex items-center gap-2">
              <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                <Zap className="size-4" />
              </div>
              <h1 className="text-lg font-semibold">SAED-LLM</h1>
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Export PDF */}
            <ExportPDFButton />

            {/* Search bar */}
            <div className="hidden md:flex items-center gap-2 w-full max-w-md">
              <div className="relative w-full">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder="Search..."
                  className="pl-8 h-9"
                />
              </div>
            </div>

            {/* Right side actions */}
            <div className="flex items-center gap-2">
              {/* Notifications */}
              <Button variant="ghost" size="icon" className="h-9 w-9">
                <Bell className="h-4 w-4" />
                <span className="sr-only">Notifications</span>
              </Button>

              {/* User menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-9 w-9">
                    <User className="h-4 w-4" />
                    <span className="sr-only">User menu</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>Profile</DropdownMenuItem>
                  <DropdownMenuItem>Settings</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>Log out</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          {/* Main content area with sidebar */}
          <div className="flex flex-1 overflow-hidden">
            <SidebarProvider className="min-h-0 h-full">
              <AppSidebar />
              <main className="flex-1 overflow-auto p-4">
                {children}
              </main>
            </SidebarProvider>
          </div>
        </div>
      </body>
    </html>
  )
}
