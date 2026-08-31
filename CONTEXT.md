# Domain Glossary

## User

An authenticated person. A User has either the Admin or User role.

## Admin

A User responsible for managing the global Tool, MCP Server, Agent, and SuperAgent catalog.

## Agent

An independently executable specialist created by an Admin. An Agent may use zero or more Tools and zero or more MCP Servers from the global catalog. Enabled Agents are available to all Users.

## SuperAgent

A coordinating agent created by an Admin and composed of one or more global Agents. An enabled SuperAgent is available to all Users and cannot directly contain another SuperAgent.

## Tool

A locally implemented capability from the global catalog that can be assigned to multiple Agents.

## MCP Server

An external capability provider using the Model Context Protocol. It is part of the global catalog and can be assigned to multiple Agents.
