"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function InstituteLoginRedirect() {
    const router = useRouter();
    useEffect(() => { router.replace("/generator"); }, [router]);
    return null;
}
