import { useState, useEffect, useMemo } from 'react'
import Fuse from 'fuse.js'
import { fetchTools, fetchTrending, fetchCategories } from '../api/client'
import { useFetch } from '../hooks/useTools'
import SearchBar from '../components/SearchBar'
import TrendingRow from '../components/TrendingRow'
import ToolCard from '../components/ToolCard'
import CategoryFilter from '../components/CategoryFilter'
import { SkeletonGrid } from '../components/LoadingSkeleton'

export default function HomePage() {
  const { data: allTools, loading: toolsLoading } = useFetch(fetchTools, [])
  const { data: trending, loading: trendLoading } = useFetch(fetchTrending, [])
  const { data: categories } = useFetch(fetchCategories, [])

  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)

  const fuse = useMemo(() => {
    if (!allTools) return null
    return new Fuse(allTools, {
      keys: ['name', 'tagline', 'categories', 'tags'],
      threshold: 0.35,
      includeScore: true,
    })
  }, [allTools])

  const displayed = useMemo(() => {
    if (!allTools) return []
    let results = query && fuse
      ? fuse.search(query).map(r => r.item)
      : allTools
    if (selectedCategory) {
      results = results.filter(t => t.categories.includes(selectedCategory))
    }
    return results
  }, [allTools, query, selectedCategory, fuse])

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-10">

      <section className="text-center flex flex-col items-center gap-4 pt-4">
        <h1 className="text-3xl font-semibold text-gray-900 leading-tight">
          Find the right AI tool <br className="hidden sm:block" />
          for any task
        </h1>
        <p className="text-gray-500 text-sm max-w-md">
          An unbiased, searchable directory of AI tools — with free tier status,
          API reference, and paid vs free comparisons.
        </p>
        <div className="w-full max-w-xl">
          <SearchBar onSearch={setQuery} />
        </div>
      </section>

      {!query && (
        <section>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Trending right now</h2>
          {trendLoading
            ? <div className="h-16 bg-gray-100 rounded-xl animate-pulse" />
            : <TrendingRow tools={trending} />
          }
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-sm font-semibold text-gray-700">
            {query ? `Results for "${query}"` : 'All tools'}
            {displayed.length > 0 && (
              <span className="ml-2 text-gray-400 font-normal">({displayed.length})</span>
            )}
          </h2>
        </div>

        {categories && (
          <div className="mb-4">
            <CategoryFilter
              categories={categories}
              selected={selectedCategory}
              onSelect={setSelectedCategory}
            />
          </div>
        )}

        {toolsLoading ? (
          <SkeletonGrid count={8} />
        ) : displayed.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {displayed.map(tool => <ToolCard key={tool.id} tool={tool} />)}
          </div>
        ) : (
          <div className="text-center py-16 text-gray-400">
            <p className="text-lg">No tools found for "{query}"</p>
            <p className="text-sm mt-1">Try a different keyword or browse by category</p>
          </div>
        )}
      </section>

    </div>
  )
}