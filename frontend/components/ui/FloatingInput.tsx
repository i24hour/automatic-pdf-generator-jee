"use client";

import { useState } from "react";

interface FloatingInputProps {
    type?: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
    required?: boolean;
    autoComplete?: string;
}

export function FloatingInput({
    type = "text",
    label,
    value,
    onChange,
    required = false,
    autoComplete,
}: FloatingInputProps) {
    const [isFocused, setIsFocused] = useState(false);

    const isActive = isFocused || value.length > 0;

    return (
        <div className="relative">
            <input
                type={type}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                required={required}
                autoComplete="off"
                data-lpignore="true"
                data-form-type="other"
                className={`
          w-full px-4 py-4 bg-white rounded-lg text-gray-900 text-base
          border transition-all duration-200 outline-none
          ${isFocused
                        ? "border-indigo-600 ring-2 ring-indigo-100"
                        : "border-gray-300 hover:border-gray-400"
                    }
        `}
            />
            <label
                className={`
          absolute left-4 pointer-events-none transition-all duration-200 ease-out
          ${isActive
                        ? "-top-2.5 text-xs px-1 bg-white"
                        : "top-4 text-base"
                    }
          ${isFocused ? "text-indigo-600" : "text-gray-500"}
        `}
            >
                {label}
            </label>
        </div>
    );
}
