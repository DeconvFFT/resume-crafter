# Resume Crafter: Skill-Based Improvements Design

**Date:** 2026-01-27
**Status:** In Progress

## Overview

This document outlines improvements identified using the following installed skills from skills.sh:
- vercel-react-best-practices (57 rules for React/Next.js optimization)
- web-design-guidelines (UI/UX and accessibility)
- nextjs-server-client-components (Server/Client component patterns)
- vercel-composition-patterns (Component architecture)

---

## Phase 1: High Priority - Performance & Architecture

### 1.1 React Performance Optimizations

#### Bundle Size Reduction
- [ ] Dynamic imports for ReactFlow/workflow components (~150KB savings)
- [ ] Optimize lucide-react imports (direct imports vs barrel)

#### Parallel Data Fetching
- [ ] Dashboard: Create `/api/dashboard/stats` endpoint to consolidate 7 API calls
- [ ] Login flow: Return user data from login endpoint directly

#### Memoization
- [ ] Add useMemo for experience skills deduplication (O(n^2) to O(n))

### 1.2 Next.js Server/Client Component Patterns

#### Add Suspense Boundaries
- [ ] Add `app/error.tsx` for error boundaries
- [ ] Add Suspense wrapper in `app/layout.tsx`

#### Server-Side Data Fetching
- [ ] Convert pages to hybrid pattern: server component fetches, client component renders
- [ ] Affected pages: documents, experiences, projects, skills, publications, jobs, resume

### 1.3 Backend Performance

#### Parallel Database Queries
- [ ] `resume_generator.py`: Use asyncio.gather for 4 sequential queries
- [ ] `automation.py` stats endpoint: Parallelize 8+ count queries

#### Pagination
- [ ] Add pagination to: `/matches`, `/jobs`, `/experiences`, `/projects`, `/documents`, `/publications`

---

## Phase 2: Medium Priority - Code Quality

### 2.1 Frontend Improvements

#### Shared Components
- [ ] Create `StatusBadge` component (duplicated in 3+ files)
- [ ] Create `PageSkeleton` component for consistent loading states

#### Composition Patterns
- [ ] Refactor `ExperienceCard` to compound component
- [ ] Create `useDialogForm` hook for reusable dialog/form state

### 2.2 Backend Improvements

#### Code Deduplication
- [ ] Extract `get_arq_redis()` to shared dependency
- [ ] Create generic `get_owned_entity()` helper
- [ ] Create `soft_delete()` utility function

#### Error Handling
- [ ] Standardize error handling with decorator pattern
- [ ] Add RetryableError vs PermanentError distinction

---

## Phase 3: Accessibility & UX

### 3.1 Accessibility Improvements
- [ ] Add skip navigation link to dashboard layout
- [ ] Add aria-live regions for dynamic content (processing status)
- [ ] Improve color contrast in status badges

### 3.2 UX Consistency
- [ ] Standardize loading states across pages
- [ ] Add focus management for command palette

---

## Implementation Order

1. **Error Boundaries** (prevents app crashes)
2. **Suspense Boundaries** (required for streaming)
3. **Dynamic Imports** (largest bundle impact)
4. **Parallel Queries** (largest performance impact)
5. **Shared Components** (reduces duplication)
6. **Accessibility** (compliance)

---

## Files to Modify

### Frontend Critical
- `app/layout.tsx` - Add Suspense
- `app/error.tsx` - Create error boundary
- `app/automations/[id]/page.tsx` - Dynamic import ReactFlow
- `components/ui/status-badge.tsx` - Create shared component

### Backend Critical
- `src/core/resume_generator.py` - Parallel queries
- `src/api/routes/automation.py` - Parallel stats queries
- `src/core/dependencies.py` - Create shared ARQ dependency

---

## Verification Checklist

- [ ] All pages have error boundaries
- [ ] Bundle size reduced by dynamic imports
- [ ] Dashboard loads faster with consolidated API
- [ ] Accessibility audit passes
- [ ] No console errors in production
