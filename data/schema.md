# Tool Data Schema

Each entry in tools.json follows this structure:

| Field                        | Type       | Description                            |
|------------------------------|------------|----------------------------------------|
| id                           | string     | kebab-case unique ID e.g. "groq-api"   |
| name                         | string     | Display name e.g. "Groq"               |
| tagline                      | string     | One-line description (max 80 chars)    |
| website                      | string     | Homepage URL                           |
| logo_url                     | string     | Logo image URL (use clearbit or direct)|
| categories                   | string[]   | From the fixed category list below     |
| tags                         | string[]   | Freeform: "open-source","trending" etc |
| pricing.has_free_tier        | boolean    | Is there a usable free tier right now? |
| pricing.free_details         | string     | What the free tier includes            |
| pricing.paid_starts_at       | string     | e.g. "$20/mo" or "Free only"           |
| pricing.pricing_url          | string     | Direct link to pricing page            |
| api.available                | boolean    | Is a public API available?             |
| api.docs_url                 | string     | API documentation URL                  |
| api.key_url                  | string     | Where to get an API key                |
| api.base_url                 | string     | e.g. "https://api.openai.com/v1"       |
| api.rate_limits              | string     | e.g. "3 RPM on free tier"              |
| api.env_var_name             | string     | e.g. "OPENAI_API_KEY"                  |
| api.auth_method              | string     | "Bearer" / "x-api-key" / "Basic"       |
| free_alternatives            | string[]   | IDs of cheaper/free alternatives       |
| status                       | string     | "active" / "beta" / "deprecated"       |
| free_tier_verified_date      | string     | "YYYY-MM-DD" — when we last checked    |

## Fixed Category List
llm | code | image | video | audio | search | agents | embeddings | speech | productivity