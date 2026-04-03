export default function ErrorMessage({ message = 'Failed to load data.', onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
      <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
        <span className="text-red-400 text-lg font-bold">!</span>
      </div>
      <p className="text-sm text-gray-500 max-w-xs">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5
                     rounded-lg transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  )
}