# Auto PDF Codebase Master Guide (All.md)

Generated from source review of the current workspace.
Workspace root: /Users/priyanshu/Desktop/Auto pdf
Primary backend path: backend/
Primary frontend path: frontend/

---

## 1) What This Product Does

This project is an AI-powered exam content platform that lets users:
1. Generate exam-style PDFs (JEE, NEET, CBSE, GATE, Olympiad) with optional solutions.
2. Stream generation progress via SSE and preview partial questions before final PDF compile.
3. Save generated PDFs to private/unlisted/public libraries.
4. Share PDFs as social posts, like/download them, and compete on a leaderboard.
5. Create and attempt NTA-CBT-style tests with timer, palette, review states, and result analytics.
6. Use institute-specific generation workflows and branding.
7. Upgrade via Cashfree payments (Free/Earth/Universe plan model).
8. Raise support tickets with screenshot/audio evidence.
9. Generate short educational videos from prompts using Manim + TTS + FFmpeg.
10. Render diagram assets via template-driven diagram APIs.

---

## 2) Repository Layout (Important Paths)

| Path | Role |
|---|---|
| backend/main.py | Main FastAPI app, SSE generation orchestration, core generation endpoints |
| backend/routers/*.py | Modular API routers (auth, posts, pdf, test, tests, community, institute, payments, support, video, diagram) |
| backend/services/llm_engine.py | Core LLM orchestration, fallback, chunked parallel generation, verification, anti-dup logic |
| backend/services/pdf_engine.py | PDF generation and LaTeX sanitization/render pipeline |
| backend/services/job_store.py | In-memory job lifecycle + subscribers for SSE |
| backend/services/storage.py | S3 abstraction for uploads, signed URLs, object key extraction |
| backend/services/manim_generator.py | LLM-to-Manim code generation and safety checks |
| backend/services/tts_engine.py | TTS abstraction (Edge, ElevenLabs, OpenAI) |
| backend/diagram_engine/* | Diagram registry/schemas/generator and template rendering |
| backend/models.py | SQLAlchemy models for users, content, tests, billing, logs, support |
| frontend/app/* | Next.js App Router pages |
| frontend/components/* | Reusable UI blocks (generator, feeds, modals, profile, nav, etc.) |
| frontend/lib/* | Auth context, generation context, config, logger, community API adapter, theming |
| Raw_Autopdf/All.md | This master documentation file |

Note: Root-level Python files (for example main.py, auth.py, models.py at repository root) exist as an older code path. The active production-style implementation is the backend/ folder.

---

## 3) Tech Stack

### Backend

| Area | Stack |
|---|---|
| Web API | FastAPI |
| Data models | SQLAlchemy |
| Validation | Pydantic |
| Auth | JWT access/refresh token model |
| Password hashing | passlib + bcrypt |
| LLM gateway | litellm |
| Model providers | Gemini/OpenAI/Anthropic through litellm |
| PDF engine | LaTeX templating + compile path + reportlab fallback utilities |
| Async events | SSE via StreamingResponse + job queue state |
| File storage | AWS S3 via boto3 |
| Payments | Cashfree API + webhook |
| Video pipeline | Manim + edge-tts + ffmpeg |
| Diagrams | Pydantic schema + Jinja2 template + pdflatex/pdf2svg |

### Frontend

| Area | Stack |
|---|---|
| Framework | Next.js App Router |
| Language | TypeScript |
| UI | React |
| Styling | Tailwind CSS |
| Icons | lucide-react |
| Auth/session | Custom AuthContext + refresh/retry authFetch |
| Streaming | EventSource SSE + reconnect + status polling fallback |
| Payment UI | @cashfreepayments/cashfree-js |
| Math rendering | katex + remark-math + rehype-katex |
| Charts | recharts |

### Deployment and Ops

| Area | Stack |
|---|---|
| Containers | Docker/Dockerfile variants |
| Deployment hints | App Runner, Cloud Run docs/scripts, Heroku files also present |
| Runtime config | .env-driven configuration and API URL fallback logic |

---

## 4) High-Level Architecture

### 4.1 Auth and Session Model

1. User signs up/logs in with email/password or Google OAuth.
2. Backend returns access token + refresh token.
3. Frontend stores auth_token + refresh_token and user snapshot in localStorage.
4. authFetch wrapper retries on 401 by calling /auth/refresh and replaying request.
5. Periodic background refresh runs every 10 minutes.
6. logout revokes refresh token server-side and clears local state.

### 4.2 PDF Generation (SSE-first Flow)

1. Frontend calls /api/generate-sse/start.
2. Backend creates a job in services/job_store.py and returns job_id.
3. Frontend opens EventSource on /api/generate-sse/{job_id}/stream with token query param.
4. Backend background task:
5. Analyze request and compute split.
6. Run LLM generation (with verification/top-up and anti-dup support).
7. Stream partial_questions as chunks become available.
8. Compile PDF in background.
9. Emit done status with pdf_base64 and metadata.
10. Frontend supports reconnect via /api/generate-sse/{job_id}/status.
11. Frontend can request immediate partial PDF via /api/generate-partial-pdf while full compile continues.

### 4.3 Test Portal Flow (NTA style)

1. Create test via SSE flow:
   - Frontend calls /api/tests/create-async → returns job_id instantly.
   - Frontend opens EventSource on /api/tests/{job_id}/stream for real-time progress.
   - Backend generates questions per-subject in background, streaming progress ("Generating Physics 1/3...").
   - On completion, SSE emits done status with test_id.
   - Fallback: /api/tests/{job_id}/status polling for reconnection on network drops.
   - Legacy sync endpoint /api/tests/create still exists for backward compatibility.
2. Launch attempt via /test/{test_id}/launch.
3. Instruction page then /test/{test_id}/start.
4. Runtime API calls:
5. /state
6. /question/{index}
7. /action (SAVE_NEXT, CLEAR, SAVE_MARK_NEXT, MARK_NEXT, BACK, NEXT, JUMP)
8. Summary via /summary.
9. Final submit via /submit (or /violation-submit when exam security triggers forced submit).
10. Result via /result and history via /test/history.

### 4.4 Community and Social Flow

1. User saves generated PDF record.
2. User posts from PostModal with visibility control.
3. Feed ranks/sorts and exposes like/download/share actions.
4. Leaderboard and badges are derived from engagement caches and relationships.

### 4.5 Payments and Plan Enforcement

1. Client requests /api/payments/create-order.
2. Backend creates Cashfree order + stores PaymentOrder.
3. Client opens Cashfree checkout.
4. Webhook validates signature and marks order paid.
5. UserSubscription and user.plan are updated.
6. Plan limits are consumed by generation and institute actions.

### 4.6 Video Generation Flow

1. /api/video/generate creates background job.
2. LLM builds Manim code + narration script.
3. Validate/fix code attempts.
4. Manim renders video.
5. TTS creates narration audio.
6. FFmpeg merges tracks.
7. Upload final mp4 to S3.
8. Client polls /api/video/status/{job_id} or listens to stream endpoint.

---

## 5) Backend API Inventory

## 5.1 Core Endpoints in backend/main.py

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | / | No | Basic health |
| GET | /api/health | No | Service health + active model |
| POST | /api/detect-subject | No | Topic-to-subject detection with cache |
| GET | /api/history | Yes | Recent generation history |
| POST | /api/store-subject | No | Crowdsource topic-subject cache entry |
| GET | /api/rate-limit | Yes | Current plan usage + reset window |
| POST | /api/generate | Yes | Non-SSE direct generation flow |
| POST | /api/generate-institute | Yes | Paid-plan institute-branded generation |
| GET | /api/download/{filename} | No/Contextual | Download/redirect generated PDF |
| POST | /api/generate-verified | Yes | Verified generation with optional solutions |
| POST | /api/apply-promo | Yes | Apply promo code bonus |
| POST | /api/log-error | Optional | Client/system error ingestion |
| POST | /api/admin/seed-promo | Admin key | Seed/reset promo and monthly entries |
| GET | /api/models | No | Advertised model list |
| POST | /api/generate-sse/start | Yes | Start SSE generation job |
| GET | /api/generate-sse/{job_id}/stream | Token query | SSE stream for job updates |
| GET | /api/generate-sse/{job_id}/status | Yes | Poll job snapshot |
| POST | /api/generate-partial-pdf | Yes | Build on-demand PDF from partial questions |

## 5.2 Auth Router (/auth)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /auth/register | Register account |
| POST | /auth/login | Login |
| POST | /auth/google | Google OAuth login/signup |
| POST | /auth/refresh | Access token refresh |
| POST | /auth/logout | Revoke current refresh token |
| POST | /auth/logout-all | Revoke all refresh tokens |
| GET | /auth/me | Current user profile |
| POST | /auth/verify-email | Verify token |
| POST | /auth/resend-verification | Resend verification email |
| POST | /auth/forgot-password | Send password reset link |
| POST | /auth/reset-password | Reset password |
| PUT | /auth/profile | Update user profile |
| GET | /auth/settings | User settings payload |
| PUT | /auth/settings/fresh-questions | Toggle fresh question mode |
| GET | /auth/me/pdfs | User PDFs by visibility |

## 5.3 Posts Router (/api/posts)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/posts/set-username | Set public username |
| POST | /api/posts | Create post from saved PDF |
| GET | /api/posts | Community feed (cursor pagination) |
| GET | /api/posts/my | Current user posts |
| GET | /api/posts/check-existing | Check similar existing tests |
| GET | /api/posts/{post_id} | Post detail |
| POST | /api/posts/{post_id}/like | Like post |
| DELETE | /api/posts/{post_id}/like | Unlike post |
| POST | /api/posts/{post_id}/download | Track download metric |
| DELETE | /api/posts/{post_id} | Delete own post |
| PATCH | /api/posts/{post_id}/visibility | Update visibility |
| GET | /api/posts/leaderboard/{category} | Most-liked/most-posts leaderboard |
| GET | /api/posts/badges/my | Fetch earned badges |

## 5.4 PDF Router (/pdf)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /pdf/{slug} | Public/unlisted slug redirect via signed URL |
| GET | /pdf/{slug}/info | Slug metadata for viewer page |
| POST | /pdf/{pdf_id}/generate-link | Create unlisted share link |
| PUT | /pdf/{pdf_id}/visibility | Toggle PDF visibility |
| POST | /pdf/save | Save generated file into library record |

## 5.5 Payments Router (/api/payments)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/payments/create-order | Create Cashfree order/session |
| GET | /api/payments/order/{order_id}/status | Poll order state |
| POST | /api/payments/webhook | Cashfree webhook ingestion and plan activation |

## 5.6 Institute Router (/api/institute)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/institute/login | Institute login |
| POST | /api/institute/refresh | Institute token refresh |
| GET | /api/institute/profile | Institute profile |
| PUT | /api/institute/profile | Institute profile update |
| POST | /api/institute/detect-subjects | Bulk chapter classification |
| POST | /api/institute/generate-sse/start | Institute SSE job start |
| POST | /api/institute/generate | Direct institute generation |
| POST | /api/institute/admin/create | Admin create institute account |

## 5.7 Test Runtime Router (/test)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /test/{test_id}/launch | Create attempt session from test |
| GET | /test/{test_id}/state | Attempt state + palette + timer |
| POST | /test/{test_id}/start | Start attempt |
| GET | /test/{test_id}/question/{index} | Get question payload |
| POST | /test/{test_id}/action | CBT action handler |
| GET | /test/{test_id}/summary | Pre-submit summary counts |
| POST | /test/{test_id}/submit | Standard submit |
| POST | /test/{test_id}/violation-submit | Forced submit with security log |
| GET | /test/{test_id}/result | Detailed result/analytics |
| GET | /test/history | User test history |

## 5.8 Tests Management Router (/api/tests)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/tests/create | Sync create master test (legacy, may timeout on proxy) |
| POST | /api/tests/create-async | Start async test creation job, returns job_id instantly |
| GET | /api/tests/{job_id}/stream | SSE stream for test creation progress (token via query param) |
| GET | /api/tests/{job_id}/status | Poll test creation job status (reconnection fallback) |
| GET | /api/tests/my | List user-created tests |
| PATCH | /api/tests/{test_id}/approve | Approval flow for moderation |

## 5.9 Community Router (/api/community)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/community/tests | Search/discover public tests |
| GET | /api/community/tests/{test_id} | Community test detail |
| GET | /api/community/tests/{test_id}/leaderboard | Community leaderboard |
| POST | /api/community/tests/{test_id}/start | Start attempt from community |

## 5.10 Support Router (/support)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /support/create | Raise support ticket |
| GET | /support/my | My tickets |
| GET | /support/admin/all | Admin ticket feed |
| PATCH | /support/{ticket_id}/status | Admin status/response update |

## 5.11 Video Router (/api/video)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/video/generate | Start video generation job |
| GET | /api/video/status/{job_id} | Poll video job status |
| GET | /api/video/status/{job_id}/stream | SSE stream for video job |
| GET | /api/video/providers | List TTS providers |
| GET | /api/video/voices | List voice options |
| GET | /api/video/history/me | User video history |
| DELETE | /api/video/{video_id} | Delete generated video record |

## 5.12 Diagram Router (/api/diagram)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/diagram/render | Validate params and return SVG diagram |

---

## 6) Data Model Inventory (backend/models.py)

| Model | What it stores |
|---|---|
| User | Auth profile, plan, premium flags, social counters, fresh-question toggle |
| RefreshToken | User refresh sessions |
| VerificationToken | Email verification links |
| PasswordResetToken | Password reset links |
| PDFGeneration | Generation history and status |
| PromoCode | Promo config and usage caps |
| PromoCodeUsage | User-to-promo usage events |
| TopicSubjectCache | Cached topic -> subject mapping |
| InstituteUser | Institute auth profile |
| InstituteRefreshToken | Institute refresh sessions |
| InstituteGeneration | Institute generation records |
| SharedPDF | Library/post metadata with visibility and counters |
| PDFLike | Like relationships |
| UserBadge | Earned badges |
| SystemErrorLog | Frontend/backend error logs |
| UserQuestionHistory | Per-user question history for anti-repeat generation |
| Test | Master test objects and publication metadata |
| TestLeaderboard | Per-test best performance by user |
| TestAttempt | Attempt session state and score summary |
| QuestionResponse | Per-question attempt details and status |
| SupportTicket | Support system records with optional media URLs |
| APIUsageLog | Per-call token accounting logs |
| TotalAPIUsage | Per-generation token aggregates |
| PaymentOrder | Cashfree order tracking |
| UserSubscription | Active plan period and status |

---

## 7) Backend Service Layer

| File | Main responsibilities |
|---|---|
| backend/services/llm_engine.py | Subject detection, question generation, async parallel chunking, fallback handling, dedup, verification flows, usage logging |
| backend/services/pdf_engine.py | LaTeX-safe sanitization, formatting fixes, PDF rendering pipeline |
| backend/services/job_store.py | Thread-safe in-memory jobs with SSE subscriber queues and cleanup |
| backend/services/storage.py | S3 upload/download/signed URL/object-key helpers |
| backend/services/manim_generator.py | Prompt enhancement, Manim code generation, banned-pattern checks, retry strategy |
| backend/services/tts_engine.py | Multi-provider TTS abstraction and voice listings |
| backend/diagram_engine/generator.py | Schema-validated render pipeline to SVG |
| backend/diagram_engine/registry.py | Supported diagram type map |
| backend/diagram_engine/schemas.py | Diagram parameter models |

---

## 8) Frontend Route Map (App Router)

| Route | Main page role |
|---|---|
| / | Desktop 3-column layout: nav + posts feed + generator |
| /generator | Generator-focused page |
| /posts | Community feed page |
| /community | Public community test discovery |
| /community/test/[testId] | Community test detail + leaderboard + start attempt |
| /community/create | Redirect to /test/create |
| /test | Test portal dashboard/history |
| /test/create | Test creation wizard |
| /test/[id]/instructions | NTA-style instruction screen |
| /test/[id] | Full test attempt interface |
| /test/[id]/result | Result analytics page |
| /leaderboard | Global post leaderboard page |
| /profile | Profile page |
| /settings | Full settings hub (profile/theme/promo/library visibility) |
| /support | Ticket creation and ticket list |
| /admin/tickets | Admin moderation page for support tickets |
| /pricing | Plan comparison and checkout trigger |
| /payment/success | Payment status polling and plan sync |
| /login | Email/password and Google sign-in |
| /signup | Registration and Google signup |
| /forgot-password | Password reset request |
| /reset-password | Password reset apply |
| /verify-email | Email verification landing |
| /pdf/[slug] | Public/unlisted PDF viewer and download |
| /institute | Institute generation page |
| /institute/login | Redirect currently to /generator |
| /institute/profile | Institute branding profile editor |
| /video-generator | Manim video generation UI |
| /trial | Legacy trial generator page using generate-verified |

---

## 9) Frontend Core Contexts and Shared Logic

| File | Feature |
|---|---|
| frontend/lib/auth-context.tsx | User auth store, refresh mutex, authFetch retry, login/register/logout, resend verification, refresh user |
| frontend/lib/generation-context.tsx | SSE generation lifecycle, reconnect strategy, partial questions state, timer, cancel/reset/download helpers |
| frontend/lib/institute-auth-context.tsx | Institute auth token/refresh/authFetch and profile update |
| frontend/lib/config.ts | API base URL resolver with unsupported host fallback |
| frontend/lib/logger.ts | Console interception ring buffer + offline log queue + sync-on-reconnect |
| frontend/lib/theme-context.tsx | Light/dark theme persistence |
| frontend/lib/community-api.ts | Typed wrappers for community test endpoints |

---

## 10) Major UI Components and Feature Roles

| Component | Key behavior |
|---|---|
| frontend/components/TestGenerator.tsx | Main generation cockpit for student + institute mode, chapter selection, exam pattern controls, SSE preview, partial/final download, post/save flow |
| frontend/components/PostsFeed.tsx | Feed listing, filters, like sync queue, download tracking, share/copy actions, delete own posts |
| frontend/components/PostModal.tsx | Caption + visibility post publish modal |
| frontend/components/UsernameModal.tsx | Force username setup/update flow |
| frontend/components/Profile.tsx | Profile form editor |
| frontend/components/Leaderboard.tsx | Most-liked and most-active leaderboard tabs |
| frontend/components/TestCard.tsx | Community test card with share and attempt CTA |
| frontend/components/VoiceRecorder.tsx | Mic recording for support voice notes |
| frontend/components/layout/DesktopSidebar.tsx | Desktop navigation and account panel |
| frontend/components/layout/MobileNav.tsx | Bottom mobile nav with plan CTA |
| frontend/components/test/DiagramRenderer.tsx | Inline SVG diagram render in test questions |
| frontend/components/WhatsAppButton.tsx | Home-only floating WhatsApp CTA |

---

## 11) Full Button and Action Inventory

This section focuses on visible button-level behavior and linked backend actions.

| Screen | Button/Control | Action | API/Effect |
|---|---|---|---|
| Desktop sidebar | Home | Navigate home | Client route /
| Desktop sidebar | INFINITEST | Open generator | Client route /generator |
| Desktop sidebar | Test Portal | Open community tests | Client route /community |
| Desktop sidebar | Explore | Open posts feed | Client route /posts |
| Desktop sidebar | Leaderboard | Open leaderboard page | Client route /leaderboard |
| Desktop sidebar | Profile | Open profile | Client route /profile |
| Desktop sidebar | Support | Open support | Client route /support |
| Desktop sidebar | Settings | Open settings | Client route /settings |
| Desktop sidebar | Upgrade CTA | Open pricing | Client route /pricing |
| Desktop sidebar | Theme | Toggle light/dark | theme-context toggleTheme |
| Desktop sidebar | Account menu logout | Logout | /auth/logout + local cleanup |
| Mobile nav | Home | Navigate home | Client route / |
| Mobile nav | Feed | Navigate posts | Client route /posts |
| Mobile nav | Test Portal | Navigate community | Client route /community |
| Mobile nav | Support | Navigate support | Client route /support |
| Mobile nav | Settings | Navigate settings | Client route /settings |
| Mobile nav | Upgrade pill | Open pricing | Client route /pricing |
| Generator | Student tab | Student mode | Local UI mode switch |
| Generator | Institute tab | Institute mode gate by auth/plan | Redirect signup/pricing or open institute panel |
| Generator | Topic input | Search/add chapter/custom topic | ncert/gate chapter helpers |
| Generator | Chapter quick select | Bulk select by class/all | Local chapter selection update |
| Generator | Existing tests CTA | View matching posts | Route to /posts with query filters |
| Generator | Subject chips | Multi-subject selection | Local state |
| Generator | GATE paper chips | Set gate paper | Local state |
| Generator | Exam type chips | Set level | Local state + pattern defaults |
| Generator | Difficulty percentage inputs | Set easy/medium/hard % | Local validation to 100% |
| Generator | Pattern inputs | Configure per-pattern counts | Local state |
| Generator | Include solutions toggle | Enable solution generation | Sent to generation API |
| Generator | Generate test paper | Start SSE generation | /api/generate-sse/start |
| Generator | Cancel generation | Cancel local stream/timer | generation-context cancel |
| Generator | Partial question expand | Open question card detail | Local UI state |
| Generator | Show answer/hide | Toggle solution visibility | Local UI state |
| Generator | Download current questions | Generate partial PDF | /api/generate-partial-pdf |
| Generator | Download final PDF | Download final artifact | base64 download or /api/download/{file} |
| Generator | Post | Open publish modal | Uses /api/posts after save |
| Generator | Save to library (via flow) | Save PDF metadata | /pdf/save |
| Generator | Recent test card click | Open generated PDF | /api/download/{filename} |
| Generator institute mode | Detect/select chapters | Chapter list and custom topic | Local state |
| Generator institute mode | Exam type and difficulty | Configure institute generation | Local state |
| Generator institute mode | Subject count inputs | Set per-subject totals | Local state with cap |
| Generator institute mode | Generate Institute Test Paper | Generate institute PDF | /api/generate-institute |
| Generator institute mode | Cancel Generation | Abort request | AbortController |
| Generator institute mode | Download Institute PDF | Download returned PDF | base64 or /api/download |
| Posts feed | Community Feed tab | Show ranked feed | /api/posts |
| Posts feed | My Posts tab | Show own posts | /api/posts/my |
| Posts feed | Subject/Level filters | Filter feed server-side | /api/posts query params |
| Posts feed | Search box | Client-side search across fields | Local filter |
| Posts feed | Post card click/download icon | Download PDF + track count | /api/posts/{id}/download + /api/download/{filename} |
| Posts feed | Like | Optimistic like toggle | /api/posts/{id}/like |
| Posts feed | Unlike | Reverse like | DELETE /api/posts/{id}/like |
| Posts feed | Share toggle | Open share actions | Local UI state |
| Posts feed | Native share | System share sheet | navigator.share |
| Posts feed | Copy link | Copy downloadable URL | Clipboard API |
| Posts feed | Delete | Remove own post | DELETE /api/posts/{id} |
| Post modal | Visibility public/unlisted/private | Select visibility | Local state |
| Post modal | Post | Create post | POST /api/posts |
| Username modal | Save Username | Set username | POST /api/posts/set-username |
| Community page | Search | Search tests | /api/community/tests |
| Community page | Subject filter | Filter tests | /api/community/tests |
| Community page | Exam filter | Filter tests | /api/community/tests |
| Community page | Sort newest/popular/trending | Reorder feed | /api/community/tests |
| Community page | Create Public Test | Open create test wizard | /test/create?mode=public |
| Community test detail | Attempt Now | Start community attempt | POST /api/community/tests/{id}/start |
| Community test detail | Share | UI share intent | Local/share API |
| Test create | Visibility selector | Private/community/classroom mode | Sent in /api/tests/create |
| Test create | Subject enable/count/difficulty/topics | Build subject_inputs payload | Sent in /api/tests/create-async |
| Test create | Create test | Start async SSE job + stream progress + auto-launch | /api/tests/create-async → SSE stream → /test/{id}/launch |
| Test instructions | Proceed | Start attempt after acceptance | POST /test/{id}/start |
| Test attempt | Subject tabs | Jump by section | /test/{id}/action JUMP |
| Test attempt | Palette number | Jump to question | /test/{id}/action JUMP |
| Test attempt | Save and Next | Save answer and move | /test/{id}/action SAVE_NEXT |
| Test attempt | Clear | Clear response | local + /test/{id}/action CLEAR |
| Test attempt | Save and Mark for Review | Save + marked | /test/{id}/action SAVE_MARK_NEXT |
| Test attempt | Mark for Review and Next | Mark no answer + next | /test/{id}/action MARK_NEXT |
| Test attempt | Back | Prev question | /test/{id}/action BACK |
| Test attempt | Next | Next question | /test/{id}/action NEXT |
| Test attempt | Submit | Open summary then submit | GET /summary then POST /submit |
| Test attempt | Forced submit path | Auto-submit after violations | POST /violation-submit |
| Test attempt | Security warning acknowledge | Return to exam and request fullscreen | useExamSecurity clearWarning |
| Test result | Show Questions | Reveal question review list | Local state |
| Test result | Filter all/correct/wrong/unattempted | Filter question review | Local state |
| Test result | Take Another Test | Open creation page | /test/create |
| Test result | View All Tests | Open test dashboard | /test |
| Settings | Profile save | Update user profile | PUT /auth/profile |
| Settings | Plan upgrade cards | Open pricing | /pricing |
| Settings | Promo apply | Redeem promo | POST /api/apply-promo |
| Settings | Theme cards | Toggle theme | theme-context |
| Settings | Fresh questions toggle | Toggle anti-repeat mode | PUT /auth/settings/fresh-questions |
| Settings | Private/Public/Unlisted tabs | Fetch filtered user library | GET /auth/me/pdfs |
| Settings | Download PDF | Open PDF file | /api/download/{filename} |
| Settings | Copy/Get link | Generate/copy unlisted slug | POST /pdf/{id}/generate-link |
| Settings | Public button | Promote to public feed | PATCH /api/posts/{id}/visibility |
| Settings | Delete PDF/post | Delete item | DELETE /api/posts/{id} |
| Support create | Category select | Set ticket category | Form state |
| Support create | Screenshot upload | Attach image | multipart to /support/create |
| Support create | Voice recorder controls | Record/stop/delete audio | Web media APIs |
| Support create | Submit Ticket | Create support ticket | POST /support/create |
| Support list | Switch to My Tickets | Fetch tickets | GET /support/my |
| Admin tickets | Filter ALL/OPEN/RESOLVED | Filter dataset | Local state |
| Admin tickets | Manage ticket | Open modal | Local state |
| Admin tickets | Save changes | Update status/response | PATCH /support/{ticket_id}/status |
| Pricing | Get Earth Plan | Start checkout | POST /api/payments/create-order |
| Pricing | Get Universe Plan | Start checkout | POST /api/payments/create-order |
| Payment success | Refresh | Recheck payment state | GET /api/payments/order/{id}/status |
| Payment success | Go Home | Return app | Client route |
| Login | Sign in | Email login | POST /auth/login |
| Login | Google sign in | OAuth login | POST /auth/google |
| Login | Forgot password | Open reset request page | /forgot-password |
| Signup | Create account | Register | POST /auth/register |
| Signup | Google signup | OAuth signup | POST /auth/google |
| Forgot password | Send reset link | Start reset flow | POST /auth/forgot-password |
| Reset password | Reset password | Apply new password | POST /auth/reset-password |
| Verify email | Verify token | Mark account verified | POST /auth/verify-email |
| Profile page | Save Changes | Update profile | PUT /auth/profile |
| Leaderboard page | Most liked / Most active tabs | Change category | /api/posts/leaderboard/{category} |
| PDF slug page | Download PDF | Open slug endpoint | GET /pdf/{slug} |
| Video generator | Topic dropdown | Select topic category | Local state |
| Video generator | Language dropdown | Select narration language | Local state |
| Video generator | Upload image | Attach optional visual input | Local state |
| Video generator | Remove image | Remove uploaded preview | Local state |
| Video generator | Example prompt chips | Prefill prompt | Local state |
| Video generator | Generate video | Start video job | POST /api/video/generate |
| Video generator | Download video | Download rendered video | S3 URL |
| Video generator | View/Hide code | Toggle generated Manim code panel | Local state |

---

## 12) Security and Quality Features

1. Test attempt hardening via frontend hook:
2. Fullscreen enforcement attempts.
3. Visibility change/tab switch detection.
4. Devtools shortcut blocking + heuristic checks.
5. Copy/cut/paste/select prevention.
6. Warning threshold that triggers forced submit.
7. Detailed security log payload attached on violation-submit.

8. Generation quality controls:
9. Difficulty and pattern-specific request shaping.
10. Numeric verification pass for generated numericals.
11. Top-up logic if LLM under-generates requested counts.
12. Question deduplication and user-history anti-repeat logic.

13. Observability:
14. Client logger intercepts console history and syncs offline error queue.
15. Server stores SystemErrorLog and API usage token records.

---

## 13) Plan and Limit Model

Observed plan matrix in code:

| Plan | PDF limit | Test limit | Institute PDF | Video |
|---|---:|---:|---:|---|
| free | 5/month | 4 | No | No |
| earth | 10/month | effectively unlimited | 1/month | No |
| universe | unlimited | unlimited | 4/month | Yes |

Rate-limit reset logic is monthly in active backend flow, with promo overlays and additional institute-specific counters.

---

## 14) Notable Implementation Details

1. API base URL safety fallback in frontend/lib/config.ts rejects unsupported hosts and falls back to default App Runner URL.
2. SSE stream endpoint requires token via query string due EventSource header limitations.
3. SharedPDF creation in SSE generation is manual-save flow now, to avoid auto-filling private library limits.
4. /institute/login page currently redirects to /generator.
5. /community/create page currently redirects to /test/create.
6. There are duplicate legacy root-level backend files beside backend/; active stack is in backend/.
7. Test creation uses SSE-based async flow (/api/tests/create-async + /api/tests/{job_id}/stream) to avoid Vercel proxy timeout (502) on long LLM generation. The pattern mirrors the existing PDF generation SSE flow. Legacy sync /api/tests/create endpoint still exists but will timeout through Vercel proxy for >30s generations.
7. auth_router.py contains duplicated field/endpoint declarations in some sections (works but should be cleaned for maintenance clarity).

---

## 15) Suggested Cleanup Backlog (Optional, for maintainability)

1. Remove duplicated legacy backend path or mark it explicitly deprecated.
2. Normalize repeated definitions in auth_router.py and User model relationships.
3. Convert in-memory job stores to Redis/database for multi-instance reliability.
4. Centralize endpoint docs from decorators into generated OpenAPI markdown snapshots.
5. Add test coverage for payment webhook, forced-submit flow, and SSE reconnect edge cases.

---

## 16) Quick Feature Checklist

| Domain | Status |
|---|---|
| Auth + refresh + Google | Implemented |
| Email verification + reset | Implemented |
| Student PDF generation | Implemented |
| Institute generation | Implemented |
| Streaming progress + partial questions | Implemented |
| Partial PDF download while compiling | Implemented |
| Save private/unlisted/public PDF records | Implemented |
| Community posting + likes + downloads + leaderboard | Implemented |
| Test creation + runtime CBT + results | Implemented |
| Exam security with forced submit | Implemented |
| Pricing + Cashfree payment + subscription updates | Implemented |
| Support tickets + admin moderation | Implemented |
| Video generation pipeline | Implemented |
| Diagram rendering API | Implemented |

---

## 17) Final Summary

This codebase is a full education content platform, not just a PDF generator. It combines:
1. AI content generation (questions and videos).
2. Real-time generation UX with SSE and partial delivery.
3. Exam runtime simulation (NTA-CBT behavior).
4. Social/community mechanics (posts, likes, leaderboard).
5. Commercial subscription controls (Cashfree billing and plans).
6. Institute workflows and support/admin operations.

The highest-complexity module on frontend is TestGenerator.tsx, and the highest-complexity module on backend is services/llm_engine.py with backend/main.py orchestration.
