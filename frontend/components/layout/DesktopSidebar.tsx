"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LayoutGrid, Trophy, User, BookOpen, LogOut, MoreHorizontal, Sun, Moon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";

export default function DesktopSidebar() {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();

    const isActive = (path: string) => pathname === path;

    return (
        <aside className="hidden md:flex flex-col w-[275px] h-screen fixed left-0 top-0 border-r border-gray-200 dark:border-[#2f3336] bg-white dark:bg-black px-4 py-4 z-50">
            {/* Logo */}
            <div className="mb-8 px-4">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
                        <BookOpen className="w-6 h-6" />
                    </div>
                    <span className="text-xl font-bold text-gray-900 dark:text-white">INFINITEST</span>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-2">
                <Link
                    href="/"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <Home className={`w-7 h-7 ${isActive("/") ? "stroke-[2.5px]" : ""}`} />
                    <span>Home</span>
                </Link>

                <Link
                    href="/posts"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/posts")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <LayoutGrid className={`w-7 h-7 ${isActive("/posts") ? "stroke-[2.5px]" : ""}`} />
                    <span>Explore</span>
                </Link>

                <Link
                    href="/leaderboard"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/leaderboard")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <Trophy className={`w-7 h-7 ${isActive("/leaderboard") ? "stroke-[2.5px]" : ""}`} />
                    <span>Leaderboard</span>
                </Link>

                <Link
                    href="/profile"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/profile")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <User className={`w-7 h-7 ${isActive("/profile") ? "stroke-[2.5px]" : ""}`} />
                    <span>Profile</span>
                </Link>
            </nav>

            {/* User Profile / Logout */}
            <div className="mt-auto space-y-2">
                <button
                    onClick={toggleTheme}
                    className="w-full flex items-center gap-4 px-4 py-3 rounded-full hover:bg-gray-100 dark:hover:bg-[#181818] transition-colors text-left text-gray-700 dark:text-gray-300"
                >
                    {theme === 'dark' ? <Sun className="w-7 h-7" /> : <Moon className="w-7 h-7" />}
                    <span className="text-xl">Theme</span>
                </button>

                <button
                    onClick={() => logout()}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-full hover:bg-gray-100 dark:hover:bg-[#181818] transition-colors text-left"
                >
                    <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
                        {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="font-bold text-gray-900 dark:text-white truncate">{user?.name || "User"}</p>
                        <p className="text-sm text-gray-500 truncate">@{user?.username || user?.email?.split('@')[0]}</p>
                    </div>
                    <MoreHorizontal className="w-5 h-5 text-gray-400" />
                </button>
            </div>
        </aside>
    );
}
