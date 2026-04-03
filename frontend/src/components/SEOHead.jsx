import { Helmet } from 'react-helmet-async'

const DEFAULT_DESC =
  'An unbiased, searchable directory of AI tools — with free tier status, API key reference, and paid vs free comparisons.'

export default function SEOHead({ title, description, path = '' }) {
  const fullTitle = title ? `${title} — AI Tools Hub` : 'AI Tools Hub'
  const desc = description || DEFAULT_DESC
  const canonical = `https://ai-tools-hub.vercel.app${path}`

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      <link rel="canonical" href={canonical} />

      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:type" content="website" />
      <meta property="og:url" content={canonical} />

      <meta name="twitter:card" content="summary" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={desc} />

      <meta name="robots" content="index, follow" />
    </Helmet>
  )
}