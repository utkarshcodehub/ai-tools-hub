import { Link } from 'react-router-dom'

export default function FreeAltCard({ original, alternatives }) {
  if (!alternatives?.length) return null

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
      <p className="text-xs font-semibold text-amber-800 mb-3">
        Free alternatives to {original.name}
      </p>
      <div className="flex flex-col gap-2">
        {alternatives.map(alt => (
          <Link
            key={alt.id}
            to={`/tool/${alt.id}`}
            className="flex items-center gap-3 bg-white border border-amber-100
                       rounded-lg px-3 py-2.5 hover:border-amber-300 transition-colors"
          >
            <img
              src={alt.logo_url}
              alt={alt.name}
              className="w-7 h-7 rounded-md object-contain border border-gray-100 bg-gray-50"
              onError={e => {
                e.target.src = `https://ui-avatars.com/api/?name=${alt.name}&background=f3f4f6&color=374151&bold=true`
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">{alt.name}</p>
              <p className="text-xs text-gray-500 truncate">{alt.tagline}</p>
            </div>
            {alt.pricing.has_free_tier && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full shrink-0">
                Free
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}