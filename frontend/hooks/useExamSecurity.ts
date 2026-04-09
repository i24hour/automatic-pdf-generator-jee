import { useEffect, useState, useCallback, useRef } from 'react';

interface SecurityLog {
    tabSwitchCount: number;
    fullscreenExitCount: number;
    devtoolsAttempts: number;
    copyAttempts: number;
    totalWarnings: number;
}

interface UseExamSecurityProps {
    isExamActive: boolean;
    onSubmitExam: () => void;
}

export function useExamSecurity({ isExamActive, onSubmitExam }: UseExamSecurityProps) {
    const [warningMessage, setWarningMessage] = useState<string | null>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    
    // Use refs for mutable values that don't need to trigger re-renders
    // but need to be accessed inside event listeners
    const logRef = useRef<SecurityLog>({
        tabSwitchCount: 0,
        fullscreenExitCount: 0,
        devtoolsAttempts: 0,
        copyAttempts: 0,
        totalWarnings: 0
    });
    
    const isExamActiveRef = useRef(isExamActive);
    const isSubmittingRef = useRef(false);

    useEffect(() => {
        isExamActiveRef.current = isExamActive;
    }, [isExamActive]);

    const handleViolation = useCallback((type: keyof SecurityLog, message: string) => {
        if (!isExamActiveRef.current || isSubmittingRef.current) return;

        // Increment the specific violation and total warnings
        logRef.current[type]++;
        if (type !== 'totalWarnings') {
            logRef.current.totalWarnings++;
        }

        console.warn(`SECURITY VIOLATION: ${message}. Total Warnings: ${logRef.current.totalWarnings}`);

        if (logRef.current.totalWarnings >= 2) {
            setWarningMessage("Maximum warnings exceeded. Your exam is being automatically submitted.");
            isSubmittingRef.current = true;
            
            // Optionally: send logRef.current to backend here before submit
            // await fetch('/api/security-log', { method: 'POST', body: JSON.stringify(logRef.current) })

            // Give the user a moment to see the final message before submitting
            setTimeout(() => {
                onSubmitExam();
            }, 3000);
        } else {
            setWarningMessage(`${message} (Warning ${logRef.current.totalWarnings} of 2)`);
        }
    }, [onSubmitExam]);


    const enterFullscreen = useCallback(() => {
        if (typeof window === 'undefined') return;
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`);
            });
        }
    }, []);

    // 1 & 2. Auto-fullscreen & Click-to-fullscreen
    useEffect(() => {
        if (!isExamActive) return;

        // Attempt immediately
        setTimeout(() => enterFullscreen(), 1000);

        // Attempt on first document click
        const handleFirstClick = () => {
            if (!document.fullscreenElement) {
                enterFullscreen();
            }
        };
        
        document.addEventListener('click', handleFirstClick);
        return () => document.removeEventListener('click', handleFirstClick);
    }, [isExamActive, enterFullscreen]);

    // 3. Fullscreen exit detection
    useEffect(() => {
        if (!isExamActive) return;

        const handleFullscreenChange = () => {
            const isFs = !!document.fullscreenElement;
            setIsFullscreen(isFs);
            
            if (!isFs) {
                handleViolation('fullscreenExitCount', 'You exited fullscreen mode.');
            }
        };

        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, [isExamActive, handleViolation]);

    // 4. Tab switching (visibilitychange)
    useEffect(() => {
        if (!isExamActive) return;

        const handleVisibilityChange = () => {
            if (document.visibilityState === 'hidden') {
                handleViolation('tabSwitchCount', 'You navigated away from the exam window.');
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
    }, [isExamActive, handleViolation]);

    // 5 & 6 & 9. Disable Right-click, Copy, Cut, Paste, Selection
    useEffect(() => {
        if (!isExamActive) return;

        const preventDefaultAndWarn = (e: Event, type: 'copyAttempts', msg: string) => {
            e.preventDefault();
            handleViolation(type, msg);
        };

        const handleContextMenu = (e: MouseEvent) => {
            e.preventDefault();
        };

        const handleCopy = (e: ClipboardEvent) => preventDefaultAndWarn(e, 'copyAttempts', 'Copying is disabled.');
        const handleCut = (e: ClipboardEvent) => preventDefaultAndWarn(e, 'copyAttempts', 'Cutting is disabled.');
        const handlePaste = (e: ClipboardEvent) => preventDefaultAndWarn(e, 'copyAttempts', 'Pasting is disabled.');

        // 9. Disable text selection (CSS is better but JS prevents keyboard select-all)
        const handleSelectStart = (e: Event) => e.preventDefault();
        const handleKeyDown = (e: KeyboardEvent) => {
            // Block Ctrl+A / Cmd+A
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a') {
                e.preventDefault();
            }
        };

        document.addEventListener('contextmenu', handleContextMenu);
        document.addEventListener('copy', handleCopy);
        document.addEventListener('cut', handleCut);
        document.addEventListener('paste', handlePaste);
        document.addEventListener('selectstart', handleSelectStart);
        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.removeEventListener('contextmenu', handleContextMenu);
            document.removeEventListener('copy', handleCopy);
            document.removeEventListener('cut', handleCut);
            document.removeEventListener('paste', handlePaste);
            document.removeEventListener('selectstart', handleSelectStart);
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isExamActive, handleViolation]);

    // 7. Prevent DevTools Shortcuts
    useEffect(() => {
        if (!isExamActive) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            const isCtrlOrCmd = e.ctrlKey || e.metaKey;
            const isBlocked = 
                e.key === 'F12' || 
                (isCtrlOrCmd && e.shiftKey && e.key.toLowerCase() === 'i') || // Ctrl+Shift+I
                (isCtrlOrCmd && e.shiftKey && e.key.toLowerCase() === 'j') || // Ctrl+Shift+J
                (isCtrlOrCmd && e.shiftKey && e.key.toLowerCase() === 'c') || // Ctrl+Shift+C
                (isCtrlOrCmd && e.key.toLowerCase() === 'u');                 // Ctrl+U

            if (isBlocked) {
                e.preventDefault();
                handleViolation('devtoolsAttempts', 'Developer tools and source inspection are disabled.');
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isExamActive, handleViolation]);

    // 8. Periodic DevTools Detection via Window Resize/Thresholds
    useEffect(() => {
        if (!isExamActive) return;

        const checkDevTools = () => {
            if (typeof navigator !== 'undefined' && /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                return; // Skip heuristic check on mobile (fixes false positives from browser bars/keyboards)
            }
            
            // A common heuristic: if outer window is significantly larger than inner window,
            // DevTools might be open docked. 
            // NOTE: This can sometimes false positive on zooming, but it's a common primitive check.
            const threshold = 160;
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            
            if (widthDiff > threshold || heightDiff > threshold) {
                // To avoid spamming warnings if they leave it open, we only warn if we haven't just warned
                handleViolation('devtoolsAttempts', 'Developer tools appear to be open.');
            }
        };

        // Check every 3 seconds
        const interval = setInterval(checkDevTools, 3000);
        return () => clearInterval(interval);
    }, [isExamActive, handleViolation]);

    // 10. BeforeUnload Warning
    useEffect(() => {
        if (!isExamActive) return;

        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isExamActiveRef.current && !isSubmittingRef.current) {
                e.preventDefault();
                e.returnValue = ''; // Standard way to trigger prompt in modern browsers
                return '';
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [isExamActive]);

    // Helper to dismiss the warning modal
    const clearWarning = useCallback(() => {
        if (!isSubmittingRef.current) {
            setWarningMessage(null);
            enterFullscreen();
        }
    }, [enterFullscreen]);

    return {
        warningMessage,
        clearWarning,
        isFullscreen,
        enterFullscreen,
        securityLog: logRef.current
    };
}
