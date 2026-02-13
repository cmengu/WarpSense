# Learning Log

> **Purpose:** Document mistakes to prevent repeating them. Feed lessons to AI tools.  
> **For AI:** Reference with `@LEARNING_LOG.md` when implementing features.  
> **Last Updated:** [DATE] | **Total Entries:** 0

---

## Quick Start

**When something breaks:**
1. Copy entry template below
2. Fill out: Date, What, Why, Fix, Prevention
3. Add to relevant category section

**When implementing features:**
- Search this file first (`Ctrl+F`)
- Reference in prompts: `@LEARNING_LOG.md check for [topic] issues`
- Follow ✅ patterns, avoid ❌ anti-patterns

**For `.cursorrules`:**
```markdown
Before generating code, check LEARNING_LOG.md for:
- Anti-patterns to avoid
- Required patterns for this feature type
- Past incidents in similar code
```

---

## Entry Template

```markdown
### 📅 YYYY-MM-DD — [Short Title]

**Category:** [Auth|Database|API|Frontend|Backend|DevOps|Testing|Performance]  
**Severity:** 🔴 Critical | 🟡 High | 🟢 Medium | ⚪ Low

**What Happened:** [1-2 sentences]

**Impact:** [Users affected, downtime]

**Root Cause:**
- Technical: [Race condition, missing validation, etc.]
- Process: [No review, skipped testing, etc.]
- Knowledge: [Didn't know about X]

**The Fix:**
```language
// ❌ BEFORE
old code

// ✅ AFTER
fixed code
```

**Prevention:**
- ✅ DO: [Pattern to follow]
- ❌ DON'T: [Pattern to avoid]
- [ ] Code review check: [What to verify]
- [ ] Test case: [Scenario to cover]

**AI Guidance:**
```
When implementing [feature type]:
"[Instruction that would prevent this]"
```

**Warning Signs:** [What to watch for]
```

---

## 🔐 Authentication

### 📅 [Date] — [Title]

**Category:** Auth | **Severity:** 🔴

**What Happened:**

**Impact:**

**Root Cause:**
- Technical:
- Process:
- Knowledge:

**The Fix:**
```python
# ❌ BEFORE

# ✅ AFTER
```

**Prevention:**
- ✅ DO:
- ❌ DON'T:

**AI Guidance:**
```
When implementing auth:
"[Instruction]"
```

---

## 💾 Database

### 📅 [Date] — [Title]

**Category:** Database | **Severity:** 🔴

**What Happened:**

**Impact:**

**Root Cause:**
- Technical:
- Process:

**The Fix:**
```sql
-- ❌ BEFORE

-- ✅ AFTER
```

**Prevention:**
- ✅ DO:
- ❌ DON'T:

**AI Guidance:**
```
When creating migrations:
"[Instruction]"
```

---

## 🌐 API Integration

### 📅 [Date] — [Title]

**Category:** API | **Severity:** 🟡

**What Happened:**

**Impact:**

**Root Cause:**
- Technical:

**The Fix:**
```javascript
// ❌ BEFORE

// ✅ AFTER
```

**Prevention:**
- ✅ DO:
- ❌ DON'T:

**AI Guidance:**
```
When integrating APIs:
"[Instruction]"
```

---

## 🎨 Frontend

### 📅 [Date] — [Title]

**Category:** Frontend | **Severity:** 🟢

**What Happened:**

**Root Cause:**
- Technical:

**The Fix:**
```typescript
// ❌ BEFORE

// ✅ AFTER
```

**Prevention:**
- ✅ DO:
- ❌ DON'T:

---

## ⚙️ Backend

### 📅 [Date] — [Title]

**Category:** Backend | **Severity:** 🟡

**What Happened:**

**Root Cause:**
- Technical:

**The Fix:**
```python
# ❌ BEFORE

# ✅ AFTER
```

**Prevention:**
- ✅ DO:
- ❌ DON'T:

---

## 🧪 Testing

### 📅 [Date] — [Title]

**Category:** Testing | **Severity:** 🟢

**What Happened:**

**The Fix:**
```javascript
// ❌ BEFORE

// ✅ AFTER
```

**Prevention:**
- ✅ DO:

---

## 🚀 DevOps

### 📅 [Date] — [Title]

**Category:** DevOps | **Severity:** 🔴

**What Happened:**

**The Fix:**
```yaml
# ❌ BEFORE

# ✅ AFTER
```

**Prevention:**
- ✅ DO:

---

## ⚡ Performance

### 📅 [Date] — [Title]

**Category:** Performance | **Severity:** 🟡

**What Happened:**

**The Fix:**
```python
# ❌ BEFORE

# ✅ AFTER
```

**Prevention:**
- ✅ DO:

---

## Quick Reference: Anti-Patterns

### Authentication
```python
# ❌ NEVER: Skip token expiry validation
payload = jwt.decode(token, SECRET_KEY)

# ✅ ALWAYS: Explicitly validate expiry
payload = jwt.decode(token, SECRET_KEY, verify_exp=True)
```

### Database
```sql
-- ❌ NEVER: Add non-nullable to existing tables
ALTER TABLE users ADD COLUMN field TEXT NOT NULL;

-- ✅ ALWAYS: Add nullable first, backfill later
ALTER TABLE users ADD COLUMN field TEXT DEFAULT '';
```

### External APIs
```javascript
// ❌ NEVER: No retry logic
const result = await externalAPI.call(data);

// ✅ ALWAYS: Exponential backoff
const result = await retryWithBackoff(() => externalAPI.call(data));
```

### Frontend State
```typescript
// ❌ NEVER: Mutate state directly
state.items.push(newItem);

// ✅ ALWAYS: Create new reference
setState({ ...state, items: [...state.items, newItem] });
```

---

## AI Prompting Patterns

### Auth Implementation
```
Implement JWT validation that:
1. Verifies expiry explicitly (see LEARNING_LOG.md entry [date])
2. Validates signature with SECRET_KEY
3. Extracts user_id from token, never request
4. Handles ExpiredSignatureError, InvalidTokenError
5. Logs failures with context (user_id, IP, timestamp)
```

### Database Migrations
```
Create migration for [field] on [table]:
1. Handle existing data (assume 500k+ rows)
2. Use nullable + default value approach
3. Include rollback SQL in comments
4. Test on production-sized dataset
```

### API Integration
```
Integrate [API] with:
1. Exponential backoff (tenacity library)
2. Circuit breaker (pybreaker)
3. Timeout (5s default, 30s max)
4. Response caching where appropriate
5. Quota monitoring with alerts
```

---

## Code Review Checklist

**General:**
- [ ] Checked LEARNING_LOG.md for this feature area
- [ ] No documented anti-patterns used
- [ ] Error handling for known failure modes
- [ ] Tests cover scenarios from learning log

**Auth:**
- [ ] Token expiry validated?
- [ ] User ID from token, not request?
- [ ] Errors logged with context?

**Database:**
- [ ] New columns nullable initially?
- [ ] Migration tested on large dataset?
- [ ] Indexes on foreign keys?

**APIs:**
- [ ] Retry logic with backoff?
- [ ] Circuit breaker implemented?
- [ ] Timeout configured?

**Frontend:**
- [ ] No state mutations?
- [ ] Error boundaries present?
- [ ] Loading states handled?

**Testing:**
- [ ] Error paths tested?
- [ ] Edge cases from log covered?

---

## Incident Metrics

| Month | Total | Repeat | New | Avg Resolution |
|-------|-------|--------|-----|----------------|
| [Month] | - | - | - | - |

**Goals:**
- Repeat issues <10% of total
- 50% faster resolution over 6 months
- Increase prevention rate

---

## Monthly Review

**Date:** [YYYY-MM]

**This Month:**
- [Issue 1] — [Category] — [Severity]
- [Issue 2] — [Category] — [Severity]

**Patterns:**
- [Pattern]: [X] occurrences

**Actions:**
- [ ] Add linter rule for [pattern]
- [ ] Update .cursorrules
- [ ] Team training on [topic]

**Working Well:**
- [Success]

**Needs Improvement:**
- [Challenge]

**Next Month Focus:**
- [Priority]

---

## Maintenance

**Daily:** Add entries when fixing bugs (5 min)  
**Weekly:** Review with team, update .cursorrules  
**Monthly:** Analyze trends, update checklist

---

## Related Docs

| File | Purpose |
|------|---------|
| `CONTEXT.md` | What exists, patterns |
| `.cursorrules` | AI configuration |
| `README.md` | Project setup |

---

**Remember:** Every mistake documented is future productivity gained. Start small, be consistent. 🚀