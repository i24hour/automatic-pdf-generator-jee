"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LayoutGrid, Trophy, Search, Feather, Sun, Moon } from "lucide-react";
import { useTheme } from "@/lib/theme-context";

export default function MobileNav() {
    const pathname = usePathname();
    const { theme, toggleTheme } = useTheme();

    const isActive = (path: string) => pathname === path;

    return (
        <>
            {/* Floating Action Button (FAB) - Only on specific pages or always? 
          User said "feather jaisa jo aa raha isse click krne se test generator pr hi pahuchenge"
          If we are already on generator (Home), maybe hide it? 
          Or maybe this IS the way to get to generator if we are on other tabs.
      */}
            {pathname !== "/" && (
                <Link
                    href="/"
                    className="fixed bottom-20 right-4 w-14 h-14 bg-indigo-600 rounded-full flex items-center justify-center text-white shadow-lg hover:bg-indigo-700 transition-colors z-50 md:hidden"
                >
                    <Feather className="w-6 h-6" />
                </Link>
            )}

            {/* Bottom Navigation Bar */}
            <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-4 py-2 flex justify-between items-center z-50 md:hidden">
                <Link
                    href="/"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <Home className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Home</span>
                </Link>

                <Link
                    href="/posts"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/posts") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <LayoutGrid className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Feed</span>
                </Link>

                <Link
                    href="/leaderboard"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/leaderboard") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <Trophy className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Rank</span>
                </Link>

                <button
                    className="flex flex-col items-center gap-1 p-2 text-gray-500 dark:text-gray-400"
                    onClick={toggleTheme}
                >
                    {theme === 'dark' ? <Sun className="w-6 h-6" /> : <Moon className="w-6 h-6" />}
                    <span className="text-[10px] font-medium">Theme</span>
                </button>
            </nav>
        </>
    );
}
