"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LayoutGrid, Trophy, Settings, Feather, BookOpen, LifeBuoy, Zap } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function MobileNav() {
    const pathname = usePathname();
    const { user } = useAuth();

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
            <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-black px-4 py-2 flex justify-between items-center z-50 md:hidden">
                {/* Upgrade pill — floats above the nav bar for free users */}
                {(!user?.plan || user.plan === "free" || user.plan === "earth") && (
                    <Link
                        href="/pricing"
                        className="absolute -top-10 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-semibold shadow-lg hover:opacity-90 transition-opacity"
                    >
                        <Zap className="w-3 h-3" />
                        {user?.plan === "earth" ? "Go Universe ₹99" : "Upgrade ₹19"}
                    </Link>
                )}
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
                    href="/community"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/community") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <BookOpen className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Test Portal</span>
                </Link>

                <Link
                    href="/support"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/support") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <LifeBuoy className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Support</span>
                </Link>

                <Link
                    href="/settings"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/settings") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <Settings className="w-6 h-6" />
                    <span className="text-[10px] font-medium">Settings</span>
                </Link>
            </nav>
        </>
    );
}

