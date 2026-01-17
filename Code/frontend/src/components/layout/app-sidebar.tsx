"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Table2,
  Network,
  Play,
  History,
  Settings,
  ChevronLeft,
  ClipboardCheck,
  FileText,
  FolderArchive,
  PlusCircle,
  GitCompare,
} from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"

const mainNavItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Tables",
    url: "/tables",
    icon: Table2,
  },
  {
    title: "Ontology",
    url: "/ontology",
    icon: Network,
  },
  {
    title: "Labels",
    url: "/labels",
    icon: FileText,
  },
  {
    title: "Batches",
    url: "/batches",
    icon: FolderArchive,
  },
]

const annotationNavItems = [
  {
    title: "New Run",
    url: "/annotations/new",
    icon: Play,
  },
  {
    title: "Run History",
    url: "/annotations",
    icon: History,
  },
]

const evaluationNavItems = [
  {
    title: "New Evaluation",
    url: "/evaluation/new",
    icon: PlusCircle,
  },
  {
    title: "Compare",
    url: "/evaluation/compare",
    icon: GitCompare,
  },
]

export function AppSidebar() {
  const pathname = usePathname()
  const { toggleSidebar } = useSidebar()

  return (
    <Sidebar collapsible="icon" className="top-14 h-[calc(100vh-3.5rem)]">
      <SidebarHeader>
        <div className="flex items-center justify-end p-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="h-8 w-8"
          >
            <ChevronLeft className="h-4 w-4 transition-transform duration-200 group-data-[collapsible=icon]:rotate-180" />
            <span className="sr-only">Toggle Sidebar</span>
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={
                      item.url === "/"
                        ? pathname === "/"
                        : pathname.startsWith(item.url)
                    }
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Annotations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {annotationNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === item.url}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Evaluation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {evaluationNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith(item.url)}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              isActive={pathname === "/settings"}
              tooltip="Settings"
            >
              <Link href="/settings">
                <Settings />
                <span>Settings</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
