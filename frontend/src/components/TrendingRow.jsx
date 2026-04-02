import { Link } from 'react-router-dom'

export default function TrendingRow({ tools }) {
  if (!tools?.length) return null

  return (
    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
      {tools.map(tool => (
        <Link
          key={tool.id}
          to={`/tool/${tool.id}`}
          className="flex items-center gap-2.5 bg-white border border-gray-200 rounded-xl
                     px-3 py-2.5 shrink-0 hover:border-gray-300 hover:shadow-sm
                     transition-all duration-150 min-w-[160px]"
        >
          <img
            src={tool.logo_url}
            alt={tool.name}
            className="w-8 h-8 rounded-md object-contain border border-gray-100 bg-gray-50"
            onError={e => {
              e.target.src = `https://ui-avatars.com/api/?name=${tool.name}&background=f3f4f6&color=374151&bold=true`
            }}
          />
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{tool.name}</p>
            <p className="text-xs text-gray-400 truncate">{tool.categories[0]}</p>
          </div>
        </Link>
      ))}
    </div>
  )
}