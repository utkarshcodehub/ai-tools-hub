import { useState, useMemo } from 'react'
import Fuse from 'fuse.js'
import { fetchTools, fetchCategories } from '../api/client'
import { useFetch } from '../hooks/useTools'
import SearchBar from '../components/SearchBar'
import ToolCard from '../components/ToolCard'
import CategoryFilter from '../components/CategoryFilter'
import { SkeletonGrid } from '../components/LoadingSkeleton'

export default function DirectoryPage() {
  const { data: allTools, loading } = useFetch(fetchTools, [])
  const { data: categories } = useFetch(fetchCategories, [])

  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [freeOnly, setFreeOnly] = useState(false)
  const [apiOnly, setApiOnly] = useState(false)

  const fuse = useMemo(() => {
    if (!allTools) return null
    return new Fuse(allTools, {
      keys: ['name', 'tagline', 'categories', 'tags'],
      threshold: 0.35,
    })
  }, [allTools])

  const displayed = useMemo(() => {
    if (!allTools) return []
    let results = query && fuse
      ? fuse.search(query).map(r => r.item)
      : allTools
    if (selectedCategory) results = results.filter(t => t.categories.includes(selectedCategory))
    if (freeOnly) results = results.filter(t => t.pricing.has_free_tier)
    if (apiOnly) results = results.filter(t => t.api.available)
    return results
  }, [allTools, query, selectedCategory, freeOnly, apiOnly, fuse])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-6">

      <div>
        <h1 className="text-2xl font-semibold text-gray-900 mb-1">Tool directory</h1>
        <p className="text-sm text-gray-500">Browse and filter all {allTools?.length || 0} tools</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <SearchBar onSearch={setQuery} placeholder="Search by name, task, or tag..." />
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setFreeOnly(v => !v)}
            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors
              ${freeOnly
                ? 'bg-green-600 text-white border-green-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
              }`}
          >
            Free tier only
          </button>
          <button
            onClick={() => setApiOnly(v => !v)}
            className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors
              ${apiOnly
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
              }`}
          >
            Has API
          </button>
        </div>
      </div>

      {categories && (
        <CategoryFilter
          categories={categories}
          selected={selectedCategory}
          onSelect={setSelectedCategory}
        />
      )}

      <div className="text-xs text-gray-400">
        {displayed.length} tool{displayed.length !== 1 ? 's' : ''} shown
      </div>

      {loading ? (
        <SkeletonGrid count={12} />
      ) : displayed.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {displayed.map(tool => <ToolCard key={tool.id} tool={tool} />)}
        </div>
      ) : (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">No tools match your filters</p>
          <p className="text-sm mt-1">Try removing a filter or changing your search</p>
        </div>
      )}

    </div>
  )
}