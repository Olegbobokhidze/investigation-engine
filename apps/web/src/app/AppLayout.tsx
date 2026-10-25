import clsx from "clsx";
import { FileText, Search, type LucideIcon } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router";

import { paths } from "@/shared/config/paths";
import { LogoMark } from "@/shared/ui/LogoMark";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const navItems: NavItem[] = [
  { to: paths.investigate, label: "Investigate", icon: Search },
  { to: paths.documents, label: "Documents", icon: FileText },
];

export function AppLayout() {
  return (
    // The window never scrolls: the header stays put and <main> scrolls instead.
    <div className="flex h-dvh flex-col">
      <header className="flex shrink-0 flex-wrap items-center gap-x-8 gap-y-3 border-b border-border bg-surface px-8 py-3">
        <Link to={paths.investigate} className="flex items-center gap-2.5 rounded-lg focus-ring">
          <LogoMark />
          <span className="text-base font-semibold tracking-tight">Investigation Engine</span>
        </Link>
        <nav aria-label="Main" className="flex gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                clsx(
                  "inline-flex h-10 items-center gap-2 rounded-control px-3.5 text-md font-medium focus-ring transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-ink-secondary hover:bg-subtle hover:text-ink",
                )
              }
            >
              <Icon aria-hidden className="size-4.5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
