import { useState, useRef, useEffect } from 'react'
import { ArrowRight, Plus } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  placeholder?: string
  disabled?: boolean
  isLoading?: boolean
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  onKeyDown,
  placeholder = "Continue the conversation...",
  disabled = false,
  isLoading = false
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
    
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
    onKeyDown?.(e)
  }

  useEffect(() => {
    if (!value && textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value])

  return (
    <div className="flex items-end space-x-3 px-4 py-2.5 bg-white border-2 border-gray-300 rounded-2xl shadow-lg hover:border-gray-400 hover:shadow-xl focus-within:border-gray-900 focus-within:shadow-2xl transition-all duration-300 ease-out">
      <button
        type="button"
        className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors duration-200 flex items-center justify-center"
        disabled={disabled}
      >
        <Plus className="w-4 h-4 text-gray-600" />
      </button>
      
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 bg-transparent text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-0 focus:border-none text-base font-normal resize-none leading-6 py-1"
        style={{
          outline: 'none',
          boxShadow: 'none',
          border: 'none',
          minHeight: '24px',
          maxHeight: '150px'
        }}
      />
      
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-200 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center shadow-md hover:scale-110 active:scale-95 mb-1"
      >
        {isLoading ? (
          <div className="w-3 h-3 border-2 border-gray-400/30 border-t-gray-600 rounded-full animate-spin" />
        ) : (
          <ArrowRight className="w-4 h-4 text-black" />
        )}
      </button>
    </div>
  )
}