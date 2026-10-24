# Production Playbook: React + Spring Boot 3 + PostgreSQL
*End-to-End Enterprise Full-Stack Blueprint with AI Assistance*
*Version: 2026.1 · Curated by DevCity Engineering*

---

## Architecture Overview
- **Frontend:** React 19, TypeScript, Vite, TanStack Query, Tailwind CSS, Lucide Icons.
- **Backend:** Java 21, Spring Boot 3.3+, Spring Data JPA, Spring Security (JWT), Bean Validation.
- **Database:** PostgreSQL 16+, Flyway Migrations, Testcontainers for integration tests.
- **Deployment:** Docker Multi-stage, Docker Compose, GitHub Actions CI/CD.

---

## Step 1: System Spec & Domain Model
- **Goal:** Define entities, relationships, REST API endpoints, and OpenAPI 3.1 specification before writing code.
- **AI Tool & Model:** Claude Code or Antigravity · **Claude 3.7 Sonnet** (High reasoning, strict schema adherence).
- **Why:** Drafting complete OpenAPI contracts and JSON schemas upfront prevents frontend/backend schema mismatch and eliminates hours of rework.
- **Prompt Template:**
  ```text
  You are a Principal Software Architect. Design an OpenAPI 3.1 specification and domain model for a [DESCRIBE FEATURE, e.g. Customer Invoicing Platform].
  Requirements:
  1. Define PostgreSQL entities: [Entities, e.g. Organization, Customer, Invoice, InvoiceItem, Payment].
  2. Include field types, non-null constraints, and foreign key relationships.
  3. Define RESTful endpoints with HTTP verbs, path variables, request bodies, and error response schemas (400, 401, 404, 409, 500).
  4. Ensure pagination parameters (page, size, sort) follow Spring Pageable conventions.
  Output clean OpenAPI 3.1 YAML and an Entity Relationship Summary.
  ```
- **Review Checklist:**
  - [ ] Are primary keys UUID or BigSerial consistently?
  - [ ] Are all audit fields present (`created_at`, `updated_at`, `created_by`)?
  - [ ] Are unique constraints defined for tenant-scoped identifiers?
- **Common Mistakes:** AI tends to skip cascade rules or forgets to document 409 Conflict error schemas for unique key violations.

---

## Step 2: Database Schema & Flyway Migrations
- **Goal:** Author versioned, idempotent SQL migrations with appropriate indexes and foreign keys.
- **AI Tool & Model:** Claude Code · **Claude 3.7 Sonnet**.
- **Why:** SQL errors in production are catastrophic. AI should author the DDL, but strict review gates must verify indexing and rollback strategies.
- **Prompt Template:**
  ```text
  Generate a Flyway migration script (V1__init_schema.sql) for PostgreSQL 16 based on the domain spec.
  Rules:
  1. Use `TIMESTAMPTZ` for all timestamps (never `TIMESTAMP` without timezone).
  2. Add foreign keys with `ON DELETE RESTRICT` by default unless cascade delete is explicitly requested.
  3. Add B-tree indexes for all foreign key columns and frequently filtered columns.
  4. Write a corresponding rollback or down-migration verification script.
  5. Use snake_case for all tables and column names.
  ```
- **Review Checklist:**
  - [ ] No `DROP TABLE` or destructive unindexed `ALTER TABLE` statements.
  - [ ] Indexes exist on all foreign key columns to prevent table locks during joins.
  - [ ] Constraints have explicit names (e.g. `fk_invoice_customer_id`).
- **Common Mistakes:** Missing indexes on foreign keys; using naive `VARCHAR(255)` for IDs instead of UUID or appropriate constraints.

---

## Step 3: Spring Boot 3 Backend Service & JPA Entities
- **Goal:** Implement JPA entities, Spring Data repositories, DTO records, service layer, and REST controllers.
- **AI Tool & Model:** Claude Code · **Claude 3.7 Sonnet**.
- **Why:** Claude Code excels at following enterprise Java conventions (immutable Java 21 Records for DTOs, Bean Validation, and MapStruct/manual mappers).
- **Prompt Template:**
  ```text
  Implement the backend service for [FEATURE] in Spring Boot 3.3 / Java 21.
  Follow clean architecture principles:
  1. JPA Entity classes with `@Table(name = "...")` and `@Column` mappings. Use Lombok only for getters/setters or standard Java 21 records for DTOs.
  2. Spring Data JPA Repository extending `JpaRepository` and `JpaSpecificationExecutor`.
  3. Service interface and `@Service` implementation wrapped in `@Transactional(readOnly = true)` with `@Transactional` on mutation methods.
  4. REST Controller with `@RestController`, `@RequestMapping`, `@Valid` annotations, and ResponseEntity return types.
  5. Global Exception Handler (`@RestControllerAdvice`) handling `MethodArgumentNotValidException` and domain exceptions.
  ```
- **Review Checklist:**
  - [ ] Are entities using `@EqualsAndHashCode(onlyExplicitlyIncluded = true)` on ID to prevent N+1 issues?
  - [ ] Are DTOs separated from JPA entities to prevent accidental over-posting?
  - [ ] Are transaction boundaries properly declared?
- **Common Mistakes:** Exposing JPA entities directly in `@RestController` endpoints; missing `@Transactional` on mutating service methods.

---

## Step 4: React 19 Frontend Components & API Integration
- **Goal:** Build responsive, accessible UI components with TanStack Query (React Query) for stateful server data.
- **AI Tool & Model:** Cursor or Claude Code · **Claude 3.7 Sonnet**.
- **Why:** Sonnet handles TypeScript types, TanStack Query mutation hooks, and Tailwind styling cleanly without inventing obsolete React patterns.
- **Prompt Template:**
  ```text
  Build a React 19 TypeScript view for [FEATURE, e.g. Invoice Dashboard and Creation Form].
  Requirements:
  1. Use TanStack Query (useQuery, useMutation) for fetching and mutating API data with cache invalidation.
  2. Build accessible forms with React Hook Form + Zod schema validation matching backend constraints.
  3. Style with Tailwind CSS. Support mobile (390x844) and desktop (1280x720) viewports cleanly.
  4. Add loading skeletons, error states, and empty state illustrations.
  5. Use Lucide-React icons and proper ARIA labels on all interactive buttons.
  ```
- **Review Checklist:**
  - [ ] Are query keys structured deterministically (e.g. `['invoices', { customerId }]`)?
  - [ ] Does form validation match the backend Bean Validation constraints exactly?
  - [ ] Is loading and error handling handled gracefully without page flickers?
- **Common Mistakes:** Omitting error states or failing to invalidate queries after successful mutations.

---

## Step 5: Unit & Integration Testing (Testcontainers & Vitest)
- **Goal:** Write isolated unit tests and full integration tests against real PostgreSQL using Testcontainers.
- **AI Tool & Model:** Claude Code · **Claude 3.7 Sonnet**.
- **Why:** Real database integration tests catch subtle SQL syntax, foreign key, and transaction rollback issues before staging.
- **Prompt Template:**
  ```text
  Author comprehensive tests for [FEATURE]:
  1. Spring Boot Integration Test using `@SpringBootTest` and Testcontainers (`@Container static PostgreSQLContainer`).
  2. Test happy path, validation errors (400), not found (404), and conflict (409).
  3. Frontend unit tests using Vitest + React Testing Library testing form submission, loading state, and error toast.
  ```
- **Review Checklist:**
  - [ ] Does Testcontainers use a lightweight PostgreSQL image (`postgres:16-alpine`)?
  - [ ] Are mock dependencies minimized in integration tests to test real queries?
  - [ ] Do frontend tests query by accessible role (`getByRole('button', { name: ... })`)?
- **Common Mistakes:** Using H2 in-memory database instead of real PostgreSQL Testcontainers (H2 behaves differently with SQL syntax and timestamps).

---

## Step 6: Security, Auth & Input Validation
- **Goal:** Harden endpoints with JWT token validation, role-based access control, CORS, and sanitization.
- **AI Tool & Model:** Claude Code · **Claude 3.7 Sonnet**.
- **Why:** Security requires precision; AI should author standard Spring Security 6 filter chains and CORS configs with strict origin whitelisting.
- **Prompt Template:**
  ```text
  Configure Spring Security 6 for JWT-based stateless authentication.
  Requirements:
  1. SecurityFilterChain bean configuring CORS with explicit allowed origins from application.yml.
  2. CSRF disabled for stateless JWT REST endpoints.
  3. SessionCreationPolicy.STATELESS.
  4. Method security enabled (`@EnableMethodSecurity`).
  5. JWT AuthenticationFilter extracting Bearer token and setting SecurityContextHolder.
  ```
- **Review Checklist:**
  - [ ] Are passwords hashed with BCrypt (strength $\ge 12$)?
  - [ ] Is CORS configured with explicit allowed origins (never `*` with credentials enabled)?
  - [ ] Are sensitive tokens/secrets loaded from environment variables, never hardcoded?
- **Common Mistakes:** Enabling wildcard CORS with credentials; using deprecated `WebSecurityConfigurerAdapter`.

---

## Step 7: CI/CD Pipeline (GitHub Actions)
- **Goal:** Automate build, lint, test, security scanning, and container packaging on every pull request.
- **AI Tool & Model:** Claude Code · **Claude 3.5 Haiku / Sonnet**.
- **Why:** Haiku generates standard YAML workflow syntax with speed and low cost.
- **Prompt Template:**
  ```text
  Author a GitHub Actions workflow `.github/workflows/ci.yml`.
  Steps:
  1. Checkout code with caching for Maven/Gradle and npm dependencies.
  2. Set up JDK 21 and Node 20.
  3. Run backend tests with Docker service container for PostgreSQL.
  4. Run frontend lint, typecheck (`tsc --noEmit`), and Vitest.
  5. Build Docker container image without publishing on PRs.
  ```
- **Review Checklist:**
  - [ ] Are GitHub Action dependencies pinned to full commit SHA or trusted major tags?
  - [ ] Does the workflow fail immediately if typecheck or tests fail?
  - [ ] Is dependency caching configured to keep CI runs under 4 minutes?
- **Common Mistakes:** Forgetting to start Docker service in GitHub Actions for Testcontainers.

---

## Step 8: Multi-Stage Containerization & Deployment
- **Goal:** Build minimal, secure, non-root Docker images and local Docker Compose orchestration.
- **AI Tool & Model:** Claude Code · **Claude 3.5 Haiku / Sonnet**.
- **Why:** Multi-stage builds reduce container attack surface and image size by ~85%.
- **Prompt Template:**
  ```text
  Write production Dockerfiles and a `docker-compose.yml`:
  1. Backend Dockerfile: Multi-stage build with Eclipse Temurin 21-jre-alpine, non-root user `spring:spring`, and layered JAR extraction.
  2. Frontend Dockerfile: Multi-stage build with Node build step and Nginx Alpine runtime serving static assets.
  3. `docker-compose.yml` linking frontend, backend, and postgres with health checks and volume persistence.
  ```
- **Review Checklist:**
  - [ ] Does backend container run as non-root user (`USER spring`)?
  - [ ] Is `.dockerignore` present in both projects to avoid copying node_modules or target/?
  - [ ] Are environment variables documented in `.env.example`?
- **Common Mistakes:** Running containers as root; including `.git` or build artifacts in image context.

---

## Step 9: Observability, Health Checks & Audit
- **Goal:** Expose Spring Actuator health/metrics, Prometheus endpoints, and client-side error telemetry.
- **AI Tool & Model:** Claude Code · **Claude 3.5 Haiku**.
- **Why:** Observability endpoints enable zero-downtime rolling deploys and rapid root-cause analysis.
- **Prompt Template:**
  ```text
  Configure Spring Boot Actuator:
  1. Enable `/actuator/health` with `show-details: when_authorized`.
  2. Enable `/actuator/prometheus` for metrics scraping.
  3. Implement a custom HealthIndicator checking PostgreSQL query response time.
  ```
- **Review Checklist:**
  - [ ] Are sensitive Actuator endpoints (`env`, `heapdump`, `beans`) protected or disabled?
  - [ ] Is database health check verified during container startup?
