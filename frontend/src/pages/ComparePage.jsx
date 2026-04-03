import { useState, useMemo } from "react";
import { fetchTools } from "../api/client";
import { useFetch } from "../hooks/useTools";
import { Link } from "react-router-dom";
import SEOHead from "../components/SEOHead";

export default function ComparePage() {
  const { data: allTools, loading } = useFetch(fetchTools, []);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState([]);

  const paidTools = useMemo(
    () => allTools?.filter((t) => !t.pricing.has_free_tier) || [],
    [allTools],
  );

  const filtered = useMemo(() => {
    if (!allTools) return [];
    if (!search) return paidTools;
    const q = search.toLowerCase();
    return paidTools.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.categories.some((c) => c.includes(q)),
    );
  }, [paidTools, search]);

  const toggleSelect = (tool) => {
    setSelected((prev) =>
      prev.find((t) => t.id === tool.id)
        ? prev.filter((t) => t.id !== tool.id)
        : prev.length < 3
          ? [...prev, tool]
          : prev,
    );
  };

  const getAlternatives = (tool) =>
    allTools?.filter((t) => tool.free_alternatives.includes(t.id)) || [];

  if (loading)
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-6" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-20 bg-gray-100 rounded-xl animate-pulse"
            />
          ))}
        </div>
      </div>
    );

  return (
    <>
      <SEOHead
        title="Paid vs free AI tools"
        description="Find free alternatives for paid AI tools. Compare pricing, features, and API availability side by side."
        path="/compare"
      />
      <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 mb-1">
            Paid vs free
          </h1>
          <p className="text-sm text-gray-500">
            Find free alternatives for paid tools. Select up to 3 tools to
            compare.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter paid tools..."
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-xl
                       bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              className="text-sm text-gray-500 hover:text-gray-700 px-3 py-2 border
                       border-gray-200 rounded-xl transition-colors"
            >
              Clear selection
            </button>
          )}
        </div>

        <div>
          <p className="text-xs text-gray-400 mb-3">
            {filtered.length} paid tool{filtered.length !== 1 ? "s" : ""} —
            click to select
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {filtered.map((tool) => {
              const isSelected = selected.find((t) => t.id === tool.id);
              return (
                <button
                  key={tool.id}
                  onClick={() => toggleSelect(tool)}
                  className={`flex items-center gap-2.5 p-3 rounded-xl border text-left
                            transition-all duration-150
                            ${
                              isSelected
                                ? "border-blue-500 bg-blue-50 ring-1 ring-blue-400"
                                : "border-gray-200 bg-white hover:border-gray-300"
                            }`}
                >
                  <img
                    src={tool.logo_url}
                    alt={tool.name}
                    className="w-8 h-8 rounded-md object-contain border border-gray-100 bg-gray-50 shrink-0"
                    onError={(e) => {
                      e.target.src = `https://ui-avatars.com/api/?name=${tool.name}&background=f3f4f6&color=374151`;
                    }}
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {tool.name}
                    </p>
                    <p className="text-xs text-red-500">
                      {tool.pricing.paid_starts_at}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {selected.length > 0 && (
          <div className="flex flex-col gap-5">
            <h2 className="text-sm font-semibold text-gray-800">
              Free alternatives
            </h2>
            {selected.map((tool) => {
              const alts = getAlternatives(tool);
              return (
                <div
                  key={tool.id}
                  className="bg-white border border-gray-200 rounded-xl p-5"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <img
                      src={tool.logo_url}
                      alt={tool.name}
                      className="w-10 h-10 rounded-lg border border-gray-100 bg-gray-50 object-contain"
                      onError={(e) => {
                        e.target.src = `https://ui-avatars.com/api/?name=${tool.name}&background=f3f4f6&color=374151`;
                      }}
                    />
                    <div>
                      <p className="font-medium text-gray-900">{tool.name}</p>
                      <p className="text-xs text-gray-400">
                        Starting at {tool.pricing.paid_starts_at}
                      </p>
                    </div>
                  </div>

                  {alts.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {alts.map((alt) => (
                        <Link
                          key={alt.id}
                          to={`/tool/${alt.id}`}
                          className="flex items-center gap-3 border border-green-200 bg-green-50
                                   rounded-lg px-3 py-2.5 hover:border-green-300 transition-colors"
                        >
                          <img
                            src={alt.logo_url}
                            alt={alt.name}
                            className="w-8 h-8 rounded-md border border-gray-100 bg-white object-contain shrink-0"
                            onError={(e) => {
                              e.target.src = `https://ui-avatars.com/api/?name=${alt.name}&background=f3f4f6&color=374151`;
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900">
                              {alt.name}
                            </p>
                            <p className="text-xs text-gray-500 truncate">
                              {alt.tagline}
                            </p>
                          </div>
                          <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full shrink-0">
                            Free
                          </span>
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400">
                      No mapped free alternatives yet.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
