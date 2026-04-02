import { useState } from "react";
import { fetchEnvTemplate } from "../api/client";

export default function ApiPanel({ tool }) {
  const [copied, setCopied] = useState(false);
  const [envText, setEnvText] = useState(null);
  const [loadingEnv, setLoadingEnv] = useState(false);

  if (!tool.api.available) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
        <p className="text-sm text-gray-500">
          No public API available for this tool.
        </p>
      </div>
    );
  }

  const handleCopyKey = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEnvTemplate = async () => {
    setLoadingEnv(true);
    try {
      const res = await fetchEnvTemplate([tool.id]);
      setEnvText(res.template);
    } catch {
      setEnvText("# Error generating template");
    } finally {
      setLoadingEnv(false);
    }
  };

  const rows = [
    { label: "Base URL", value: tool.api.base_url },
    { label: "Auth method", value: tool.api.auth_method },
    { label: "Rate limits", value: tool.api.rate_limits },
    { label: "Env var name", value: tool.api.env_var_name },
  ].filter((r) => r.value);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 text-sm">API reference</h3>
        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
          API available
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-start justify-between gap-4"
          >
            <span className="text-xs text-gray-400 shrink-0 pt-0.5 w-24">
              {row.label}
            </span>
            <span className="text-xs text-gray-800 font-mono text-right break-all">
              {row.value}
            </span>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 pt-1 border-t border-gray-100">
        <a
          href={tool.api.docs_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5
                     rounded-lg font-medium transition-colors"
        >
          View docs ↗
        </a>
        <a
          href={tool.api.key_url}
          target="_blank"
          rel="noreferrer"
          className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5
                     rounded-lg font-medium transition-colors"
        >
          Get API key ↗
        </a>
        <button
          onClick={handleEnvTemplate}
          disabled={loadingEnv}
          className="text-xs bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5
                     rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {loadingEnv ? "Generating…" : ".env template"}
        </button>
      </div>

      {envText && (
        <div className="relative">
          <pre
            className="bg-gray-950 text-green-400 text-xs rounded-lg p-3 overflow-x-auto
                          font-mono leading-relaxed whitespace-pre-wrap"
          >
            {envText}
          </pre>
          <button
            onClick={() => handleCopyKey(envText)}
            className="absolute top-2 right-2 text-xs bg-gray-800 hover:bg-gray-700
                       text-gray-300 px-2 py-1 rounded transition-colors"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      )}
    </div>
  );
}
