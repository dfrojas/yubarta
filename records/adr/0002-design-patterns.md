# 2. Design Patterns

Date: 2025-04-01

## Status

Superceded by [3. Capability-aligned architecture](0003-capability-aligned-architecture.md)

## Context

Since this is a personal hobby project, I wanted to explore the different design patterns out there to understand how it works.

In a real world scenario, the reason would be because is needed to establish a clear and maintainable architecture for the Yubarta project that promotes:

- Clear separation of concerns
- Modularity and extensibility
- Testability
- Code organization that reflects business domains
- Easy integration of new features and providers

The project requires a structure that can accommodate growth while maintaining code quality and developer productivity.

## Decision

I have decided to implement a hybrid architectural approach combining:

1. Domain-Driven Design (DDD)
   - Core business logic will be organized in domain-specific modules under `yubarta/core`
   - Use of dataclasses for domain/model classes
   - Clear boundaries between different domains

2. Hexagonal Architecture (Ports and Adapters)
   - Adapters will be placed in `yubarta/drivers`
   - Interfaces in `yubarta/entrypoints`
   - Application logic in `yubarta/controllers`
   - Shared code in `yubarta/common`

3. Plugin Architecture
   - Used for extending functionality through providers
   - Allows for easy integration of new features
   - Promotes loose coupling between components

4. Database Mapping
   - Classical SQLAlchemy mapping for domain/model classes
   - Consistent approach for all new domain/model additions

## Consequences

### Positive
- Clear organization of code based on business domains
- Easier testing due to clear boundaries and dependency inversion
- Flexibility to add new providers without modifying existing code
- Better maintainability through separation of concerns
- Reduced coupling between different parts of the system
- Consistent patterns make the codebase more predictable

### Negative
- Initial overhead in setting up the architecture
- Learning curve for new developers to understand the patterns
- Need for careful consideration before implementing complex patterns
- More boilerplate code compared to simpler architectures

### Mitigations
- Documentation of patterns and their proper usage
- Code reviews to ensure adherence to patterns
- Regular evaluation of pattern effectiveness
- Training for team members on the chosen patterns
- Consider revert the decision and implement another structure.
