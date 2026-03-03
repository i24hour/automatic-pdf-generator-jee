'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// This page was moved to /test/create
export default function CommunityCreateRedirect() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/test/create');
    }, [router]);

    return null;
}
