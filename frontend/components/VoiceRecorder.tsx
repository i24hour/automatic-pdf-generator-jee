import { useState, useRef, useEffect } from 'react';
import { Mic, Square, Trash2, Play, Pause } from 'lucide-react';

interface VoiceRecorderProps {
    onRecordingComplete: (file: File) => void;
    onDelete: () => void;
}

export default function VoiceRecorder({ onRecordingComplete, onDelete }: VoiceRecorderProps) {
    const [isRecording, setIsRecording] = useState(false);
    const [audioURL, setAudioURL] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [timer, setTimer] = useState(0);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
            if (audioURL) URL.revokeObjectURL(audioURL);
        };
    }, []);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' }); // or webm
                const url = URL.createObjectURL(audioBlob);
                setAudioURL(url);

                // Create File object
                const file = new File([audioBlob], "voice_note.wav", { type: "audio/wav" });
                onRecordingComplete(file);

                // Stop tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);

            // Start Timer
            setTimer(0);
            timerRef.current = setInterval(() => {
                setTimer(prev => prev + 1);
            }, 1000);

        } catch (err) {
            console.error("Error accessing microphone:", err);
            alert("Could not access microphone. Please allow permissions.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
            if (timerRef.current) clearInterval(timerRef.current);
        }
    };

    const handleDelete = () => {
        setAudioURL(null);
        setTimer(0);
        onDelete();
    };

    // Format timer
    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    };

    return (
        <div className="flex items-center gap-4 p-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50">
            {!audioURL ? (
                <>
                    <button
                        type="button"
                        onClick={isRecording ? stopRecording : startRecording}
                        className={`p-3 rounded-full transition-all ${isRecording
                                ? 'bg-red-100 text-red-600 animate-pulse'
                                : 'bg-indigo-100 text-indigo-600 hover:bg-indigo-200'
                            }`}
                    >
                        {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
                    </button>

                    <div className="flex-1">
                        <p className={`text-sm font-medium ${isRecording ? 'text-red-500' : 'text-gray-500'}`}>
                            {isRecording ? `Recording... ${formatTime(timer)}` : 'Click to record voice note'}
                        </p>
                    </div>
                </>
            ) : (
                <>
                    <div className="p-3 bg-green-100 text-green-600 rounded-full">
                        <Play className="w-5 h-5 fill-current" />
                    </div>
                    <div className="flex-1">
                        <audio src={audioURL} controls className="h-8 w-full max-w-[200px]" />
                        <p className="text-xs text-gray-400 mt-1">Voice note recorded ({formatTime(timer)})</p>
                    </div>
                    <button
                        type="button"
                        onClick={handleDelete}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                        <Trash2 className="w-5 h-5" />
                    </button>
                </>
            )}
        </div>
    );
}
