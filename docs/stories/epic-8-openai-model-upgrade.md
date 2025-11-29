# Epic 8: OpenAI Model Upgrade to GPT-5.1

**Status:** In Progress  
**Epic Owner:** Development Team  
**Target Version:** 2.0  
**Business Value:** High  
**Technical Risk:** Medium

---

## Epic Overview

Upgrade the JobSearchAI application to support OpenAI's GPT-5.1 model, which introduces significant architectural improvements including reasoning capabilities, verbosity controls, and enhanced performance. This upgrade will improve the quality of generated content (CVs, motivation letters, LinkedIn messages) while optimizing costs through better token management and caching.

---

## Business Goals

1. **Improved Content Quality:** Leverage GPT-5.1's enhanced reasoning for better job matching, CV tailoring, and networking messages
2. **Cost Optimization:** Utilize new caching features (90% discount on cached inputs) to reduce API costs
3. **Performance Flexibility:** Enable fast mode for simple tasks and reasoning mode for complex analysis
4. **Future-Proofing:** Adopt latest OpenAI standards to ensure long-term compatibility

---

## Technical Goals

1. Implement backward-compatible OpenAI client supporting both GPT-4 and GPT-5.1
2. Migrate from deprecated `system` role to new `developer` role for reasoning models
3. Implement `reasoning_effort` parameter for variable intelligence/speed tradeoff
4. Implement `verbosity` controls for output length management
5. Update token parameter handling (`max_tokens` → `max_completion_tokens`)
6. Add support for reasoning token tracking and cost monitoring

---

## Scope

### In Scope

- Update `utils/api_utils.py` to support GPT-5.1 parameters
- Migrate all OpenAI API calls to new parameter schema
- Add configuration options for model selection and reasoning levels
- Implement token usage tracking for reasoning models
- Update all services using OpenAI (CV, motivation letter, LinkedIn generators)
- Documentation updates for new capabilities

### Out of Scope

- Complete rewrite of existing prompt engineering
- Migration away from Flask framework
- UI redesign for new features
- Advanced tool usage (shell, apply_patch) - Phase 2

---

## Stories

1. **Story 8.1:** Core OpenAI Manager Implementation *(This Story)*
   - Update `utils/api_utils.py` with GPT-5.1 support
   - Implement backward compatibility layer
   - Add configuration management

2. **Story 8.2:** Service Integration and Migration *(Future)*
   - Update all service modules to use new API
   - Migrate prompts to `developer` role
   - Add reasoning mode selection per use case

3. **Story 8.3:** Monitoring and Optimization *(Future)*
   - Implement token usage tracking
   - Add cost monitoring dashboard
   - Optimize caching strategies

---

## Success Criteria

- [ ] All existing OpenAI features work with GPT-5.1
- [ ] No regression in content quality
- [ ] Token usage tracking implemented
- [ ] Configuration allows easy model switching
- [ ] All tests pass with both GPT-4 and GPT-5.1
- [ ] Documentation complete for new features
- [ ] Cost per API call reduced by 10-30% through caching

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes in existing prompts | High | Medium | Implement backward compatibility, thorough testing |
| Increased API costs during transition | Medium | Low | Monitor token usage, implement gradual rollout |
| Reasoning mode performance overhead | Medium | Medium | Use `reasoning_effort="none"` for latency-sensitive tasks |
| Model availability/rate limits | High | Low | Maintain GPT-4 fallback configuration |

---

## Dependencies

- OpenAI Python SDK >= 1.55.0
- Existing utils/api_utils.py module
- All service modules using OpenAI
- config.py for model configuration

---

## Notes

- GPT-5.1 introduces a new pricing model with caching benefits
- `system` role is deprecated for reasoning models
- Token parameter naming has changed
- Reasoning tokens are billed but hidden from output
- Full migration can be gradual - modules can be updated independently
