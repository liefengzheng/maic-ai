# Domain Glossary

## Tenant

An isolated organization or workspace. Every User belongs to exactly one Tenant. Agent definitions and capabilities owned by one Tenant are invisible and unavailable to every other Tenant.

## User

An authenticated person belonging to exactly one Tenant. A Tenant may contain multiple Users. A User has either the Admin or User role.

## Admin

A User responsible for managing Agent and SuperAgent definitions within their Tenant.

## Agent

An independently executable specialist created and owned by an Admin within a Tenant. An Agent may use zero or more Tools and zero or more MCP Servers owned by the same Tenant. It is private to its owner by default and may be shared with all Users in that Tenant.

## SuperAgent

A coordinating agent created and owned by an Admin within a Tenant and composed of one or more Agents from that Tenant. It is private by default and may be shared with its Tenant. A SuperAgent cannot directly contain another SuperAgent.

## Tool

A locally implemented capability that can be assigned to multiple Agents within its Tenant.

## MCP Server

An external capability provider using the Model Context Protocol. It can be assigned to multiple Agents within its Tenant.
