# Peogram - QA Testing Framework

## Why This Project Exists

I built this because I got tired of manually testing the same scenarios over and over. We were losing about 15-20% of bugs in production that should've been caught earlier, and honestly? It was painful watching the support team deal with stuff we could've found in testing.

Started as a side project to automate our most repetitive checks, and it actually saved us from shipping a critical payment flow bug last quarter. That's when I knew it was worth polishing.

## What It Does

Peogram is a lightweight testing framework designed to catch common issues without being a pain to maintain. It focuses on:

- **Smoke testing** - The quick "did I break the obvious stuff?" checks
- **Data validation** - Making sure the garbage in/garbage out principle doesn't bite us
- **Integration testing** - Catching those weird edge cases where one service breaks because another changed
- **Performance baselines** - Tracking when things got slower (even slightly)

## The Problem I Was Solving

Our testing pipeline was a mess. We had:
- Tests scattered across 3 different frameworks (nightmare for maintenance)
- 40% flaky tests that would pass/fail randomly
- Average test run time of 45 minutes (nobody wants to wait that long)
- Onboarding new team members took forever because the setup was undocumented

After implementing Peogram:
- **Test suite time**: 45min → 8min (parallel execution + better test design)
- **Flakiness**: 40% → 3% (better waits, reduced race conditions)
- **Maintenance**: One framework, clear patterns, reduced technical debt
- **Coverage**: Went from ~55% to ~78% in the first month

## How to Use It

### Quick Start

```bash
git clone https://github.com/chen2022001901-ship-it/peogram.git
cd peogram
npm install
npm test
```

### Running Specific Test Suites

```bash
npm run test:smoke       # Quick sanity checks (~2 min)
npm run test:integration # Full integration tests (~5 min)
npm run test:performance # Performance regression checks
```

## What I Learned the Hard Way

**1. Flaky tests are worse than no tests**
Our original suite had ~100 tests, but 40 of them were unreliable. Developers stopped trusting the results, and nobody would investigate real failures. Spent two weeks removing sleeps and fixing race conditions. The payoff: tests developers actually trust.

**2. Test data matters more than you think**
We were using production data seeds for testing, which meant:
- Tests broke when production data changed
- Couldn't test edge cases safely
- New team members had no idea what the test data represented

Now we have clean, isolated fixtures. Tests run the same way every time.

**3. Documentation in code > Documentation in files**
I learned this lesson twice. Wrote great test docs that nobody read. Then I focused on:
- Clear test names that describe the scenario, not just the function
- Helper methods with obvious purposes
- Comments explaining the "why" not the "what"
- Real usage examples in test files

**4. Performance testing needs baseline data**
We started monitoring performance when we noticed things felt slow. By then, we couldn't tell if we broke something or if it was always that way. Now we baseline every release.

## Current Test Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| Auth Flow | 87% | ✓ Stable |
| Data Processing | 82% | ✓ Stable |
| API Integration | 91% | ✓ Stable |
| UI Components | 64% | ⚠ In Progress |
| Payment Module | 95% | ✓ Critical (High Attention) |

## Known Limitations

- **Browser testing**: Currently focused on headless/API testing. If you need Selenium stuff, I'd recommend Cypress for now.
- **Mobile**: Not covering native mobile apps yet, only mobile web.
- **Load testing**: This is functional testing. For heavy load scenarios, you'd want something like k6 or JMeter.
- **Visual regression**: Not implemented yet. We use Percy for that separately.

## Real Issues I've Hit

**Memory leaks in test database connections**: Our integration tests were creating connections but not cleaning up properly. Added a cleanup hook, reduced flakiness by 80%. Simple fix, took way too long to debug.

**Timezone-related test failures**: Tests passed locally but failed in CI because of timezone differences. Not fun discovering that at 2 AM. Now everything uses UTC and we test against multiple zones.

**Test interdependencies**: Had tests that would only fail if run in a certain order. Refactored to make each test truly independent. Lesson: if your test only fails when test X runs before it, you have a problem.

## Future Plans

- **Better HTML reporting** - Current reports are functional but ugly
- **CI/CD integration examples** - Adding templates for GitHub Actions and GitLab CI
- **Database snapshot/restore** - Making integration test setup faster
- **API contract testing** - Catching breaking changes earlier
- **Visual diff testing** - Starting with critical user paths

## Contributing

If you're thinking about contributing, here's what helps most:
- Bug reports with reproduction steps (seriously, I'll prioritize these)
- Tests for edge cases you've encountered
- Improvements to test performance
- Better documentation/examples

I'm not picky about code style if the PR has good intent. That said, I will ask for tests to be added if you change core functionality.

## The Honest Truth

This isn't perfect. It won't catch every bug (nothing will). But it catches the common stuff that would've broken production, and it's fast enough that people actually run it before committing.

The real win? Our support team is handling 30% fewer "this shouldn't have shipped" tickets. That's what matters.

---

**Built by someone who spent too many late nights fixing bugs that tests should've caught.**
