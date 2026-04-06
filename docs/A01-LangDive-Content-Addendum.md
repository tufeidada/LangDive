# A01 · LangDive Content System Improvement — Addendum to v1.1

> **Scope:** Replaces Pipeline Step 1-2 in the main document  
> **Priority:** P0 — must be implemented in MVP  
> **Affects:** Pipeline, data models, API endpoints, frontend (1 hidden page)

---

## 1. Architecture: Three-Layer Content Pool

The content system uses a **three-layer sourcing model** instead of raw keyword search. Each layer has different priority, refresh frequency, and quality characteristics.

```
┌──────────────────────────────────────────────────────────┐
│                    DAILY PIPELINE                         │
│                                                          │
│  Layer 1: WHITELIST (highest priority)                   │
│  ├── YouTube channels → pull latest videos               │
│  ├── Newsletters → parse RSS, extract recommended links  │
│  ├── Substack/Blog RSS → pull new articles               │
│  └── Output: ~20-30 candidates/day                       │
│                                                          │
│  Layer 2: CLASSIC LIBRARY (fill + variety)               │
│  ├── Pre-imported evergreen essays/talks                 │
│  ├── Random draw when Layer 1 < 15 candidates            │
│  └── Output: 0-5 candidates/day                          │
│                                                          │
│  Layer 3: SEARCH (lowest priority, fallback only)        │
│  ├── LLM-generated YouTube search queries                │
│  ├── Only activated if Layer 1+2 < 10 candidates         │
│  └── Output: 0-10 candidates/day                         │
│                                                          │
│  ─── AI RANKING ───                                      │
│  All candidates → LLM scores & selects 5                 │
│  (1-2 videos + 3-4 articles)                             │
│  Selected → full Pipeline processing (Step 3-9)          │
│                                                          │
│  ─── USER OVERRIDE (hidden page, optional) ───           │
│  Can promote/reject candidates, submit URLs               │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Content Source Whitelist

### 2.1 YouTube Channels (Video)

> ⚠️ **IMPLEMENTATION NOTE — YouTube Channel Fetching**
>
> Do NOT use `search.list` for whitelist channels. Use `playlistItems.list` with the channel's uploads playlist ID. This is more reliable, doesn't consume search quota, and returns chronological results.
>
> ```python
> # Get uploads playlist ID: replace "UC" prefix with "UU"
> # Channel ID: UCrBzBOMcUVV8ryyAU_c6P5g (Bloomberg Technology)
> # Uploads playlist: UUrBzBOMcUVV8ryyAU_c6P5g
> youtube.playlistItems().list(playlistId="UU...", part="snippet", maxResults=5)
> ```

| Channel | Channel ID | Content Type | Difficulty | Tags |
|---|---|---|---|---|
| Lex Fridman Podcast | UCSHZKJJfhK1O0g4PenTXSGQ | AI/Science/Philosophy long interviews | B2-C1 | AI, Tech |
| All-In Podcast | UCESLZhusAkFfsNsApnjF_Cg | Tech/VC/Macro 4-person discussion | B2 | Finance, Tech |
| Bloomberg Technology | UCrBzBOMcUVV8ryyAU_c6P5g | Finance + Tech daily interviews | B2 | Finance, Tech |
| a16z (Andreessen Horowitz) | UCOmOuZ7AxVYnatig15jk5Sg | VC perspective, tech analysis | B2 | Tech, Management |
| Y Combinator | UCcefcZRL2oaA_uBNeo5UOWg | Startup talks, founder interviews | B1-B2 | Tech, Management |
| TED | UCAuUUnT6oDeKwE6v1NGQxug | General talks (filter by topic) | B1-B2 | General |
| Acquired Podcast | UC_5RqZ5L3Kc3VvJwXLOTZjQ | Company deep-dive case studies | B2-C1 | Tech, Finance |
| Patrick Boyle | UCASM0cgfkJxQ1ICmRilfHLQ | Financial markets, hedge funds, humor | B2-C1 | Finance |
| Ben Felix | UC5cN4PGIkBGo_c7q0UNc-Rg | Evidence-based investing | B2 | Finance |
| Tim Ferriss Show | UCznv7Vf9nBdJYvBagFdAHWw | Interviews with world-class performers | B2 | General, Management |

### 2.2 Newsletters & RSS (Article — curated links)

> ⚠️ **IMPLEMENTATION NOTE — Newsletter Parsing**
>
> Newsletters like TLDR AI and Ben's Bites are **meta-curators**: they link to original articles. The pipeline should:
> 1. Fetch the newsletter via RSS
> 2. Extract all outbound links from the newsletter body
> 3. Use Trafilatura to fetch each linked article's full text
> 4. Treat each linked article as a separate candidate (not the newsletter itself)
>
> This means one newsletter issue can produce 5-10 candidates.

| Source | RSS / URL | Type | Frequency | Difficulty | Tags |
|---|---|---|---|---|---|
| TLDR AI | tldrai.info (RSS) | AI daily digest → extract links | Daily | B1-B2 | AI |
| Ben's Bites | bensbites.com (RSS) | AI tools + business → extract links | Daily | B1-B2 | AI, Tech |
| The Batch (deeplearning.ai) | deeplearning.ai/the-batch (RSS) | AI weekly roundup | Weekly | B2 | AI |
| Stratechery | stratechery.com/feed (RSS) | Tech business deep analysis | Weekly (free) | B2-C1 | Tech, Finance |
| Not Boring (Packy McCormick) | notboring.co (Substack RSS) | Tech/business long essays | Weekly | B2 | Tech, Finance |
| Lenny's Newsletter | lennysnewsletter.com (Substack RSS) | Product management, startups | Weekly | B2 | Tech, Management |
| Hacker News (Top) | news.ycombinator.com/rss | Tech community curated | Continuous | B1-C1 | Tech |

> ⚠️ **IMPLEMENTATION NOTE — Hacker News**
>
> HN RSS returns high volume. Filter candidates by score: only include items with `score >= 100` (indicates community validation). Use the Algolia HN API for score filtering:
> ```
> https://hn.algolia.com/api/v1/search?tags=story&numericFilters=points>100&hitsPerPage=10
> ```

### 2.3 Direct Blog/Essay RSS (Article — original content)

| Source | RSS / URL | Content Type | Difficulty | Tags |
|---|---|---|---|---|
| Paul Graham | paulgraham.com/rss.html | Startup/thinking essays | B2-C1 | Tech, Management |
| Morgan Housel (Collab Fund) | collabfund.com/blog/feed | Investing psychology | B2 | Finance |
| Farnam Street (fs.blog) | fs.blog/feed | Mental models, decision-making | B2 | General, Management |
| Wait But Why | waitbutwhy.com/feed | Science/tech/philosophy mega-posts | B1-B2 | Tech, General |
| a16z Blog | a16z.com/feed | VC insights, tech trends | B2 | Tech, Finance |
| MIT Tech Review | technologyreview.com/feed | Deep tech journalism | B2 | AI, Tech |
| Ars Technica | feeds.arstechnica.com/arstechnica/index | Tech analysis | B1-B2 | Tech |
| BBC Tech | feeds.bbci.co.uk/news/technology/rss.xml | Tech news (accessible) | B1 | Tech |

### 2.4 Classic Library (Evergreen, pre-imported)

> ⚠️ **IMPLEMENTATION NOTE — Classic Library**
>
> These are NOT fetched daily. They are **one-time imports** into the database during `init_db.py` or via a separate `seed_classics.py` script. Each entry is stored as a `content_candidate` with `source_layer = 'classic'` and `status = 'library'`.
>
> When the daily pipeline finds fewer than 15 Layer 1 candidates, it randomly draws from the classic library to supplement. Classic items are marked as `used` after being selected, so they don't repeat.

| Source | Quantity | Content Type | Difficulty |
|---|---|---|---|
| Paul Graham Essays (paulgraham.com/articles.html) | ~220 essays | Startups, thinking, society | B2-C1 |
| Naval Ravikant (almanack + tweets compiled) | ~50 pieces | Wealth, happiness, philosophy | B1-B2 |
| Morgan Housel selected essays | ~30 essays | Investing, behavioral finance | B2 |
| Wait But Why selected posts | ~20 mega-posts | AI, Fermi paradox, procrastination | B1-B2 |
| Farnam Street selected | ~30 essays | Mental models, decision-making | B2 |
| TED Talks (curated list, video) | ~50 talks | Mixed topics, high production quality | B1-B2 |

**Total classic library: ~400 items.** At a rate of 0-2 classics per day, this lasts 6-12 months before exhaustion.

---

## 3. Data Model Changes

### 3.1 New Table: `content_source`

```sql
CREATE TABLE content_source (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,                        -- "Lex Fridman Podcast"
  type TEXT NOT NULL CHECK(type IN (
    'youtube_channel', 'newsletter_rss', 'blog_rss', 'hn_api', 'classic_library'
  )),
  url TEXT NOT NULL,                          -- RSS URL or channel ID
  extra_config JSONB,                        -- type-specific config (see below)
  layer INTEGER NOT NULL DEFAULT 1 CHECK(layer IN (1, 2, 3)),
  priority INTEGER DEFAULT 50,               -- 1-100, higher = more preferred
  quality_score REAL DEFAULT 0.5,            -- 0-1, adjustable by user feedback
  default_difficulty TEXT,                    -- estimated CEFR level
  tags JSONB,                                -- ["AI", "Finance"]
  is_active BOOLEAN DEFAULT TRUE,
  last_fetched TIMESTAMPTZ,
  fetch_error_count INTEGER DEFAULT 0,       -- consecutive errors; disable after 5
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extra_config examples:
-- youtube_channel: {"channel_id": "UC...", "uploads_playlist": "UU...", "min_duration_minutes": 5}
-- newsletter_rss: {"extract_links": true, "max_links_per_issue": 10}
-- hn_api: {"min_score": 100, "max_items": 10}
-- classic_library: {"import_script": "seed_classics.py"}
```

### 3.2 New Table: `content_candidate`

```sql
CREATE TABLE content_candidate (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source_id INTEGER REFERENCES content_source(id),
  source_layer INTEGER NOT NULL,              -- 1, 2, or 3
  type TEXT CHECK(type IN ('article', 'video')),
  
  -- Pre-screening metadata (lightweight, no full extraction yet)
  estimated_difficulty TEXT,
  estimated_word_count INTEGER,
  summary TEXT,                               -- LLM-generated 1-sentence summary
  thumbnail_url TEXT,                         -- for video candidates
  duration TEXT,                              -- for video candidates
  published_at TIMESTAMPTZ,
  
  -- AI ranking results
  ai_score REAL,                              -- 0-1, composite score
  ai_reason TEXT,                             -- "High relevance: AI + finance intersection, B2 difficulty matches target"
  
  -- Status
  status TEXT DEFAULT 'pending' CHECK(status IN (
    'pending',          -- just fetched, not yet ranked
    'selected',         -- AI picked for today
    'rejected',         -- AI skipped (with reason)
    'user_promoted',    -- user manually selected from pool
    'user_rejected',    -- user manually rejected
    'user_submitted',   -- user pasted URL
    'library',          -- classic library item, not yet used
    'library_used'      -- classic library item, already served
  )),
  
  date DATE NOT NULL,                         -- pipeline date
  content_hash TEXT,
  content_id INTEGER REFERENCES content(id),  -- set after full processing
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(url, date)                           -- same URL won't appear twice on same day
);

CREATE INDEX idx_candidate_date_status ON content_candidate(date, status);
CREATE INDEX idx_candidate_source ON content_candidate(source_id);
```

### 3.3 New Table: `search_query_log` (for Layer 3 only)

```sql
CREATE TABLE search_query_log (
  id SERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'youtube',
  result_count INTEGER,
  date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Revised Pipeline Steps 0-2

Replace the original Pipeline Steps 1-2 with the following:

```
Step 0: FETCH CANDIDATES FROM ALL LAYERS

  Layer 1 — Whitelist Sources (parallel fetch):
  
    For each active source where type = 'youtube_channel':
      ├── Call YouTube playlistItems.list(uploadsPlaylistId, maxResults=5)
      ├── Filter: published in last 7 days, duration > 5 min
      ├── Filter: has captions (call videos.list to check contentDetails)
      ├── Insert into content_candidate (status='pending', source_layer=1)
      └── Update source.last_fetched

    For each active source where type = 'newsletter_rss':
      ├── Fetch RSS feed
      ├── Parse latest issue(s) since last_fetched
      ├── If source.extra_config.extract_links = true:
      │   ├── Extract all outbound links from issue body (skip internal/nav links)
      │   ├── For each link: create a content_candidate (type='article')
      │   └── Limit: max_links_per_issue from extra_config
      ├── Else: treat the issue itself as a candidate
      └── Insert into content_candidate (status='pending', source_layer=1)

    For each active source where type = 'blog_rss':
      ├── Fetch RSS feed
      ├── Parse new entries since last_fetched
      └── Insert into content_candidate (status='pending', source_layer=1)

    For each active source where type = 'hn_api':
      ├── Call Algolia HN API: points > min_score, last 48 hours
      ├── Filter: exclude Show HN, Ask HN, job posts
      ├── Take top max_items by score
      └── Insert into content_candidate (status='pending', source_layer=1)

  Layer 2 — Classic Library (supplement):
    ├── Count Layer 1 candidates for today
    ├── If count < 15:
    │   ├── Draw (15 - count) random items where status='library'
    │   └── Set their date to today, status to 'pending', source_layer=2
    └── Else: skip

  Layer 3 — Search Fallback (emergency only):
    ├── Count Layer 1 + Layer 2 candidates for today
    ├── If count < 10:
    │   ├── Generate LLM search queries (same logic as current doc)
    │   ├── Execute YouTube searches
    │   ├── Insert results into content_candidate (source_layer=3)
    │   └── Log queries to search_query_log
    └── Else: skip

  De-duplication:
    ├── Check content_candidate.url against last 30 days of candidates
    ├── Check content_candidate.content_hash against cached_asset table
    └── Remove duplicates (set status='rejected', ai_reason='duplicate')


Step 1: AI RANKING

  ├── Collect all today's candidates where status='pending'
  ├── Also include any where status='user_promoted' or 'user_submitted'
  │   (these are pre-approved, always included)
  ├── Send candidate titles + summaries + source info to LLM:
  │
  │   Prompt:
  │   """
  │   You are selecting today's English learning content for a Chinese learner.
  │   Learner profile: IELTS B1-B2, interests in AI/finance/tech/management.
  │   
  │   Candidates (one per line, format: [ID] [TYPE] [SOURCE] [TITLE]):
  │   {candidate_list}
  │   
  │   Select exactly 5 items following these rules:
  │   - 1-2 videos + 3-4 articles (hard constraint)
  │   - Prioritize Layer 1 sources over Layer 2, Layer 2 over Layer 3
  │   - Prefer diverse sources (don't pick 3 from same source)
  │   - Prefer difficulty B1-B2 (allow 1 item at C1 for challenge)
  │   - Prefer content published in last 7 days (except classics)
  │   - user_promoted and user_submitted items are ALWAYS included
  │   
  │   For each candidate, provide:
  │   - score: 0-1 (relevance * quality * difficulty_match)
  │   - selected: true/false
  │   - reason: one sentence explanation
  │   
  │   Return ONLY JSON array sorted by score DESC.
  │   """
  │
  ├── Parse LLM response
  ├── Top 5 (or user-overridden): set status='selected'
  ├── Remaining: set status='rejected' with ai_reason
  └── Proceed to Step 2 (extract content) for selected items only


Step 2-9: unchanged from main document
  Only process candidates where status IN ('selected', 'user_promoted', 'user_submitted')
```

---

## 5. New API Endpoints

### 5.1 Content Candidates (for hidden admin page)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/candidates?date={date}` | All candidates for a date, grouped by status |
| PUT | `/api/candidates/{id}/promote` | User manually selects → triggers Pipeline Step 2-9 for this item |
| PUT | `/api/candidates/{id}/reject` | User manually rejects |
| POST | `/api/content/submit-url` | User pastes URL → creates candidate with status='user_submitted', triggers immediate processing |

### 5.2 Content Sources (for hidden admin page)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sources` | List all content sources with stats |
| POST | `/api/sources` | Add new source |
| PUT | `/api/sources/{id}` | Update source (priority, is_active, tags) |
| DELETE | `/api/sources/{id}` | Deactivate source (soft delete: set is_active=false) |

### 5.3 Submit URL Detail

```
POST /api/content/submit-url
Body: { "url": "https://..." }

Response flow:
1. Create content_candidate with status='user_submitted', source_layer=0
2. Run Trafilatura/youtube-transcript-api to extract content
3. Run Pipeline Steps 3-9 (segment, annotate, TTS, etc.)
4. Return: { "candidate_id": 123, "content_id": 456, "status": "processing" }

Processing is synchronous (single user, acceptable to wait 30-60s).
Frontend shows a loading state: "Processing your content..."
```

---

## 6. Hidden Admin Page: `/pool`

> ⚠️ **IMPLEMENTATION NOTE — Hidden Page**
>
> This page is accessible via direct URL `/pool` only. There is NO link, button, or menu item pointing to it anywhere in the frontend UI. It is not in the navigation, not on the home page, not in settings.
>
> No authentication is needed (single-user system). The page simply exists at that route.

### 6.1 Page Layout

```
Route: /pool
Title: Content Pool

┌──────────────────────────────────────────────────┐
│  Content Pool            [date picker: today ▼]  │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │ 📥 Paste URL to add content              │    │
│  │ ┌────────────────────────────┐ [Submit]  │    │
│  │ │ https://...                │           │    │
│  │ └────────────────────────────┘           │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ── Sources (32 active) ──────── [Manage ▼] ──   │
│  │ When expanded:                               │
│  │ ✅ Lex Fridman    YT  P:90  Q:0.8  [Edit]   │
│  │ ✅ TLDR AI        RSS P:85  Q:0.7  [Edit]   │
│  │ ⬜ TechCrunch     RSS P:40  Q:0.4  [Edit]   │
│  │ [+ Add Source]                               │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ── Today's Selected (5) ─────────────────────   │
│  ┌──────────────────────────────────────────┐    │
│  │ ✅ 🎬 Lex Fridman: Neural Networks...    │    │
│  │    Layer 1 · Score: 0.92 · B2            │    │
│  │    "High relevance + recent + quality"   │    │
│  │    [Remove from today]                   │    │
│  ├──────────────────────────────────────────┤    │
│  │ ✅ 📄 Stratechery: Why SaaS Isn't...    │    │
│  │    Layer 1 · Score: 0.88 · B2-C1         │    │
│  │    "Deep analysis, matches finance tag"  │    │
│  │    [Remove from today]                   │    │
│  ├──────────────────────────────────────────┤    │
│  │ ... (3 more)                             │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ── Candidates Not Selected (18) ─────────────   │
│  ┌──────────────────────────────────────────┐    │
│  │ ○ 📄 a16z: The Future of AI Agents       │    │
│  │   Layer 1 · Score: 0.71 · B2             │    │
│  │   "Good quality but overlaps with #2"    │    │
│  │   [↑ Promote to today]                   │    │
│  ├──────────────────────────────────────────┤    │
│  │ ○ 📄 HN: Show HN: Open-source LLM...    │    │
│  │   Layer 1 · Score: 0.65 · B2             │    │
│  │   "Technical, slightly above target"     │    │
│  │   [↑ Promote to today]                   │    │
│  ├──────────────────────────────────────────┤    │
│  │ ○ 📄 Paul Graham: Cities and Ambition    │    │
│  │   Layer 2 (classic) · Score: 0.60 · B2   │    │
│  │   "Evergreen essay, good variety"        │    │
│  │   [↑ Promote to today]                   │    │
│  ├──────────────────────────────────────────┤    │
│  │ ... (15 more, collapsed)  [Show all]     │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ── Pipeline Status ──────────────────────────   │
│  Last run: 2026-04-05 06:02:13 SGT              │
│  Layer 1: 24 fetched · Layer 2: 3 drawn          │
│  Layer 3: not triggered                          │
│  Selected: 5 · Processed: 5/5 ✓                  │
│  Errors: 0                                       │
└──────────────────────────────────────────────────┘
```

### 6.2 Key Interactions

**Promote a candidate:**
- Click "↑ Promote to today" on any unselected candidate
- Calls `PUT /api/candidates/{id}/promote`
- Backend sets status to `user_promoted` and triggers Pipeline Steps 2-9 for this item
- Frontend shows processing spinner, then moves item to "Selected" section
- If already 5 selected: the lowest-scoring AI-selected item gets bumped to "Candidates" (status back to 'rejected')

**Submit URL:**
- Paste URL in the input box, click Submit
- Calls `POST /api/content/submit-url`
- Frontend shows "Processing..." state (30-60s)
- When done, item appears in "Selected" section with status `user_submitted`

**Manage Sources:**
- Expand "Sources" section to see all content sources
- Each source shows: name, type, priority (P), quality score (Q), active/inactive toggle
- Edit inline: change priority, toggle active/inactive
- "Add Source" button: form with name, type, URL, tags

### 6.3 Component

```
frontend/src/pages/Pool.tsx        # the hidden admin page
frontend/src/components/
  ├── CandidateCard.tsx            # single candidate row
  ├── SourceManager.tsx            # source list + edit
  ├── UrlSubmitForm.tsx            # paste URL input
  └── PipelineStatus.tsx           # last run info
```

Add route (no navigation link):
```tsx
// App.tsx
<Route path="/pool" element={<Pool />} />
// Do NOT add <Link to="/pool"> anywhere in the UI
```

---

## 7. Seed Data: `seed_sources.py`

Script to initialize all whitelist sources on first setup:

```python
SOURCES = [
    # Layer 1: YouTube Channels
    {"name": "Lex Fridman Podcast", "type": "youtube_channel", "layer": 1, "priority": 95,
     "url": "https://youtube.com/@lexfridman",
     "extra_config": {"channel_id": "UCSHZKJJfhK1O0g4PenTXSGQ", "uploads_playlist": "UUSHZKJJfhK1O0g4PenTXSGQ", "min_duration_minutes": 10},
     "tags": ["AI", "Tech"], "default_difficulty": "B2"},

    {"name": "All-In Podcast", "type": "youtube_channel", "layer": 1, "priority": 90,
     "url": "https://youtube.com/@alaborofjoy",
     "extra_config": {"channel_id": "UCESLZhusAkFfsNsApnjF_Cg", "uploads_playlist": "UUESLZhusAkFfsNsApnjF_Cg", "min_duration_minutes": 10},
     "tags": ["Finance", "Tech"], "default_difficulty": "B2"},

    {"name": "Bloomberg Technology", "type": "youtube_channel", "layer": 1, "priority": 85,
     "url": "https://youtube.com/@BloombergTelevision",
     "extra_config": {"channel_id": "UCrBzBOMcUVV8ryyAU_c6P5g", "uploads_playlist": "UUrBzBOMcUVV8ryyAU_c6P5g", "min_duration_minutes": 5},
     "tags": ["Finance", "Tech"], "default_difficulty": "B2"},

    {"name": "a16z", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@a16z",
     "extra_config": {"channel_id": "UCOmOuZ7AxVYnatig15jk5Sg", "uploads_playlist": "UUOmOuZ7AxVYnatig15jk5Sg", "min_duration_minutes": 5},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Y Combinator", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@ycombinator",
     "extra_config": {"channel_id": "UCcefcZRL2oaA_uBNeo5UOWg", "uploads_playlist": "UUcefcZRL2oaA_uBNeo5UOWg", "min_duration_minutes": 5},
     "tags": ["Tech", "Management"], "default_difficulty": "B1"},

    {"name": "TED", "type": "youtube_channel", "layer": 1, "priority": 70,
     "url": "https://youtube.com/@TED",
     "extra_config": {"channel_id": "UCAuUUnT6oDeKwE6v1NGQxug", "uploads_playlist": "UUAuUUnT6oDeKwE6v1NGQxug", "min_duration_minutes": 5},
     "tags": ["General"], "default_difficulty": "B1"},

    {"name": "Acquired Podcast", "type": "youtube_channel", "layer": 1, "priority": 85,
     "url": "https://youtube.com/@AcquiredFM",
     "extra_config": {"channel_id": "UC_5RqZ5L3Kc3VvJwXLOTZjQ", "uploads_playlist": "UU_5RqZ5L3Kc3VvJwXLOTZjQ", "min_duration_minutes": 15},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Patrick Boyle", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@PBoyle",
     "extra_config": {"channel_id": "UCASM0cgfkJxQ1ICmRilfHLQ", "uploads_playlist": "UUASM0cgfkJxQ1ICmRilfHLQ", "min_duration_minutes": 8},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Ben Felix", "type": "youtube_channel", "layer": 1, "priority": 75,
     "url": "https://youtube.com/@BenFelixCSI",
     "extra_config": {"channel_id": "UC5cN4PGIkBGo_c7q0UNc-Rg", "uploads_playlist": "UU5cN4PGIkBGo_c7q0UNc-Rg", "min_duration_minutes": 5},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Tim Ferriss Show", "type": "youtube_channel", "layer": 1, "priority": 75,
     "url": "https://youtube.com/@timferriss",
     "extra_config": {"channel_id": "UCznv7Vf9nBdJYvBagFdAHWw", "uploads_playlist": "UUznv7Vf9nBdJYvBagFdAHWw", "min_duration_minutes": 10},
     "tags": ["Management", "General"], "default_difficulty": "B2"},

    # Layer 1: Newsletter RSS (extract links)
    {"name": "TLDR AI", "type": "newsletter_rss", "layer": 1, "priority": 85,
     "url": "https://tldr.tech/ai/rss",
     "extra_config": {"extract_links": True, "max_links_per_issue": 8},
     "tags": ["AI"], "default_difficulty": "B1"},

    {"name": "Ben's Bites", "type": "newsletter_rss", "layer": 1, "priority": 80,
     "url": "https://bensbites.com/feed",
     "extra_config": {"extract_links": True, "max_links_per_issue": 6},
     "tags": ["AI", "Tech"], "default_difficulty": "B1"},

    {"name": "The Batch (deeplearning.ai)", "type": "newsletter_rss", "layer": 1, "priority": 75,
     "url": "https://www.deeplearning.ai/the-batch/feed",
     "extra_config": {"extract_links": True, "max_links_per_issue": 5},
     "tags": ["AI"], "default_difficulty": "B2"},

    # Layer 1: Blog RSS (direct content)
    {"name": "Stratechery", "type": "blog_rss", "layer": 1, "priority": 90,
     "url": "https://stratechery.com/feed/",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Not Boring", "type": "blog_rss", "layer": 1, "priority": 85,
     "url": "https://www.notboring.co/feed",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Lenny's Newsletter", "type": "blog_rss", "layer": 1, "priority": 80,
     "url": "https://www.lennysnewsletter.com/feed",
     "extra_config": {},
     "tags": ["Tech", "Management"], "default_difficulty": "B2"},

    {"name": "Paul Graham", "type": "blog_rss", "layer": 1, "priority": 85,
     "url": "http://www.paulgraham.com/rss.html",
     "extra_config": {},
     "tags": ["Tech", "Management"], "default_difficulty": "B2"},

    {"name": "Morgan Housel", "type": "blog_rss", "layer": 1, "priority": 80,
     "url": "https://collabfund.com/blog/feed/",
     "extra_config": {},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Farnam Street", "type": "blog_rss", "layer": 1, "priority": 75,
     "url": "https://fs.blog/feed/",
     "extra_config": {},
     "tags": ["Management", "General"], "default_difficulty": "B2"},

    {"name": "a16z Blog", "type": "blog_rss", "layer": 1, "priority": 70,
     "url": "https://a16z.com/feed/",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "MIT Technology Review", "type": "blog_rss", "layer": 1, "priority": 70,
     "url": "https://www.technologyreview.com/feed/",
     "extra_config": {},
     "tags": ["AI", "Tech"], "default_difficulty": "B2"},

    {"name": "Ars Technica", "type": "blog_rss", "layer": 1, "priority": 60,
     "url": "https://feeds.arstechnica.com/arstechnica/index",
     "extra_config": {},
     "tags": ["Tech"], "default_difficulty": "B1"},

    {"name": "BBC Technology", "type": "blog_rss", "layer": 1, "priority": 55,
     "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
     "extra_config": {},
     "tags": ["Tech"], "default_difficulty": "B1"},

    # Layer 1: Hacker News
    {"name": "Hacker News Top", "type": "hn_api", "layer": 1, "priority": 65,
     "url": "https://hn.algolia.com/api/v1/search",
     "extra_config": {"min_score": 100, "max_items": 10},
     "tags": ["Tech"], "default_difficulty": "B2"},

    # Layer 2: Classic Library (seeded separately by seed_classics.py)
    {"name": "Classic Library", "type": "classic_library", "layer": 2, "priority": 50,
     "url": "internal://classic-library",
     "extra_config": {"import_script": "seed_classics.py"},
     "tags": ["General"], "default_difficulty": "B2"},
]
```

---

## 8. Updated Project Structure (additions only)

```
backend/
  ├── app/
  │   ├── routers/
  │   │   ├── candidates.py          # NEW: candidate pool API
  │   │   └── sources.py             # NEW: content source management API
  │   ├── services/
  │   │   ├── fetcher.py             # NEW: multi-layer content fetcher
  │   │   ├── newsletter_parser.py   # NEW: extract links from newsletter HTML
  │   │   └── hn.py                  # NEW: Hacker News API client
  │   └── pipeline/
  │       └── steps.py               # MODIFIED: new Step 0 (fetch) and Step 1 (rank)
  ├── scripts/
  │   ├── seed_sources.py            # NEW: initialize content_source table
  │   └── seed_classics.py           # NEW: import classic library items

frontend/
  ├── src/
  │   ├── pages/
  │   │   └── Pool.tsx               # NEW: hidden admin page at /pool
  │   └── components/
  │       ├── CandidateCard.tsx       # NEW
  │       ├── SourceManager.tsx       # NEW
  │       ├── UrlSubmitForm.tsx       # NEW
  │       └── PipelineStatus.tsx      # NEW
```

---

## 9. Development Phase Impact

This addendum **extends Phase 1** by approximately 3-4 days:

**Phase 1 additions:**
- [ ] Create `content_source` and `content_candidate` tables
- [ ] Run `seed_sources.py` to initialize whitelist
- [ ] Run `seed_classics.py` to import classic library (~400 items)
- [ ] Implement multi-layer fetcher (`fetcher.py`)
- [ ] Implement newsletter link parser (`newsletter_parser.py`)
- [ ] Implement HN API client (`hn.py`)
- [ ] Rewrite Pipeline Step 0 (fetch from all layers)
- [ ] Rewrite Pipeline Step 1 (AI ranking with candidate table)
- [ ] Implement candidate API endpoints
- [ ] Implement source management API endpoints
- [ ] Implement `/api/content/submit-url` endpoint

**Phase 2 additions (minimal):**
- [ ] Build `/pool` page (Pool.tsx)
- [ ] Build CandidateCard, SourceManager, UrlSubmitForm, PipelineStatus components
- [ ] Wire to candidate/source APIs
- [ ] Do NOT add any navigation link to /pool
