import { useEffect, useRef } from 'react';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  focusTrigger?: number;
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search...',
  className = '',
  focusTrigger,
}: SearchInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (focusTrigger) inputRef.current?.focus();
  }, [focusTrigger]);

  return (
    <input
      ref={inputRef}
      type="text"
      className={className}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
