"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, LayoutGrid, Trophy, Settings, BookOpen, LifeBuoy, Zap, FileText } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function MobileNav() {
    const pathname = usePathname();
    const { user } = useAuth();

    const isActive = (path: string) => pathname === path;

    return (
        <>
            {/* Bottom Navigation Bar */}
            <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-black px-4 py-2 flex justify-between items-center z-50 md:hidden">
                {/* Upgrade pill — only for free users */}
                {(!user?.plan || user.plan === "free") && (
                    <Link
                        href="/pricing"
                        className="absolute -top-10 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-semibold shadow-lg hover:opacity-90 transition-opacity"
                    >
                        <Zap className="w-3 h-3" />
                        Upgrade ₹19
                    </Link>
                )}
                {user?.plan === "earth" && (
                    <Link
                        href="/pricing"
                        className="absolute -top-10 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gradient-to-r from-green-500 to-teal-500 text-white text-xs font-semibold shadow-lg hover:opacity-90 transition-opacity"
                    >
                        <Zap className="w-3 h-3" />
                        Go Universe ₹99
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
                    href="/pdf-to-test"
                    className={`flex flex-col items-center gap-1 p-2 ${isActive("/pdf-to-test") ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 dark:text-gray-400"
                        }`}
                >
                    <FileText className="w-6 h-6" />
                    <span className="text-[10px] font-medium">PDF2Test</span>
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
                    {user?.plan && user.plan !== "free" && (
                        <span className={`text-[8px] font-bold uppercase px-1 rounded-full leading-tight ${
                            user.plan === "universe"
                                ? "bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300"
                                : "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
                        }`}>
                            {user.plan}
                        </span>
                    )}
                </Link>
            </nav>
        </>
    );
}

