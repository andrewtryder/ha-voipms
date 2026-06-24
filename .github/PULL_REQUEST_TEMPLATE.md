## Summary

<!-- Describe the change and what problem it solves. -->

## Related issues

<!-- Link to any related issues, e.g., Closes #123, Relates to #456. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Repository governance / CI / chore

## Quality checklist

- [ ] Code builds/starts without errors
- [ ] Lint and format checks pass
- [ ] Tests pass (existing and new)
- [ ] Documentation updated (README, ADRs, etc.)
- [ ] PR title follows Conventional Commits (`feat:`, `fix:`, `chore:`, etc.)

## Standards sync checklist

- [ ] If docs changed, I checked whether `ai/rules/*.md` or downstream `.rulesync/rules/*.md` also needs an update.
- [ ] If AI rule source changed, I ran `npx rulesync generate` where generated outputs are committed.
- [ ] I did not hand-edit generated AI/editor outputs as the source of truth.
- [ ] `.repo-policy.yml` remains consistent with docs, templates, and AI rules.
- [ ] If docs changed without AI rule changes, the PR explains why no AI behavior changed.
