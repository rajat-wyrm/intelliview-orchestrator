# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/).

Entries below this point are generated automatically by [semantic-release](https://semantic-release.gitbook.io/) from Conventional Commits on every merge to the release branch. See `CONTRIBUTING.md` for the commit format.

## 1.0.0 (2026-08-10)

### Features

* add automatic worker restart after MAX_TASKS_BEFORE_RESTART tasks (Issue [#524](https://github.com/aa-kriti/intelliview-orchestrator/issues/524)) ([d488d6c](https://github.com/aa-kriti/intelliview-orchestrator/commit/d488d6c08a0158f47df609daa90e027d1b779bf2))
* add CandidateList component with Reschedule modal fix ([#276](https://github.com/aa-kriti/intelliview-orchestrator/issues/276)) ([528457e](https://github.com/aa-kriti/intelliview-orchestrator/commit/528457e94060d0432ea15b5bca8feaaad2243dcc))
* add config for Gemini, Grok, screen lock, real-time tracking, Neon DB SSL ([56ec7c9](https://github.com/aa-kriti/intelliview-orchestrator/commit/56ec7c98cb650169100b488f8fb8a3af10e156a4))
* add DashboardSkeleton component with loading placeholders ([6556f4a](https://github.com/aa-kriti/intelliview-orchestrator/commit/6556f4ad8dd168fbcc026f9049acb779865ed29f))
* add downloadable risk report endpoint (JSON/PDF) - closes [#91](https://github.com/aa-kriti/intelliview-orchestrator/issues/91) ([646015d](https://github.com/aa-kriti/intelliview-orchestrator/commit/646015d2bd6508bf548aed291002e980cfc86bdb))
* add error handler hook with deduplication and rate limiting ([a09ad31](https://github.com/aa-kriti/intelliview-orchestrator/commit/a09ad31385cbb635b2a53f0371ab05df520b4871))
* add Gemini and Grok AI integration to ai_client ([e2de7cd](https://github.com/aa-kriti/intelliview-orchestrator/commit/e2de7cd733a10376c293e91162211eca7a16bbb5))
* add Gemini and Grok fallback to evaluation pipeline ([cb301d7](https://github.com/aa-kriti/intelliview-orchestrator/commit/cb301d7ef2cf511acb06e79b9c22ec785dc34a4c))
* add interview report API endpoint ([23d43ea](https://github.com/aa-kriti/intelliview-orchestrator/commit/23d43ea3c4ee839b83313c8ffd4a9b19c61ad594))
* add moment timeline to session detail modal ([264e622](https://github.com/aa-kriti/intelliview-orchestrator/commit/264e6226de9103500a1d20e25613d11e68c777c9))
* add multilingual notification template engine ([5f927fc](https://github.com/aa-kriti/intelliview-orchestrator/commit/5f927fc885ae973f8ae9b366ec0c29edfbda0fe7))
* add performance hooks (debounce, throttle, virtual list, lazy load) ([ab1e0a8](https://github.com/aa-kriti/intelliview-orchestrator/commit/ab1e0a8d8fb4a06961b912e8c349d53765a10a3f))
* add persistent subscriber storage ([1fa1db4](https://github.com/aa-kriti/intelliview-orchestrator/commit/1fa1db4a40913b83b75dc4f178cb9b3c786d4343))
* add priority queues (high/medium/low) for Celery pipeline ([72b987a](https://github.com/aa-kriti/intelliview-orchestrator/commit/72b987a0c030d209c4ee278a8f17c8cc5857f87e))
* add real-time moment tracking for interview sessions ([e5667cc](https://github.com/aa-kriti/intelliview-orchestrator/commit/e5667cc88d7ce8cd1cfdc8fc80fbc477f8b4c8fd))
* add Redis connection pooling with configurable limits ([7b6efc0](https://github.com/aa-kriti/intelliview-orchestrator/commit/7b6efc09af030173646777b784656ba265542fa9))
* add request_id param to log_config_change ([d6e85e1](https://github.com/aa-kriti/intelliview-orchestrator/commit/d6e85e1fb928a690f0217cab6046a9898f7c92ad))
* add reusable get_db dependency ([bdd02e2](https://github.com/aa-kriti/intelliview-orchestrator/commit/bdd02e226d9128a342a71377b4eda84b58b1246a))
* add risk status badge handling for HR-08 ([62328ce](https://github.com/aa-kriti/intelliview-orchestrator/commit/62328ce2e00a3d29fa4f08aa895f74e449d827be))
* add screen lock with auto-lock and PIN unlock ([e58c296](https://github.com/aa-kriti/intelliview-orchestrator/commit/e58c2964d3b14eda53c7d6e0da2738274fc084a5))
* add sortable table header component ([9018c17](https://github.com/aa-kriti/intelliview-orchestrator/commit/9018c170f0a45e83f9bae49df5bae7fcbee59931))
* add SortableHeader component ([79d0510](https://github.com/aa-kriti/intelliview-orchestrator/commit/79d05104c67a14e9c4d64b02518c320c7e211e34))
* add SSL connection support for Neon DB ([8e0d639](https://github.com/aa-kriti/intelliview-orchestrator/commit/8e0d6396c53f6b568b9207f60bedcbf6f0a3988e))
* add VideoPlayer component for interview recording playback ([e90e861](https://github.com/aa-kriti/intelliview-orchestrator/commit/e90e8617cb8382f204c0f535fb954daa926210d3))
* add worker capability tags during worker registration ([68c9d49](https://github.com/aa-kriti/intelliview-orchestrator/commit/68c9d49061c2fef6ab06cfef9b7c4da8a0234cd3))
* assemble HR dashboard page with filtering, Tailwind styling, and unit tests ([380a359](https://github.com/aa-kriti/intelliview-orchestrator/commit/380a359c76c78a27d1cf0b6212f42ed272054389))
* **audio:** Integrate Voice Activity Detection (VAD) to skip silent audio segments during analysis ([#455](https://github.com/aa-kriti/intelliview-orchestrator/issues/455)) ([02c16e1](https://github.com/aa-kriti/intelliview-orchestrator/commit/02c16e15a1c5d39c662d426524efa415c08ee807))
* build HR profile page with edit and save ([#390](https://github.com/aa-kriti/intelliview-orchestrator/issues/390)) ([cd61590](https://github.com/aa-kriti/intelliview-orchestrator/commit/cd61590a1ec472347dd1c75733ef833ec4160c90))
* complete persistent subscriber storage ([4179f62](https://github.com/aa-kriti/intelliview-orchestrator/commit/4179f628deb5cf555f11aa20785b1c7d2aecfa95))
* complete Task 1.1 JWT Login and User Table ([f9181dc](https://github.com/aa-kriti/intelliview-orchestrator/commit/f9181dc4a6630e99b7935fb61bb1d2bb123b8734))
* enhance dashboard with glassmorphism cards and live indicator ([15e90fb](https://github.com/aa-kriti/intelliview-orchestrator/commit/15e90fb4571b9dabb05eb02059cad1cc48c22d1a))
* enhance settings page with glassmorphism and cache clear ([17d43e8](https://github.com/aa-kriti/intelliview-orchestrator/commit/17d43e80b44d287af7d537e68f0e7a70252bfd68))
* enhance WebSocket hook with send/reconnect and realtime subscription ([ef8eeda](https://github.com/aa-kriti/intelliview-orchestrator/commit/ef8eeda53f18a58f8a96a873a337070ae6883fe2))
* **frontend:** implement synced video player with closed captions ([#512](https://github.com/aa-kriti/intelliview-orchestrator/issues/512)) ([6b6dc2b](https://github.com/aa-kriti/intelliview-orchestrator/commit/6b6dc2b3d6a1ed446a298a8d642195daa6e40dc1))
* graceful degradation with HTTP 503 fallback when all workers saturated ([887728e](https://github.com/aa-kriti/intelliview-orchestrator/commit/887728e3c0c3604fedf30bc8f94db0691472aebe))
* **hr-dashboard:** add dashboard API service with mock fallback ([ed9e8db](https://github.com/aa-kriti/intelliview-orchestrator/commit/ed9e8db09b1a384dec2ca35d0a7b93aef54ff206))
* **hr-dashboard:** add reusable filter bar component ([1ca84ca](https://github.com/aa-kriti/intelliview-orchestrator/commit/1ca84ca2f1aad44a055516ff6f4a09446ab59008))
* **hr:** add SortableHeader with 3-state sorting and single active column state ([#358](https://github.com/aa-kriti/intelliview-orchestrator/issues/358)) ([c948f62](https://github.com/aa-kriti/intelliview-orchestrator/commit/c948f62dbfc1d921eadbdb925d7f7844914bfb0b))
* implement cache warming for configuration data on startup ([#274](https://github.com/aa-kriti/intelliview-orchestrator/issues/274)) ([cd2c9fe](https://github.com/aa-kriti/intelliview-orchestrator/commit/cd2c9fedf0f180bd8f8b2bbc9d9347e05b2f3938))
* implement Smooth Weighted Round Robin scheduling strategy ([ac33560](https://github.com/aa-kriti/intelliview-orchestrator/commit/ac335607b3eb4b5747a75f56ad3f4d23f147beba))
* implement task 4.4 sentiment analysis ([e86eeb4](https://github.com/aa-kriti/intelliview-orchestrator/commit/e86eeb42be900306937027f4f49dc05d44bc8c9b))
* implement Web Vitals monitoring ([131f400](https://github.com/aa-kriti/intelliview-orchestrator/commit/131f400166c4a852f926a850db1591b637110f3f))
* integrate AWS Secrets Manager dynamic config and unit tests ([f2b4665](https://github.com/aa-kriti/intelliview-orchestrator/commit/f2b4665d530637224ac31285abd49a41992bf7f7))
* integrate digest notifications dashboard, dockerize service, and update navigation ([baa27c2](https://github.com/aa-kriti/intelliview-orchestrator/commit/baa27c2f3c1055800918cea1264d2b69933bc56e))
* integrate moment tracking into interview page ([94e582d](https://github.com/aa-kriti/intelliview-orchestrator/commit/94e582de7e74329ccef416984a40b0ce892dc847))
* integrate Notification-Deduplication module ([ed2c214](https://github.com/aa-kriti/intelliview-orchestrator/commit/ed2c214c2cc25bef752ed4fb5cda115ff812c932))
* integrate push-notification-setup-new module ([ec82bef](https://github.com/aa-kriti/intelliview-orchestrator/commit/ec82bef607d0cda07a25c020546c18e93182d81d))
* track LLM token usage and add database migration ([#120](https://github.com/aa-kriti/intelliview-orchestrator/issues/120)) ([41ef712](https://github.com/aa-kriti/intelliview-orchestrator/commit/41ef712526e4dee7532e8feb740fffef2910d781))
* transform into best modern AI interview system ([1b8e709](https://github.com/aa-kriti/intelliview-orchestrator/commit/1b8e709ee80605f1239190d624ac6567ca57ec6e))

### Bug Fixes

* add candidate records for PostgreSQL foreign key tests ([02a7148](https://github.com/aa-kriti/intelliview-orchestrator/commit/02a7148e47a7b25099bacbe5fb48432d820701db))
* add database configuration validation ([59d161d](https://github.com/aa-kriti/intelliview-orchestrator/commit/59d161dd08b4584d304346c55b2b6c483c19658f))
* Add database indexes for frequently queried columns ([#338](https://github.com/aa-kriti/intelliview-orchestrator/issues/338)) ([a2abeec](https://github.com/aa-kriti/intelliview-orchestrator/commit/a2abeecad518e0b3fb688b82eb103d8698321fdf))
* add error handling for database engine initialization ([cec3a80](https://github.com/aa-kriti/intelliview-orchestrator/commit/cec3a80367b79a861fd844f872099ba45a474965))
* add guardrail validation for LLM-generated interview questions ([#121](https://github.com/aa-kriti/intelliview-orchestrator/issues/121)) ([7fa299a](https://github.com/aa-kriti/intelliview-orchestrator/commit/7fa299a6eef2aeab22744d6f4a11e48ae41bdcfd))
* add missing public folder for docker build ([e9aceb6](https://github.com/aa-kriti/intelliview-orchestrator/commit/e9aceb621248688e450efe6a3967602c82b26df3))
* add reset sort on third click and filter change ([28cec02](https://github.com/aa-kriti/intelliview-orchestrator/commit/28cec02c47269017e3fb6487e49724bb769bb385))
* add trailing newline to load_balancer.py ([2771091](https://github.com/aa-kriti/intelliview-orchestrator/commit/27710918904f01777ce783bf61c468d81b458025))
* add trailing newline to load_balancer.py ([4a4e478](https://github.com/aa-kriti/intelliview-orchestrator/commit/4a4e478e02a2b2cc56d05e698aff50f6934d8f3b))
* add trailing newline to satisfy ruff lint ([f9ccf72](https://github.com/aa-kriti/intelliview-orchestrator/commit/f9ccf72951acb57d71d86ef71d5354b08ab1921b))
* add trailing newline to worker_entrypoint.py ([6af356e](https://github.com/aa-kriti/intelliview-orchestrator/commit/6af356ef407325fb6d12a25d0f7430fe90f0f5e3))
* add TTLs to Redis health and dead-letter queue keys ([#199](https://github.com/aa-kriti/intelliview-orchestrator/issues/199)) ([4196a72](https://github.com/aa-kriti/intelliview-orchestrator/commit/4196a72b1a54e469edcab705e62ceb7e22743deb))
* address web vitals review feedback ([e27f7b4](https://github.com/aa-kriti/intelliview-orchestrator/commit/e27f7b44747ec57b00df15f2385b10c458056a5a))
* **audio:** add speaker_segments key to stub response ([d68fc58](https://github.com/aa-kriti/intelliview-orchestrator/commit/d68fc588bb6de19e2c9b8841d8221ac5618f8b03))
* CI passing, lint clean, professional README, add DATABASE_SSLMODE, fix missing imports ([e5d5325](https://github.com/aa-kriti/intelliview-orchestrator/commit/e5d5325db680d36e143288a415ca15aba19876ea))
* ci startup and git checkout ([044b0ff](https://github.com/aa-kriti/intelliview-orchestrator/commit/044b0ff4626d5d490196f5e4ff94948c0590f8b3))
* **ci:** resolve merge conflicts, update mocks, and add docker build validation ([6d636f8](https://github.com/aa-kriti/intelliview-orchestrator/commit/6d636f8162cfac6718d5bcc444d163c2bad8b97f))
* clean up package dependencies ([695e090](https://github.com/aa-kriti/intelliview-orchestrator/commit/695e090b099073847c2b234e62bdd3ebbcf3e5e0))
* Core UI state sync, auth header interpolation, and Compose health checks ([ab9ff33](https://github.com/aa-kriti/intelliview-orchestrator/commit/ab9ff333feb22d67406f385a632771d1b669cc1a)), closes [#485](https://github.com/aa-kriti/intelliview-orchestrator/issues/485)
* correct chord dispatch in process_interview_session ([0cc9b46](https://github.com/aa-kriti/intelliview-orchestrator/commit/0cc9b465d59fd31dc58d24d6c9eb9c21214784ba))
* correct Flower healthcheck path ([29ae497](https://github.com/aa-kriti/intelliview-orchestrator/commit/29ae497c0bc43a150130678125b76908b7489733))
* correct previous_strategy value in /switch-strategy response ([a3f57a4](https://github.com/aa-kriti/intelliview-orchestrator/commit/a3f57a489695e60576fec218b0986f4f925b1e93))
* create database seed script for development ([#327](https://github.com/aa-kriti/intelliview-orchestrator/issues/327)) ([ab3dc4b](https://github.com/aa-kriti/intelliview-orchestrator/commit/ab3dc4b4a42305d272e986f03a6558d9be0f1dee))
* E2E pipeline, chord-based parallel processing, and CI rate-limit isolation ([51b82e7](https://github.com/aa-kriti/intelliview-orchestrator/commit/51b82e7a8e91496183854999cb9fac7b133ebbda))
* enforce 72-byte limit on passwords for bcrypt and add grafana default password ([60b35b7](https://github.com/aa-kriti/intelliview-orchestrator/commit/60b35b77eb0ed2c8da873537c5a09db27d9f41bb))
* enqueue task payload to Redis fallback in QUEUE_BASED load balancer ([13ee63e](https://github.com/aa-kriti/intelliview-orchestrator/commit/13ee63eb3ce97f63914be5d8d54baaafa1d6d1c9))
* export User model properly in models package ([d24477b](https://github.com/aa-kriti/intelliview-orchestrator/commit/d24477b2566262e34fbaaa027179386092ae2f56))
* fail fast with clear error when required settings are missing ([f8bd393](https://github.com/aa-kriti/intelliview-orchestrator/commit/f8bd3936ad23e7542b1f32f96a290d8b71266f82))
* handle JSONDecodeError in evaluation pipeline with stub fallback ([67ee115](https://github.com/aa-kriti/intelliview-orchestrator/commit/67ee11596d2493516812e947c5e2b0a4f5aab53e))
* ignore worker system status for available checks and relax health monitor ([4bfd7f1](https://github.com/aa-kriti/intelliview-orchestrator/commit/4bfd7f1603277ff87d1644eb487bf6740cd9395a))
* ignore worker system status for available checks and remove stale submodule ([a995ca0](https://github.com/aa-kriti/intelliview-orchestrator/commit/a995ca0af05565861d856d16555732a9392fb523))
* Implement SQLAlchemy ORM relationships ([#171](https://github.com/aa-kriti/intelliview-orchestrator/issues/171)) ([290d49b](https://github.com/aa-kriti/intelliview-orchestrator/commit/290d49be2110db27409251bd35af8bdf3eb04243))
* improve SQLAlchemy session lifecycle management  rajat-wyrm[#103](https://github.com/aa-kriti/intelliview-orchestrator/issues/103) issue ([#449](https://github.com/aa-kriti/intelliview-orchestrator/issues/449)) ([8117b42](https://github.com/aa-kriti/intelliview-orchestrator/commit/8117b42a0446578cd30b01648cc4bf2543e094c3))
* isolate ScreenLock in lazy wrapper to avoid SSR localStorage access ([cce1ec1](https://github.com/aa-kriti/intelliview-orchestrator/commit/cce1ec1d6df474644d980531ba90f45924eb5e34))
* lazy-import heavy deps in conftest so E2E CI job (httpx+pytest only) can collect tests ([0935448](https://github.com/aa-kriti/intelliview-orchestrator/commit/09354487fda4347d5130a48ea060928a2bcbb298))
* load balancer edge cases and disable OTel in tests ([3c6d3c6](https://github.com/aa-kriti/intelliview-orchestrator/commit/3c6d3c6e14e56264b6c172b68f9d32a420425866))
* make startup user creation resilient to bcrypt ValueError ([ef21f04](https://github.com/aa-kriti/intelliview-orchestrator/commit/ef21f04544ae1dd51ca4d853674411702c3c45d1))
* mock lrange payload in fault manager unit test ([ab1cacc](https://github.com/aa-kriti/intelliview-orchestrator/commit/ab1caccf9039f05cccd281cf65690c50fdd86d3b))
* **orchestrator:** implement Redis Pub/Sub cache sync listener with graceful shutdown and unit tests ([#362](https://github.com/aa-kriti/intelliview-orchestrator/issues/362)) ([7766e5d](https://github.com/aa-kriti/intelliview-orchestrator/commit/7766e5d91fad01bc42c0e033b88afa2ce160c1db))
* prevent duplicate Celery subtask execution on retry ([88a75c0](https://github.com/aa-kriti/intelliview-orchestrator/commit/88a75c07ffdbcacd2574d219f09cf5bb974fe05c))
* redis fragmentation with lint fixes ([#394](https://github.com/aa-kriti/intelliview-orchestrator/issues/394)) ([d562498](https://github.com/aa-kriti/intelliview-orchestrator/commit/d56249806bcf4202883469da068e334f69339732))
* remove duplicate headers argument ([ff43c64](https://github.com/aa-kriti/intelliview-orchestrator/commit/ff43c640dc5e558b931945943a0c53d447b79c0f))
* remove duplicate session_db parameter ([0a5ff5d](https://github.com/aa-kriti/intelliview-orchestrator/commit/0a5ff5df88eaaefe38a25febf92fc313c3d82348))
* remove duplicated function definition in fault manager tests ([f4e5d26](https://github.com/aa-kriti/intelliview-orchestrator/commit/f4e5d266a06f41e8677db94a4b8545e5b492233f))
* remove invalid eslint-disable comment for unconfigured react-hooks/exhaustive-deps rule ([71a8870](https://github.com/aa-kriti/intelliview-orchestrator/commit/71a8870c21702f415d86926ba60b97fc4b736eea))
* remove nested repo from tracking ([3058ec8](https://github.com/aa-kriti/intelliview-orchestrator/commit/3058ec849a2e8d864941e6fd7c3ca60b69781768))
* remove trailing whitespace ([1f84d70](https://github.com/aa-kriti/intelliview-orchestrator/commit/1f84d70f3d5b311dd9776386c475badc8d8be95d))
* remove trailing whitespace in main.py ([01c5baf](https://github.com/aa-kriti/intelliview-orchestrator/commit/01c5bafe45657de2177d0b4f7d1a37ca345edf3f))
* remove unused imports flagged by ruff (F401) in main.py and video_pipeline.py ([37ac004](https://github.com/aa-kriti/intelliview-orchestrator/commit/37ac0047ac65457b7c98a83fc36f822f9ba20cf7))
* replace datetime.utcnow with timezone-aware UTC datetime ([3d5901d](https://github.com/aa-kriti/intelliview-orchestrator/commit/3d5901df520eae8ca26bebe2fd2db43e967b21a2))
* resolve conflicts in worker registry test ([067d34d](https://github.com/aa-kriti/intelliview-orchestrator/commit/067d34df9471c9f8b1097a80b4864d5d21c5dd0a))
* resolve failing orchestration tests ([397c9b0](https://github.com/aa-kriti/intelliview-orchestrator/commit/397c9b0929d3123b423584c1c7fa020677aba789))
* resolve git merge conflict in worker registry tests ([80f8d9a](https://github.com/aa-kriti/intelliview-orchestrator/commit/80f8d9a5948cfd1d70c979476947b2858478501f))
* resolve merge conflicts in worker registry tests ([7342e64](https://github.com/aa-kriti/intelliview-orchestrator/commit/7342e645a11f88b939999d155e6f700f9024ea0c))
* resolve Next.js lint warning in useDebounce hook ([64f4750](https://github.com/aa-kriti/intelliview-orchestrator/commit/64f47506a1e23be2f7cfa4aea89e2fc06515cf89))
* resolve permission errors in CI for app cache ([6b1ac77](https://github.com/aa-kriti/intelliview-orchestrator/commit/6b1ac7714786bf8518a8124662346b5412fbf978))
* resolve Python tests CI lint/format failures ([605487c](https://github.com/aa-kriti/intelliview-orchestrator/commit/605487c25eded869796d26f29a8910af52d63449))
* resolve remaining Ruff lint issue ([de616e2](https://github.com/aa-kriti/intelliview-orchestrator/commit/de616e2cab79db9f0c2d61c7f98d5969d2c4e849))
* resolve ruff format failures in health_monitor and audio_pipeline ([751d1bf](https://github.com/aa-kriti/intelliview-orchestrator/commit/751d1bf34087f5de4e256e3de8d9b87fcde659c1))
* resolve ruff lint errors (E402, F821, W291) ([93f457d](https://github.com/aa-kriti/intelliview-orchestrator/commit/93f457d1afd408fca31d33fcb61e1799f29e7597))
* resolve ruff lint issues (unused import, missing newlines) ([e96993f](https://github.com/aa-kriti/intelliview-orchestrator/commit/e96993fd509e4e243d684fba56f0cd9030d797c2))
* resolve ruff linter CI failures ([62f79e8](https://github.com/aa-kriti/intelliview-orchestrator/commit/62f79e8c73d08617943a9f21e5691da0a5ee3eb3))
* resolve undefined variable ([b3b23be](https://github.com/aa-kriti/intelliview-orchestrator/commit/b3b23be4c147c802de49335ab7d98ef8f8cd4c23))
* resolve workflow syntax, ruff linting, and docker compose flags ([daa1b56](https://github.com/aa-kriti/intelliview-orchestrator/commit/daa1b569bd8f8155a544529812374160cadf555b))
* restore Dockerfile contents for CI build ([cb6122b](https://github.com/aa-kriti/intelliview-orchestrator/commit/cb6122be322fba34f6b91499f8c2ba9bd9de0408))
* ScreenLock import error - use lazy default import with wrapper ([83f580f](https://github.com/aa-kriti/intelliview-orchestrator/commit/83f580fbe9522e5bd4a6bba9a861b2603e20a6d0))
* sqlite db path, audio pipeline None handling, and test token bug ([f496a8d](https://github.com/aa-kriti/intelliview-orchestrator/commit/f496a8d8ae9f54051b216a32c152870bab26d758))
* update package-lock.json and repair test mocks for refactored redis_client ([f260a2f](https://github.com/aa-kriti/intelliview-orchestrator/commit/f260a2f55fe35b4795e1ca786a3048f24431337f))
* Update test tokens to match CI environment variable ([41ce1c2](https://github.com/aa-kriti/intelliview-orchestrator/commit/41ce1c2abdd03bc715db9115a20630d3ab5d811d))
* use reported active tasks in heartbeat ([007a373](https://github.com/aa-kriti/intelliview-orchestrator/commit/007a3735249055d3491a66a238da548ed2e2ed4f))
* validate audio file before whisper transcription ([#446](https://github.com/aa-kriti/intelliview-orchestrator/issues/446)) ([b0408ec](https://github.com/aa-kriti/intelliview-orchestrator/commit/b0408ec26ea9ec8c92dded8849a0e40556efceb1))
* **worker:** enforce solo pool for active task tracking ([20215be](https://github.com/aa-kriti/intelliview-orchestrator/commit/20215becaf02fd4cba73ebb164a2741f9f3bfe33))
* **workers:** resolve double-dispatch and performance issue in scan_and_dispatch_retries ([97de1e0](https://github.com/aa-kriti/intelliview-orchestrator/commit/97de1e0c1f9b3b4fba3c17ea6f2764c5c3644ff8))

### Code Refactoring

* extract shared utils and clean up helper functions ([a4dd1ff](https://github.com/aa-kriti/intelliview-orchestrator/commit/a4dd1fff2c08b2bd44121b6b7334498e0ee1f4ad))
* remove all dead code - 15 items across 16 files ([4cb8a4a](https://github.com/aa-kriti/intelliview-orchestrator/commit/4cb8a4a10de849e5dfb17036bc1e491bf09a9162))
* replace inline styles with Tailwind utility classes ([3ff8125](https://github.com/aa-kriti/intelliview-orchestrator/commit/3ff81259a059bea8fabe46097e743acd5f46ffd8))
* split database/models.py into database/models/ package ([#545](https://github.com/aa-kriti/intelliview-orchestrator/issues/545)) ([#554](https://github.com/aa-kriti/intelliview-orchestrator/issues/554)) ([090b625](https://github.com/aa-kriti/intelliview-orchestrator/commit/090b625500c92bfedc612ddd9d0616b46c065aad))
* split orchestrator routes into dedicated routers ([31114d1](https://github.com/aa-kriti/intelliview-orchestrator/commit/31114d15201e9d05cb008cc753f798d6a4fe7d57))

### Documentation

* add README for Celery worker file ([f63f27f](https://github.com/aa-kriti/intelliview-orchestrator/commit/f63f27ffe399edc549c00caeb49ce1bcacea70db))
* add reusable prompt template library for interview workflows ([d8df940](https://github.com/aa-kriti/intelliview-orchestrator/commit/d8df940b34976d5fd63101a780205b89b4857248))
* add role-based prompt template library for AI agents ([3860b8c](https://github.com/aa-kriti/intelliview-orchestrator/commit/3860b8cbb15b91f83daba2f14d263ad89a429295))
* complete task 10.1 documentation ([b38dc25](https://github.com/aa-kriti/intelliview-orchestrator/commit/b38dc25767d164cf14156bdcb074358b2e00e919))
* improve documentation for idempotency key generation ([5e29e36](https://github.com/aa-kriti/intelliview-orchestrator/commit/5e29e360edd206125c63526db2c5c332870627a7))
* restore CONTRIBUTING.md to match main ([a8d19f0](https://github.com/aa-kriti/intelliview-orchestrator/commit/a8d19f0b488a0cc0c31a2154d88f6e27bb6a0aec))
* update PR template details ([dd706bc](https://github.com/aa-kriti/intelliview-orchestrator/commit/dd706bc54328ffe2b191de3bfe6c56350641aec9))
* update quick start instructions and remove obsolete frontend development steps in README ([fe430be](https://github.com/aa-kriti/intelliview-orchestrator/commit/fe430beca123d23ac4e2171505d14aa2dacfb66e))
* update README with new features (screen lock, moment tracking, AI integration) ([a4378d4](https://github.com/aa-kriti/intelliview-orchestrator/commit/a4378d49b793fcb51bbb45b9749f7ed963988b39))
* verified skeleton loader implementation ([ccfa001](https://github.com/aa-kriti/intelliview-orchestrator/commit/ccfa001194ae86ea15b34b2e53d4f3485979dc60))

### Chores

* configure semantic-release workflow ([2bc37e9](https://github.com/aa-kriti/intelliview-orchestrator/commit/2bc37e9d2aeb2d7cf2a6f30f26cc4c592ab786eb))
* increase start_period for health check in docker-compose to 30s ([5dddebb](https://github.com/aa-kriti/intelliview-orchestrator/commit/5dddebb19a83ebe29bf454f60d5a809012055184))
* remove unrelated changes from Issue [#39](https://github.com/aa-kriti/intelliview-orchestrator/issues/39) PR ([a971809](https://github.com/aa-kriti/intelliview-orchestrator/commit/a971809387714d50cfed2d2bff5556b250ef7d75))
* update .env.example with new settings (AI keys, screen lock, real-time) ([8747d7e](https://github.com/aa-kriti/intelliview-orchestrator/commit/8747d7e02f9f105ca282da55c79d7fcee6240472))
* update frontend environment variable and healthcheck configuration in docker-compose ([0eede90](https://github.com/aa-kriti/intelliview-orchestrator/commit/0eede90084b5824cabfb73c9583407212354bb7d))

### Tests

* add load balancer fairness simulation ([d02f93b](https://github.com/aa-kriti/intelliview-orchestrator/commit/d02f93b61b7f9bac7c57877abc056df2e2689268))
* add test coverage for interview report API and update docs ([f8e48fa](https://github.com/aa-kriti/intelliview-orchestrator/commit/f8e48fae897e711b21a59338cb237df478022d26))
* add unit test coverage for load balancing strategies ([fe7567b](https://github.com/aa-kriti/intelliview-orchestrator/commit/fe7567b951206507155cf09cf96f3d9f5ce76100))
* add unit tests for core orchestrator modules ([a9200c1](https://github.com/aa-kriti/intelliview-orchestrator/commit/a9200c1435a895c333344f00dd104f6a5022f60f))
* add unit tests for SQLAlchemy models ([76726dc](https://github.com/aa-kriti/intelliview-orchestrator/commit/76726dcbbb6d69303d26021bd4540eb02e892919))
* **hr-dashboard:** add unit tests for dashboard components (HR-12) ([046f0a6](https://github.com/aa-kriti/intelliview-orchestrator/commit/046f0a6d35a7e7b502fb9ebef5ba21ca4359d87b))
* migrate integration tests to PostgreSQL Testcontainers ([7e60967](https://github.com/aa-kriti/intelliview-orchestrator/commit/7e609677151a4377c7d3aa3cc0842e44c92a0960))
* migrate integration tests to PostgreSQL Testcontainers ([9ec9508](https://github.com/aa-kriti/intelliview-orchestrator/commit/9ec9508dfb910e52abdb5e9b1e33766b8ac7bb2f))
* patch get_redis_client in unit tests ([ef54e14](https://github.com/aa-kriti/intelliview-orchestrator/commit/ef54e145279259e028711eb87a9f242e2e1552b4))
* update Redis client mocks ([669cb84](https://github.com/aa-kriti/intelliview-orchestrator/commit/669cb849c4467e3568d38cd69b5063da02f71290))

# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Production hardening: `pool_pre_ping` + `pool_recycle` on the SQLAlchemy
  engine so connections survive Postgres restarts.
- Graceful lifespan shutdown that closes Redis-backed resources.
- Auth on previously open privileged endpoints:
  `/start-interview`, `/switch-strategy`, `/retry-session/{id}`,
  `/detect-failures`.
- Scheduler rollback: if Celery dispatch fails, the worker active-task
  counter is decremented back.
- `RiskScoringEngine` and AI pipelines (`video`, `audio`, `evaluation`)
  now produce deterministic per-session signals so risk classification
  thresholds actually fire in dev/test.
- Frontend: skip-to-content link, focus trap + `aria-modal` on `Dialog`,
  `prefers-reduced-motion` support via `useReducedMotion`.
- Frontend: per-route `loading.tsx`, `error.tsx`, `not-found.tsx`.
- Frontend: analytics Risk Distribution pie now reads
  `/completed-sessions` and buckets real risk scores (no more hardcoded
  zeros).
- `Dockerfile` now runs as non-root, declares `HEALTHCHECK`, and a
  matching `.dockerignore` keeps secrets and build artefacts out of
  the image.
- CI: `ruff format --check`, `mypy` (best-effort), and a production
  `next build` step.
- Unit tests for `WorkerRegistry`, `RetryManager`, `FaultManager`, and
  the AI pipeline stubs (27 new tests, 91 total).
- Documentation: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CHANGELOG.md`.

- Hallucination detection module using semantic similarity + NLI entailment,
  integrated into the evaluation pipeline and risk scoring engine (#67)

### Changed
- Removed dead `workers/worker.py` (replaced by `worker_entrypoint.py`).
- Removed duplicate `logging.basicConfig` that appended a handler on
  every `main.py` import.
- Lifespan now logs a loud warning when the default `API_TOKEN` is in
  use.
- README rewritten to reflect the actual production-grade surface area.

### Fixed
- `RiskScoringEngine` was always returning 0.0 because pipelines returned
  empty booleans; now produces a non-trivial per-session signal.

## [0.2.0] - 2026-06-21

### Added
- Structured JSON logging (`JSON_LOGGING` env flag) and `log_event` helper.
- Request-ID middleware (`X-Request-ID` echo + response-time header).
- SQLAlchemy 2.0 migration of all read paths (`select()` syntax).
- Frontend: command palette (`cmdk`), mobile sidebar, session-detail
  modal with live polling, search input, SVG illustrations,
  shimmer skeleton, theme toggle, keyboard-shortcut help dialog.
- Prometheus-style hooks in `MetricsCollector` (no `/metrics` endpoint
  yet — pending).

### Changed
- Tightened `StartInterviewRequest` validation (regex, length,
  whitelist priority).
- API token now checked on worker-management routes.

### Fixed
- Bare `except` clauses wrapped with logging and narrowed exception
  types.

## [0.1.0] - 2026-06-01

- Initial release: FastAPI orchestrator, Celery workers, Redis
  state cache, Postgres source of truth, Next.js dashboard.
