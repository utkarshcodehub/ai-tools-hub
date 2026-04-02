import { Link } from 'react-router-dom'

const CATEGORY_COLORS = {
  llm:          'bg-purple-100 text-purple-800',
  code:         'bg-blue-100 text-blue-800',
  image:        'bg-pink-100 text-pink-800',
  video:        'bg-orange-100 text-orange-800',
  audio:        'bg-amber-100 text-amber-800',
  search:       'bg-teal-100 text-teal-800',
  agents:       'bg-green-100 text-green-800',
  embeddings:   'bg-indigo-100 text-indigo-800',
  speech:       'bg-cyan-100 text-cyan-800',
  productivity: 'bg-gray-100 text-gray-700',
}

export default function ToolCard({ tool }) {
  const primaryCategory = tool.categories[0]
  const categoryColor = CATEGORY_COLORS[primaryCategory] || 'bg-gray-100 text-gray-700'

  return (
    <Link
      to={`/tool/${tool.id}`}
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3
                 hover:border-gray-300 hover:shadow-sm transition-all duration-150 group"
    >
      <div className="flex items-start gap-3">
        <img
          src={tool.logo_url}
          alt={tool.name}
          className="w-10 h-10 rounded-lg object-contain border border-gray-100 bg-gray-50"
          onError={e => {
            e.target.src = `https://ui-avatars.com/api/?name=${tool.name}&background=f3f4f6&color=374151&bold=true`
          }}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-gray-900 group-hover:text-blue-600 transition-colors truncate">
              {tool.name}
            </span>
            {tool.pricing.has_free_tier && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium shrink-0">
                Free
              </span>
            )}
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium mt-0.5 inline-block ${categoryColor}`}>
            {primaryCategory}
          </span>
        </div>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
        {tool.tagline}
      </p>

      <div className="flex flex-wrap gap-1.5 mt-auto">
        {tool.api.available && (
          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
            API
          </span>
        )}
        {tool.tags.slice(0, 2).map(tag => (
          <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  )
}