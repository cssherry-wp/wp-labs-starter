---
alwaysApply: false
globs: '*.sql'
description: Enterprise-level SQL coding guidelines for schema design, security, and best practices
---

# Enterprise SQL Guidelines

## Naming Conventions

### Tables
- **Always use plural names**: `users`, `projects`, `organizations`, `products`
- Use lowercase with underscores for multi-word tables: `user_preferences`, `api_tokens`
- Never use singular table names: `user`, `project`

### Columns
- Use descriptive, lowercase names with underscores: `created_at`, `email_address`, `last_login_time`
- Boolean columns should use `is_`, `has_`, or `can_` prefixes: `is_active`, `has_verified_email`, `can_edit`
- Timestamp columns should use `_at` suffix: `created_at`, `updated_at`, `deleted_at`

### Foreign Keys
- **Use singular table name + `_id`**: `user_id`, `project_id`, `organization_id`
- Always name the foreign key constraint: `fk_projects_user_id` (format: `fk_<table>_<column>`)
- Add indexes on foreign key columns for performance: `idx_projects_user_id`

Example:
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    CONSTRAINT fk_projects_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_projects_user_id ON projects(user_id);
```

### Join Tables
- **Use plural names for both tables**: `organizations_users`, `projects_tags`, `roles_permissions`
- Order alphabetically when no natural hierarchy exists
- Include composite primary key on both foreign keys
- Always add foreign key constraints and indexes

Example:
```sql
CREATE TABLE organizations_users (
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (organization_id, user_id),
    CONSTRAINT fk_organizations_users_org_id FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_organizations_users_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_organizations_users_user_id ON organizations_users(user_id);
CREATE INDEX idx_organizations_users_org_id ON organizations_users(organization_id);
```

## Index Strategy
- Always index foreign key columns
- Create composite indexes for frequently used column combinations
- Add partial indexes with WHERE clauses for filtered queries
- Index columns used in ORDER BY and GROUP BY operations

## Primary Key Strategy: UUID vs Integer

### Use UUIDs When:
- Distributed systems (multiple databases, sharding)
- Need globally unique identifiers
- Want to prevent ID enumeration attacks
- Merging data from multiple sources
- Public-facing IDs in URLs

### Use Auto-Incrementing Integers When:
- Single database instance
- Need better performance for joins (integers are faster than UUIDs)
- Storage size matters (UUIDs are 16 bytes vs 4/8 bytes for integers)

### Hybrid Approach
Use integer primary key for performance, add UUID for external references:

```sql
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    public_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    CONSTRAINT fk_orders_user_id FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_orders_public_id ON orders(public_id);
```

## SQL Injection Prevention

- **NEVER** concatenate user input directly into SQL statements
- **ALWAYS** use parameterized queries with placeholders ($1, $2, ?, etc.)
- **ALWAYS** validate dynamic table/column names against a whitelist
- For PostgreSQL dynamic identifiers, use `format()` with `%I`

## Additional Best Practices

### Use Constraints for Data Integrity
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL,
    CONSTRAINT chk_orders_status CHECK (status IN ('pending', 'processing', 'completed', 'cancelled')),
    CONSTRAINT chk_orders_amount CHECK (total_amount >= 0)
);
```

### Transaction Guidelines
- Use transactions for multi-step operations
- Keep transactions short to avoid lock contention

```sql
BEGIN;
    UPDATE accounts SET balance = balance - 100 WHERE id = $1;
    UPDATE accounts SET balance = balance + 100 WHERE id = $2;
COMMIT;
```
