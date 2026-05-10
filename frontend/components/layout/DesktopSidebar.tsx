"use client";

import { useState } from "react";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Home, LayoutGrid, Trophy, User, Infinity as InfinityIcon, LogOut, MoreHorizontal, Sun, Moon, Settings, BookOpen, LifeBuoy, FileText } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";

export default function DesktopSidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const [showLogoutMenu, setShowLogoutMenu] = useState(false);

    const isActive = (path: string) => pathname === path;

    return (
        <aside className="hidden md:flex flex-col w-[275px] h-screen fixed left-0 top-0 border-r border-gray-200 dark:border-[#2f3336] bg-white dark:bg-black px-4 py-4 z-50">
            {/* Logo */}
            <div className="mb-8 px-4">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
                        <InfinityIcon className="w-6 h-6" />
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
                    href="/generator"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/generator")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <InfinityIcon className={`w-7 h-7 ${isActive("/generator") ? "stroke-[2.5px]" : ""}`} />
                    <span>INFINITEST</span>
                </Link>

                <Link
                    href="/community"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/community")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <BookOpen className={`w-7 h-7 ${isActive("/community") ? "stroke-[2.5px]" : ""}`} />
                    <span>Test Portal</span>
                </Link>

                <Link
                    href="/pdf-to-test"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/pdf-to-test")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <FileText className={`w-7 h-7 ${isActive("/pdf-to-test") ? "stroke-[2.5px]" : ""}`} />
                    <span>PDF2Test</span>
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

                {/* <Link
                    href="/video-generator"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/video-generator")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <Video className={`w-7 h-7 ${isActive("/video-generator") ? "stroke-[2.5px]" : ""}`} />
                    <span>Video Generator</span>
                </Link> */}

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

                <Link
                    href="/support"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/support")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <LifeBuoy className={`w-7 h-7 ${isActive("/support") ? "stroke-[2.5px]" : ""}`} />
                    <span>Support</span>
                </Link>

                <Link
                    href="/settings"
                    className={`flex items-center gap-4 px-4 py-3 rounded-full text-xl transition-colors ${isActive("/settings")
                        ? "font-bold text-gray-900 dark:text-white"
                        : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#181818]"
                        }`}
                >
                    <Settings className={`w-7 h-7 ${isActive("/settings") ? "stroke-[2.5px]" : ""}`} />
                    <span>Settings</span>
                </Link>
            </nav>

            {/* User Profile / Logout */}
            <div className="mt-auto space-y-2">

                {/* Upgrade CTA — only show for free / earth users */}
                {(!user?.plan || user.plan === "free") && (
                    <Link
                        href="/pricing"
                        className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90 transition-opacity"
                    >
                        <div className="min-w-0">
                            <p className="font-bold text-sm leading-tight">Upgrade to Pro</p>
                            <p className="text-xs text-indigo-200 leading-tight">Earth ₹19 · Universe ₹99</p>
                        </div>
                    </Link>
                )}
                {user?.plan === "earth" && (
                    <Link
                        href="/pricing"
                        className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-gradient-to-r from-green-600 to-teal-600 text-white hover:opacity-90 transition-opacity"
                    >
                        <div className="min-w-0">
                            <p className="font-bold text-sm leading-tight">Upgrade to Universe</p>
                            <p className="text-xs text-green-200 leading-tight">Unlimited everything · ₹99/mo</p>
                        </div>
                    </Link>
                )}
                <button
                    onClick={toggleTheme}
                    className="w-full flex items-center gap-4 px-4 py-3 rounded-full hover:bg-gray-100 dark:hover:bg-[#181818] transition-colors text-left text-gray-700 dark:text-gray-300"
                >
                    {theme === 'dark' ? <Sun className="w-7 h-7" /> : <Moon className="w-7 h-7" />}
                    <span className="text-xl">Theme</span>
                </button>

                <div className="relative">
                    {showLogoutMenu && (
                        <>
                            <div
                                className="fixed inset-0 z-40"
                                onClick={() => setShowLogoutMenu(false)}
                            />
                            <div className="absolute bottom-full left-0 w-[300px] mb-4 bg-white dark:bg-black rounded-2xl shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_0_15px_rgba(255,255,255,0.1)] border border-gray-100 dark:border-[#2f3336] overflow-hidden z-50 py-2">
                                <button
                                    onClick={async () => {
                                        await logout();
                                        setShowLogoutMenu(false);
                                        router.push("/login");
                                    }}
                                    className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-[#16181c] transition-colors font-bold text-gray-900 dark:text-white"
                                >
                                    Log out @{user?.username || user?.email?.split('@')[0]}
                                </button>
                            </div>
                        </>
                    )}
                    <button
                        onClick={() => setShowLogoutMenu(!showLogoutMenu)}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-full hover:bg-gray-100 dark:hover:bg-[#181818] transition-colors text-left"
                    >
                        <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center text-white font-semibold flex-shrink-0">
                            {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U"}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-bold text-gray-900 dark:text-white truncate">{user?.name || "User"}</p>
                            <p className="text-sm text-gray-500 truncate flex items-center gap-1.5">
                                @{user?.username || user?.email?.split('@')[0]}
                                {user?.plan && user.plan !== "free" && (
                                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${
                                        user.plan === "universe"
                                            ? "bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300"
                                            : "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
                                    }`}>
                                        {user.plan}
                                    </span>
                                )}
                            </p>
                        </div>
                        <MoreHorizontal className="w-5 h-5 text-gray-400" />
                    </button>
                </div>
            </div>
        </aside>
    );
}
