import { useParams, Link } from "react-router-dom";
import { fetchTool, fetchAlternatives } from "../api/client";
import { useFetch } from "../hooks/useTools";
import ApiPanel from "../components/ApiPanel";
import FreeAltCard from "../components/FreeAltCard";
import { ToolCardSkeleton } from "../components/LoadingSkeleton";

export default function ToolDetailPage() {
  const { id } = useParams();
  const { data: tool, loading, error } = useFetch(() => fetchTool(id), [id]);
  const { data: alternatives } = useFetch(
    () => (tool ? fetchAlternatives(id) : Promise.resolve([])),
    [tool],
  );

  if (loading)
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <ToolCardSkeleton />
      </div>
    );

  if (error || !tool)
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center text-gray-400">
        <p className="text-lg">Tool not found</p>
        <Link to="/" className="text-blue-600 text-sm mt-2 inline-block">
          ← Back to home
        </Link>
      </div>
    );

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
      <Link
        to="/directory"
        className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
      >
        ← Back to directory
      </Link>

      <div className="flex items-start gap-4">
        <img
          src={tool.logo_url}
          alt={tool.name}
          className="w-16 h-16 rounded-xl border border-gray-200 bg-gray-50 object-contain"
          onError={(e) => {
            e.target.src = `https://ui-avatars.com/api/?name=${tool.name}&background=f3f4f6&color=374151&bold=true&size=64`;
          }}
        />
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-semibold text-gray-900">
              {tool.name}
            </h1>
            {tool.pricing.has_free_tier && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                Free tier
              </span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium
              ${tool.status === "active" ? "bg-gray-100 text-gray-600" : "bg-red-100 text-red-600"}`}
            >
              {tool.status}
            </span>
          </div>
          <p className="text-gray-500 text-sm mt-1">{tool.tagline}</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {tool.categories.map((cat) => (
              <span
                key={cat}
                className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full"
              >
                {cat}
              </span>
            ))}
            {tool.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Pricing</h3>
          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-400">Free tier</span>
              <span
                className={
                  tool.pricing.has_free_tier
                    ? "text-green-600 font-medium"
                    : "text-red-500"
                }
              >
                {tool.pricing.has_free_tier ? "Yes" : "No"}
              </span>
            </div>
            {tool.pricing.has_free_tier && (
              <div className="flex justify-between gap-2">
                <span className="text-gray-400 shrink-0">Includes</span>
                <span className="text-gray-700 text-right">
                  {tool.pricing.free_details}
                </span>
              </div>
            )}
            <div className="flex justify-between gap-2">
              <span className="text-gray-400 shrink-0">Paid from</span>
              <span className="text-gray-700 text-right">
                {tool.pricing.paid_starts_at}
              </span>
            </div>
          </div>
          <a
            href={tool.pricing.pricing_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-blue-600 hover:underline mt-1"
          >
            View full pricing ↗
          </a>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-gray-900">Links</h3>
          <div className="flex flex-col gap-2">
            <a
              href={tool.website}
              target="_blank"
              rel="noreferrer"
              className="text-xs bg-gray-900 text-white px-3 py-2 rounded-lg text-center
                         font-medium hover:bg-gray-700 transition-colors"
            >
              Visit website ↗
            </a>
            {tool.api.available && (
              <a
                href={tool.api.docs_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs bg-blue-50 text-blue-700 px-3 py-2 rounded-lg text-center
                           font-medium hover:bg-blue-100 transition-colors"
              >
                API documentation ↗
              </a>
            )}
          </div>
        </div>
      </div>

      <ApiPanel tool={tool} />

      {alternatives?.length > 0 && !tool.pricing.has_free_tier && (
        <FreeAltCard original={tool} alternatives={alternatives} />
      )}

      <p className="text-xs text-gray-400 text-center">
        Free tier last verified: {tool.free_tier_verified_date}
      </p>
    </div>
  );
}
