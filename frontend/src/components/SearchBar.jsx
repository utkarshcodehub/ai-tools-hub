import { useState } from 'react'

export default function SearchBar({ onSearch, placeholder = 'Search tools or describe a task...' }) {
  const [value, setValue] = useState('')

  const handleChange = (e) => {
    setValue(e.target.value)
    onSearch(e.target.value)
  }

  const handleClear = () => {
    setValue('')
    onSearch('')
  }

  return (
    <div className="relative w-full">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full pl-9 pr-9 py-2.5 text-sm border border-gray-200 rounded-xl
                   bg-white focus:outline-none focus:ring-2 focus:ring-blue-500
                   focus:border-transparent transition-all"
      />
      {value && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400
                     hover:text-gray-600 transition-colors"
        >
          ✕
        </button>
      )}
    </div>
  )
}