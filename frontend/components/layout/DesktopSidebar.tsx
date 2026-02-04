"use client";

import { useState } from "react";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Home, LayoutGrid, Trophy, User, Infinity as InfinityIcon, LogOut, MoreHorizontal, Sun, Moon, Settings, BookOpen } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";

export default function DesktopSidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const [showLogoutMenu, setShowLogoutMenu] = useState(false);

    const isActive = (path: string) => pathname === path;

    return (
        <aside className="hidden md:flex flex-col w-[275px] h-screen fixed left-0 top-0 border-r border-border bg-glass backdrop-blur-xl px-4 py-6 z-50">
            <div className="mb-10 px-4">
                <Link href="/" className="flex items-center gap-3 group">
                    <div className="w-11 h-11 rounded-2xl bg-white flex items-center justify-center p-1.5 shadow-lg shadow-primary/10 group-hover:scale-110 transition-transform duration-300 overflow-hidden">
                        <img src="/logo.png" alt="INFINITEST Logo" className="w-full h-full object-contain" />
                    </div>
                    <span className="text-2xl font-black tracking-tighter text-foreground group-hover:brightness-110 transition-all">INFINITEST</span>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1.5">
                {[
                    { href: "/", icon: Home, label: "Home" },
                    { href: "/generator", icon: InfinityIcon, label: "INFINITEST" },
                    { href: "/test", icon: BookOpen, label: "Test Portal" },
                    { href: "/posts", icon: LayoutGrid, label: "Explore" },
                    { href: "/leaderboard", icon: Trophy, label: "Leaderboard" },
                    { href: "/profile", icon: User, label: "Profile" },
                    { href: "/settings", icon: Settings, label: "Settings" },
                ].map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-4 px-4 py-3.5 rounded-2xl text-lg transition-all duration-200 group ${isActive(item.href)
                            ? "bg-primary/10 text-primary font-bold shadow-sm"
                            : "text-text-muted hover:bg-secondary hover:text-foreground"
                            }`}
                    >
                        <item.icon className={`w-6 h-6 transition-transform group-hover:scale-110 ${isActive(item.href) ? "stroke-[2.5px]" : ""}`} />
                        <span>{item.label}</span>
                    </Link>
                ))}
            </nav>

            {/* User Profile / Logout */}
            <div className="mt-auto space-y-4">
                <button
                    onClick={toggleTheme}
                    className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl hover:bg-secondary transition-all text-left text-text-muted hover:text-foreground group"
                >
                    <div className="w-6 h-6 flex items-center justify-center group-hover:rotate-12 transition-transform">
                        {theme === 'dark' ? <Sun className="w-6 h-6" /> : <Moon className="w-6 h-6" />}
                    </div>
                    <span className="text-lg">Theme</span>
                </button>

                <div className="relative">
                    {showLogoutMenu && (
                        <>
                            <div
                                className="fixed inset-0 z-40"
                                onClick={() => setShowLogoutMenu(false)}
                            />
                            <div className="absolute bottom-full left-0 w-full mb-4 glass-card overflow-hidden z-50 py-2 animate-in fade-in slide-in-from-bottom-4 duration-300">
                                <button
                                    onClick={async () => {
                                        await logout();
                                        setShowLogoutMenu(false);
                                        router.push("/login");
                                    }}
                                    className="w-full text-left px-5 py-3 hover:bg-red-500/10 hover:text-red-500 transition-colors font-bold text-foreground"
                                >
                                    Log out @{user?.username || user?.email?.split('@')[0]}
                                </button>
                            </div>
                        </>
                    )}
                    <button
                        onClick={() => setShowLogoutMenu(!showLogoutMenu)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl hover:bg-secondary transition-all text-left group border border-transparent hover:border-border"
                    >
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold flex-shrink-0 shadow-sm">
                            {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-bold text-foreground truncate">{user?.name || "User"}</p>
                            <p className="text-xs text-text-muted truncate">@{user?.username || user?.email?.split('@')[0]}</p>
                        </div>
                        <MoreHorizontal className="w-4 h-4 text-text-muted group-hover:text-foreground transition-colors" />
                    </button>
                </div>
            </div>
        </aside>
    );
}
