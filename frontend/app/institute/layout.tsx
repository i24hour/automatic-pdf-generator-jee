"use client";

import { InstituteAuthProvider } from "@/contexts/institute-auth-context";

export default function InstituteLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <InstituteAuthProvider>
            {children}
        </InstituteAuthProvider>
    );
}
