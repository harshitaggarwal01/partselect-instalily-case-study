# System Detail — PartSelect Support Assistant

Everything about how this project is structured, what each file does, and how the features work. Written as a reference for anyone reading the code or picking it up after me.

---

## Table of Contents

1. [High-level architecture](#1-high-level-architecture)
2. [Request lifecycle](#2-request-lifecycle)
3. [Backend — API layer](#3-backend--api-layer)
4. [Backend — Services](#4-backend--services)
5. [Backend — LLM client](#5-backend--llm-client)
6. [Backend — Tools](#6-backend--tools)
7. [Backend — Models / Schemas](#7-backend--models--schemas)
8. [Backend — Data files](#8-backend--data-files)
9. [Backend — Scripts](#9-backend--scripts)
10. [Frontend — Pages & routing](#10-frontend--pages--routing)
11. [Frontend — Components](#11-frontend--components)
12. [Frontend — Lib (clients, types)](#12-frontend--lib-clients-types)
13. [Features in depth](#13-features-in-depth)

---

## 1. High-level architecture

```
Browser (Next.js, localhost:3000)
  │
  │  HTTP  (Authorization: Bearer <token>)
  ▼
FastAPI (localhost:8000)
  ├── /api/auth       ← login, signup
  ├── /api/threads    ← list, create, load thread history
  ├── /api/cart       ← add/remove/checkout
  └── /api/chat       ← main agent endpoint
        │
        ▼
    run_agent()
        ├── ThreadStore          (threads.json)
        ├── classify_intent_and_flags()   (Haiku — 1 call, returns intent + followup + clarification flags)
        ├── response cache       (in-memory FIFO, 100 entries)
        │
        ├── InstallAgent         → vector search + rerank → Claude Sonnet
        ├── CompatibilityAgent   → compatibility.json lookup → Claude Sonnet
        ├── ProductInfoAgent     → products.json / live scrape → Claude Sonnet
        └── TroubleshootingAgent → vector search + rerank → Claude Sonnet
```

The backend is **stateless between restarts** only in the sense that JSON files are the persistence layer. `ThreadStore`, `CartStore`, and the user cache are all loaded from disk at startup and written back on every mutation.

---

## 2. Request lifecycle

A typical `/api/chat` request follows this path:

1. **Middleware (frontend)** — `middleware.ts` checks `auth_token` cookie before the page even loads.
2. **ChatWindow** — user types a message; `sendChat()` posts to `/api/chat` with `{messages, thread_id, session_id}` and `Authorization: Bearer <token>`.
3. **`chat_endpoint`** — extracts user from the token (`get_current_user`), returns 401 if missing, calls `run_agent(body, user_id)`.
4. **`run_agent`**:
   - Resolves `thread_id` (creates a new thread if none provided).
   - Loads history from session RAM cache → falls back to `thread_store.get_recent_messages`.
   - If `len(history) > 20`, summarises oldest 10 messages with Haiku, replaces them in thread store.
   - Calls `_classify_intent_and_flags` — keyword fast-path first, single Haiku call for anything ambiguous.
   - Checks the response cache (keyed by intent + normalised message + appliance type).
   - Routes to the appropriate agent (or answers directly for follow-ups and clarifications).
   - Sets `thread_id` on the response, appends messages to thread store, updates session cache.
   - Auto-titles the thread from the first user message.
5. **Response** — Pydantic discriminated union (`InstallResponse | CompatibilityResponse | TroubleshootingResponse | ProductInfoResponse`) serialised to JSON, with `thread_id` field.
6. **Frontend** — `ChatWindow` receives response, renders the appropriate widget, notifies `SupportPage` of the thread ID so the sidebar refreshes.

---

## 3. Backend — API layer

### `app/main.py`
Entry point. Creates the FastAPI app, registers CORS middleware (origins from `ALLOWED_ORIGINS` env var), and mounts all routers. Uses a `lifespan` async context manager to load `users.json` into the in-memory user cache at startup.

Routers mounted:
| Prefix | Router |
|--------|--------|
| `/api` | `chat_router`, `health_router` |
| `/api/auth` | `auth_router` |
| `/api/threads` | `threads_router` |
| `/api/cart` | `cart_router` |

### `app/api/health.py`
Single endpoint: `GET /api/health` → `{"status": "ok"}`. Used to verify the server is up.

### `app/api/auth.py`
Handles user authentication.

**`POST /api/auth/login`** — looks up user by username, compares plaintext password (demo only), issues a signed token. Returns 401 on mismatch.

**`POST /api/auth/signup`** — rejects duplicate usernames (400), creates a new user with a `user_{8hex}` id, adds to in-memory cache and appends to `users.json`, returns token.

### `app/api/chat.py`
The main agent endpoint. Extracts the authenticated user from the `Authorization` header, raises 401 if missing, calls `run_agent(body, user_id=user.id)`, logs latency and intent. Catches `ExternalAPIError` (Claude API failures) and returns a graceful troubleshooting response.

### `app/api/threads.py`
All routes require a valid auth token.

| Endpoint | Behaviour |
|----------|-----------|
| `GET /api/threads` | All threads for current user, sorted by last update |
| `POST /api/threads` | Create thread; body `{title?: string}` |
| `GET /api/threads/{id}` | Thread metadata + last 20 messages |

### `app/api/cart.py`
All routes require auth.

| Endpoint | Behaviour |
|----------|-----------|
| `GET /api/cart` | Current user's cart |
| `POST /api/cart/items` | Add item by `part_number`; looks up product data automatically |
| `DELETE /api/cart/items/{pn}` | Remove item |
| `POST /api/cart/clear` | Empty cart |
| `GET /api/cart/checkout-links` | Returns `{links: string[]}` — real PartSelect URLs or search fallbacks |

---

## 4. Backend — Services

### `app/services/agent.py`
The orchestrator. This is the most complex file in the project.

**Session cache** — in-memory dict keyed by `thread_id`, TTL 30 minutes. Stores recent messages so we don't hit `threads.json` on every turn. Thread store is the source of truth; this is just a read cache.

**Response cache** — FIFO dict, max 100 entries. Key: `(intent, normalised_message, appliance_type)`. Only caches deterministic standalone queries (not follow-ups or clarifications). Prevents re-running RAG + LLM for repeated identical questions.

**`_classify_intent_and_flags(user_msg, history_tail, last_response_type)`**
Replaces what was previously two separate LLM calls. Works in layers:
1. Broader part-number regex (`_BROAD_PART_RE`) — catches PS, WP, W-prefixed, letter+digit combos (`DA97-07827A`), 6+ bare digits.
2. Keyword fast-path for install, troubleshoot, compatibility — returns immediately with no API call.
3. Single Haiku call for anything ambiguous — returns `{intent, is_followup, needs_clarification}` as JSON.

**`_answer_followup(history)`** — Haiku call using last 6 turns as context. No retrieval. Returns `ProductInfoResponse` with empty sources.

**`_ask_clarification(user_msg)`** — Haiku call. Prompts for a brief acknowledgment + markdown bullet list of what info is needed (appliance type, symptom, part number).

**`_summarize_messages(messages)`** — Haiku call. Summarises a list of messages into one condensed assistant message for history compression.

**`run_agent(request, user_id)`** — main function. See [§2 Request lifecycle](#2-request-lifecycle) for the full flow.

### `app/services/intent_router.py`
Keyword sets and a legacy `detect_intent()` function (kept for reference; superseded by `_classify_intent_and_flags` in `agent.py` for actual routing). Contains the domain keyword sets (`_DOMAIN`, `_TROUBLESHOOT`, `_COMPAT`, `_INSTALL`) and `_PART_NUMBER_RE` that `agent.py` imports.

Also exposes `classify_intent_llm()` — a standalone few-shot Haiku classifier, still used if something calls `detect_intent()` directly.

### `app/services/thread_store.py`
`ThreadStore` class with `asyncio.Lock` on all write operations.

All data lives in `backend/app/data/threads.json` as `{threads: [...], messages: [...]}`. Messages are flat — each one has a `thread_id` field. Threads are filtered by `user_id`.

Key methods: `create_thread`, `get_recent_messages`, `append_messages`, `update_messages_for_thread` (for summarisation), `update_title`.

Singleton `thread_store` is imported wherever needed.

### `app/services/cart_store.py`
`CartStore` class, same pattern as `ThreadStore`. Stores carts in `carts.json` as `{carts: [{user_id, items: [...]}]}`.

`add_item` increments quantity if the part number already exists. `checkout-links` endpoint builds URLs from stored `item.url` fields, falling back to `search.aspx?SearchTerm=` for parts without direct page URLs.

---

## 5. Backend — LLM client

### `app/llm/claude_client.py`
**The only file that talks to Claude.** Everything else goes through here.

Two model constants:
- `MODEL_FULL = "claude-sonnet-4-5"` — used for full guide generation (install, troubleshoot, compat, product info)
- `MODEL_FAST = "claude-haiku-4-5-20251001"` — used for classification, follow-up detection, clarification, reranking, summarisation

`chat_claude(system, messages, max_tokens, model)` — wraps `anthropic.Anthropic().messages.create()`. Raises `ExternalAPIError` on API failures.

`chat_claude_json(system, messages, schema_description)` — calls `chat_claude` with a JSON-enforcing system prompt, strips markdown code fences, parses JSON. Returns `{"text": raw, "parse_error": True}` if parsing fails.

`DOMAIN_SYSTEM_PROMPT` — the system prompt shared by all agents. Instructs Claude to stay within refrigerator/dishwasher parts scope.

**To swap out Claude**, rewrite `chat_claude` and `chat_claude_json` to call another provider. Nothing else needs to change.

---

## 6. Backend — Tools

### `app/tools/products.py`
Loads `products.json` at startup into an in-memory list.

`get_product(part_number)` — O(n) lookup by part number (n ≤ ~50 products).

`search_products(query?, part_number?)` — fuzzy search by part number or keyword match across name/description.

`lookup_part_live(part_number)` — tries to fetch a part page from PartSelect using `httpx` with browser-like headers. PartSelect's CDN blocks most automated requests, so this frequently returns `None`. The result (including None) is cached in `_live_cache` for the process lifetime to avoid repeated failed requests. When it succeeds, it extracts the name, price, and `azurefd.net` image URL.

### `app/tools/guides.py`
Loads `install_guides.jsonl` and `troubleshooting_guides.jsonl` at startup.

`find_install_guides(part_number?)` — if a part number is given, tries vector search first (`async_similarity_search`), falls back to scanning all guides.

`find_troubleshooting_guides(symptom, appliance_type?)` — vector search with appliance type filter.

Both functions attach a `_source` field to results (`"vector"` or `"fallback"`) for logging.

### `app/tools/compatibility.py`
Loads `compatibility.json` — a dict of `model_number → [list of compatible part numbers]`.

`check_compatibility(model_number, part_number)` → `"compatible" | "not_compatible" | "unknown"`. Pure dict lookup.

### `app/tools/vector_store.py`
Loads `vector_index.json` lazily on first call. Stores all chunk embeddings as a numpy matrix for fast cosine similarity.

`async_similarity_search(query, k=6, appliance_type?, kind?, symptom_keyword?, part_number?)`:
1. Filters candidates by `kind` and `appliance_type`.
2. Embeds the query via `embed_texts`.
3. Computes cosine similarity across filtered candidates.
4. Applies score boosts: `symptom_keyword` match → 1.2×, `part_number` match → 1.3×.
5. Returns top-k by score, without the embedding vectors.

### `app/tools/embeddings.py`
`embed_texts(texts)` — dispatches to the configured provider. Currently only `voyage` is implemented. Calls the Voyage AI REST API directly with `httpx`.

To add another embedding provider: add an `_embed_<provider>()` function and a new branch in `embed_texts`.

### `app/tools/rerank.py`
`rerank_chunks(question, chunks, top_k=3)` — sends chunk snippets (first 150 chars each) to Haiku in a single prompt asking for the top-k most relevant indices as a JSON array. Falls back to original order if the LLM call fails or returns malformed JSON.

---

## 7. Backend — Models / Schemas

### `app/models/schemas.py`
Central Pydantic v2 schemas for the chat API.

`ChatMessage` — `{role: "user" | "assistant" | "system", content: str}`

`ChatRequest` — `{messages: list[ChatMessage], session_id?: str, thread_id?: str}`

`BaseResponse` — `{type: str, text: str, thread_id?: str}` — all response types inherit this.

Response types (discriminated union via `type` field):
- `ProductInfoResponse` — `{products: list[Product]}`
- `InstallResponse` — `{part?: Product, steps: list[InstallStep], sources: list[str], part_image_url?: str}`
- `CompatibilityResponse` — `{part?, model_number?, status: "compatible"|"not_compatible"|"unknown", details?}`
- `TroubleshootingResponse` — `{appliance_type?, issue?, steps: list[TroubleshootStep], sources, part_suggestions: list[Product]}`

`ChatResponse` — annotated union with `discriminator="type"`.

### `app/models/auth.py`
`User`, `UserPublic`, `LoginRequest`, `SignupRequest`, `AuthResponse`.

### `app/models/threads.py`
`Thread` — `{id, user_id, title, created_at, updated_at}`.

### `app/models/cart.py`
`CartItem` — `{part_number, name, url?, image_url?, price?, quantity}`.
`Cart` — `{user_id, items: list[CartItem]}`.

---

## 8. Backend — Data files

All under `backend/app/data/`.

| File | Format | Contents |
|------|--------|----------|
| `products.json` | JSON array | ~7 curated products with part number, name, price, image URL (Azure CDN), PartSelect URL, description |
| `compatibility.json` | JSON object | `{model_number: [part_numbers]}` — which parts fit which models |
| `install_guides.jsonl` | JSONL | One guide per line: `{id, title, url, steps: [{step_number, instruction, caution?}]}` |
| `troubleshooting_guides.jsonl` | JSONL | `{id, symptom, appliance, url, steps: [{step_number, description}]}` |
| `vector_index.json` | JSON array | Generated by `build_index.py`. Each entry: chunk text + embedding + metadata |
| `users.json` | JSON array | Demo users (plaintext passwords — demo only) |
| `threads.json` | JSON object | `{threads: [...], messages: [...]}` |
| `carts.json` | JSON object | `{carts: [{user_id, items: [...]}]}` |
| `rag_eval_queries.json` | JSON array | 8 labelled queries with `expected_guide_ids` for RAG evaluation |

---

## 9. Backend — Scripts

### `scripts/build_index.py`
Offline script — run once to (re)build `vector_index.json`.

Chunking strategy:
- For each guide, produces a **summary chunk** (title/symptom + first 2 step instructions) and **step chunks** (groups of 3 steps).
- Each chunk gets metadata: `appliance_type`, `symptom_keywords` (top 5 non-stopword tokens), `part_numbers` (regex-extracted), `step_range`.

Run with: `PYTHONPATH=. python scripts/build_index.py`

### `scripts/eval_rag.py`
Loads `rag_eval_queries.json`, runs each query through `async_similarity_search(k=6)`, checks top-3 results against `expected_guide_ids`, prints per-query pass/fail and overall `Recall@3`.

### `scripts/update_image_urls.py`
One-time script using Playwright (real browser) to fetch correct product image URLs from PartSelect. PartSelect blocks `httpx`/`requests`, so Playwright is required. Run offline when product image URLs break due to CDN changes.

### `scripts/scrape_partselect.py`
Offline data refresh tool. Takes a list of part numbers, scrapes PartSelect for name/price/image/description, and updates `products.json`. Use when adding new parts to the catalog.

---

## 10. Frontend — Pages & routing

### `middleware.ts`
Runs at the Next.js Edge before every request to `/support/*`. Reads the `auth_token` cookie — redirects to `/login` if missing. This is why `login()` in `AuthContext` sets both localStorage AND a cookie: localStorage is for client-side reads, the cookie is for middleware.

### `app/layout.tsx`
Root layout. Wraps all pages with `<AuthProvider>` (global auth state) and renders `<Header>` above children. Font setup (Geist) is here too.

### `app/page.tsx`
Landing page at `/`. Hero section with "Find Your Part" CTA that links to `/support`. Uses `MessageCircle` and `ArrowRight` from the custom `Icons` component.

### `app/login/page.tsx`
Login form with PartSelect teal/amber styling. On submit: calls `loginUser()`, then `login(user, token)` from AuthContext, then `window.location.href = "/support"` (hard navigation — not `router.push`, which caused a redirect loop with the middleware cookie check).

### `app/signup/page.tsx`
Same structure as login. Adds password confirmation. Calls `signupUser()`.

### `app/support/page.tsx`
The main app page. Three-column desktop layout:
- **Left (w-56)**: `ThreadList` — conversation history sidebar
- **Centre (flex-1)**: amber banner + `ChatWindow`
- **Right (w-64)**: `CartSidebar`

Manages thread state: on mount, fetches threads, selects the last-used thread (from `localStorage.lastThreadId`) or the most recent one. `handleThreadCreated` is called by `ChatWindow` when the backend returns a new `thread_id`, triggering a thread list refresh.

Auth guard: if `user === null` and no `auth_token` in localStorage after a 100 ms debounce, redirects to `/login`.

---

## 11. Frontend — Components

### `components/Header.tsx`
Three-row PartSelect-style header (requires `"use client"` for the logout handler):

- **Row 1 (white)**: Logo with amber "Here to help since 1999" badge; right side shows Start Chat link, Order Status, username + Logout (or Sign In if not logged in), cart icon.
- **Row 2 (teal `#1d6b64`)**: Nav links including Refrigerator Finder and Dishwasher Finder (both open PartSelect category pages in new tabs); search box.
- **Row 3 (gray `#f5f5f5`)**: Trust bar — Price Match, Fast Shipping, OEM Parts, 1 Year Warranty. Hidden on mobile.

Logout clears AuthContext state (which wipes localStorage + cookie) then does a hard redirect to `/login`.

### `components/ThreadList.tsx`
Left sidebar. "+ New Conversation" button (calls `onCreateThread`). Each thread shows title + last updated date. Active thread highlighted with a teal left border.

### `components/CartSidebar.tsx`
Right sidebar. Fetches cart on mount and on `cart-updated` custom DOM events. Shows item list (image, name, part number, price × qty, remove button) and estimated total.

"Checkout on PartSelect" button calls `GET /api/cart/checkout-links`, shows a confirmation modal listing each item, then `window.open(url, "_blank", "noopener,noreferrer")` for each link.

### `components/ChatWindow/ChatWindow.tsx`
The main conversation component. Holds message state. When `currentThreadId` changes (thread switch), clears messages and hydrates from `initialMessages` prop. Sends each message via `sendChat(messages, sessionId, token, currentThreadId)`. Calls `onThreadCreated` when the response contains a new `thread_id`.

### `components/ChatWindow/MessageList.tsx`
Renders the message history. User messages appear right-aligned in blue; assistant messages appear left-aligned in gray. Routes assistant responses to the correct widget by `response.type`. Shows a welcome screen with example prompts when the chat is empty.

### `components/ChatWindow/MessageInput.tsx`
Textarea that auto-resizes, submits on Enter (Shift+Enter for newline), shows a disabled send button while loading.

### `components/InstallWidget.tsx`
Renders `InstallResponse`. Shows the part image (from `part_image_url` or the `part.image_url`) at the top, an intro text paragraph, numbered installation steps (with caution callouts), and source links.

### `components/TroubleshootWidget.tsx`
Renders `TroubleshootingResponse`. Accordion-style steps — each step button shows `step.title` (4-6 word action phrase generated by Claude) rather than a truncated sentence. Expanding reveals the full description. Shows `part_suggestions` chips (small image + part number) at the bottom.

### `components/CompatWidget.tsx`
Renders `CompatibilityResponse`. Shows a coloured status badge (green/red/gray) for compatible/not_compatible/unknown, the part card, and Claude's detailed explanation.

### `components/ProductCard.tsx`
Used in `MessageList` for `product_info` responses. Shows part image, part number, name, price, a "View on PartSelect" link, and (when logged in) a teal "Add to Cart" button. Clicking Add to Cart posts to `/api/cart/items` and dispatches a `cart-updated` event so `CartSidebar` refreshes.

### `components/MarkdownText.tsx`
Lightweight inline markdown renderer — no npm package. Handles:
- `**text**` → `<strong>`
- `*text*` → `<em>`
- `[label](url)` → `<a target="_blank">` with PartSelect blue underline
- `- item` / `* item` / `1. item` → `<ul><li>` list

Used in `MessageList` for all assistant text, so Claude's formatted responses (bold, bullet points, links) render correctly.

### `components/Icons.tsx`
Three custom SVG icon components: `MessageCircle`, `ChevronDown`, `ArrowRight`. Used throughout instead of inline path data.

---

## 12. Frontend — Lib (clients, types)

### `lib/types.ts`
TypeScript interfaces mirroring the backend's Pydantic schemas. `ChatResponse` is a discriminated union on `type`. Also defines `FrontendMessage` (adds `id` and optional `response` to the basic `ChatMessage`), plus `Thread`, `CartItem`, `Cart`.

### `lib/apiClient.ts`
`sendChat(messages, sessionId?, token?, threadId?)` — posts to `/api/chat`. When `sessionId` is set, sends only the last message (backend holds full history in the session cache). Includes `Authorization: Bearer` header when token is present.

Also exports cart helpers: `getCart`, `addToCart`, `removeFromCart`, `getCheckoutLinks`.

### `lib/authClient.ts`
`loginUser(username, password)` and `signupUser(username, password)` — thin wrappers over `fetch` to `/api/auth/login` and `/api/auth/signup`.

### `lib/threadClient.ts`
`listThreads(token)`, `createThread(token, title?)`, `getThreadMessages(token, threadId)` — bearer-authenticated fetches to `/api/threads`.

### `context/AuthContext.tsx`
Global React context providing `{ user, token, login, logout }`. On mount, reads from localStorage. `login()` sets React state + localStorage + a `SameSite=Lax` cookie (for middleware). `logout()` clears all three.

---

## 13. Features in depth

### Intent classification

Every chat message goes through a two-stage classifier:

1. **Keyword fast-path** (zero LLM cost): checks for part number patterns, appliance keywords, troubleshooting verbs, install verbs. Covers ~80% of real queries.
2. **Haiku fallback**: for ambiguous messages, a single Haiku call returns `{intent, is_followup, needs_clarification}` as JSON. This replaces what was previously two separate API calls.

The five intents are: `install`, `compatibility`, `product_info`, `troubleshooting`, `out_of_scope`.

### RAG pipeline

When `InstallAgent` or `TroubleshootingAgent` runs:
1. `find_*_guides()` calls `async_similarity_search()` with `k=6`.
2. The vector store filters candidates by `kind` and `appliance_type`, applies score boosts for metadata matches, returns top 6 by cosine similarity.
3. `rerank_chunks(user_msg, guides, top_k=3)` sends snippets to Haiku and re-orders by semantic relevance.
4. The top 3 chunks are formatted into a context string and injected into the user's message before the Sonnet call.

The index is built offline by `build_index.py`. Each guide produces a summary chunk plus step-group chunks, so a 6-step guide becomes 3 chunks (summary, steps 1-3, steps 4-6). Each chunk carries metadata (`symptom_keywords`, `part_numbers`, `appliance_type`, `step_range`) used for filtering and boosting.

### Authentication

Tokens are `<base64(user_id:timestamp)>.<hmac_sha256_signature>`. No expiry in demo mode — `parse_token` ignores the timestamp after verifying the signature. The secret key is hardcoded in `security.py` (fine for a demo; would be an env var in production).

Every protected endpoint calls `get_current_user(request)` at the top, which reads the `Authorization` header, parses and verifies the token, and returns the `User` object or `None`.

### Persistent threads

Each user can have multiple named threads. Threads and messages are stored together in `threads.json`. When a chat request arrives with no `thread_id`, a new thread is auto-created and its ID is returned in the response so the frontend can track it.

Thread history is loaded from `threads.json` via `ThreadStore`, cached in `_session_cache` (RAM, 30-min TTL) for fast subsequent reads. When a thread exceeds 20 messages, the oldest 10 are summarised by Haiku into a single assistant message and written back to the thread store.

Thread titles are auto-set from the first user message (first 50 characters) after the first response is generated.

### Cart & checkout

The cart stores `CartItem` objects per user in `carts.json`. When a user clicks "Add to Cart" on a product card, the frontend posts `{part_number}` to `/api/cart/items`. The backend looks up the full product data (name, price, URL, image) from `products.json` and builds the cart item.

"Checkout on PartSelect" calls `/api/cart/checkout-links`, which returns the `url` fields from each cart item (or a `search.aspx?SearchTerm=` fallback). The frontend opens each URL in a new tab via `window.open(..., "noopener,noreferrer")`. No private PartSelect cart API is called — this is a browser handoff only.

### Performance optimisations

| Optimisation | Where | Effect |
|-------------|-------|--------|
| Keyword fast-path | `agent.py:_classify_intent_and_flags` | ~80% of queries skip the Haiku classification call |
| Combined classifier | `agent.py:_classify_intent_and_flags` | One Haiku call replaces two (intent + follow-up) |
| Session cache | `agent.py:_session_cache` | Avoids reading `threads.json` on every turn |
| Response cache | `agent.py:_response_cache` | Identical queries skip RAG + LLM entirely |
| Haiku for fast tasks | `claude_client.py:MODEL_FAST` | Classification, reranking, clarification, summarisation all use Haiku (8× cheaper than Sonnet) |
| History summarisation | `agent.py:_summarize_messages` | Keeps context window bounded for long threads |

### Markdown rendering

Claude's responses often contain `**bold**`, `- bullet points`, and `[links](url)`. The `MarkdownText` component handles these without any npm dependency, using a simple line-by-line parser that emits React elements. This is applied to all assistant message text in `MessageList`.
