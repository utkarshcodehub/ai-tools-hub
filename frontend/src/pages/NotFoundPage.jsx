import { Link } from 'react-router-dom'
import SEOHead from '../components/SEOHead'

export default function NotFoundPage() {
  return (
    <>
      <SEOHead title="Page not found" />
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-4 px-4 text-center">
        <p className="text-6xl font-semibold text-gray-200">404</p>
        <h1 className="text-xl font-semibold text-gray-900">Page not found</h1>
        <p className="text-sm text-gray-500 max-w-xs">
          The page you're looking for doesn't exist or the tool ID is wrong.
        </p>
        <div className="flex gap-3 mt-2">
          <Link
            to="/"
            className="text-sm bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            Go home
          </Link>
          <Link
            to="/directory"
            className="text-sm border border-gray-200 text-gray-600 px-4 py-2 rounded-lg
                       hover:border-gray-300 transition-colors"
          >
            Browse directory
          </Link>
        </div>
      </div>
    </>
  )
}