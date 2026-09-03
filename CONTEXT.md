# Domain Glossary

## User

An authenticated person. A User has either the Admin or User role.

## Admin

A User responsible for managing the global Skill, Agent, and SuperAgent catalog.

## Agent

An independently executable specialist created by an Admin. An Agent may use zero or more Skills from the global catalog. Enabled Agents are available to all Users.

## SuperAgent

A coordinating agent created by an Admin and composed of one or more global Agents. An enabled SuperAgent is available to all Users and cannot directly contain another SuperAgent.

## Skill

A locally implemented capability from the global catalog that can be assigned to multiple Agents. Its metadata and input schema are stored in the catalog, while its execution logic is loaded from the runtime Skills directory.
