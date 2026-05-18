# Desk Theme App Specification

## Goal

Build a Frappe app that allows administrators and managers to customize the Desk UI under `/app` without patching Frappe core.

The app should support:

- non-technical users who want visual controls
- semi-technical users who want reusable presets and page rules
- technical users who want custom CSS and controlled JS injection

The app should treat Desk theming as a runtime configuration layer, not as static asset replacement.

## Problem Framing

Frappe provides theme support mainly for the website layer. Desk customization is limited and not designed for:

- brand-level theming of the app shell
- route-specific appearance changes
- tenant-specific UI token management
- controlled injection of custom CSS/JS for Desk

Desk is a SPA, so page-level theming cannot rely on full page reloads. Theme application must respond to route changes inside the client runtime.

## Product Scope

### In Scope

- global Desk theme tokens
- light and dark mode theme variants
- route/page-specific theme overrides
- role-based theme assignment
- workspace-specific theme assignment
- non-technical visual editor for common properties
- advanced CSS editor for trusted admins
- optional controlled JS hooks for trusted admins
- theme preview, draft, publish, rollback
- import/export of theme configs
- audit trail for theme changes

### Out of Scope for V1

- arbitrary DOM builder / drag-and-drop layout editor
- full component-level editor for every Frappe widget
- per-user visual builder for standard users
- support for modifying Frappe core templates directly
- unrestricted third-party script embedding for all admins

## User Levels

### Level 1: Non-Technical Admin

Needs a safe UI with form fields and pickers.

Capabilities:

- choose colors
- manage separate light and dark palettes when needed
- choose fonts from an allowlist
- change top bar, sidebar, content background, borders, links, headings
- set logo and favicon if needed later
- select from presets
- preview before publish

### Level 2: Power User / Manager

Needs rule-based targeting without writing much code.

Capabilities:

- assign themes by workspace
- assign themes by page type
- assign themes by role
- define overrides for list, form, report, workspace
- enable compact variants like "minimal sidebar" or "soft borders"

### Level 3: Technical Admin

Needs escape hatches.

Capabilities:

- inject scoped CSS
- inject controlled JS modules
- target selectors or route patterns
- define custom CSS variables
- use theme lifecycle hooks such as `on_route_change`

## Customization Model

Use a layered model instead of one giant CSS blob.

### Layer 1: Design Tokens

Global variables mapped to CSS custom properties.

Tokens should support a mode scope so a theme can define:

- shared tokens used in all modes
- light-only token values
- dark-only token values

Examples:

- `--cdt-topbar-bg`
- `--cdt-sidebar-bg`
- `--cdt-text-color`
- `--cdt-heading-color`
- `--cdt-border-color`
- `--cdt-scrollbar-thumb`
- `--cdt-scrollbar-track`
- `--cdt-link-color`
- `--cdt-primary-accent`
- `--cdt-content-bg`

This layer should cover 80 percent of use cases.

Mode should be modeled as a first-class theme dimension, not as ad hoc custom CSS.

### Layer 2: Semantic Areas

Map tokens to Desk areas:

- app shell
- top navbar
- sidebar
- workspace cards
- page header
- forms
- list views
- reports
- dialogs
- badges / pills
- buttons
- tabs
- scrollbar

This gives non-technical users meaningful controls without selector knowledge.

### Layer 3: Route Overrides

Override a subset of tokens or CSS for specific contexts:

- active mode: `Light` or `Dark`
- route pattern: `/app`
- route pattern: `/app/<workspace>`
- form pages
- list pages
- query reports
- specific doctypes

Example rules:

- workspace "Sales" gets a dark sidebar
- all form pages get higher border contrast
- report pages get denser table styling
- dark mode uses softer borders and lower glare backgrounds

### Layer 4: Advanced CSS

Trusted admin can add scoped CSS that is appended after generated token CSS.

Rules:

- store separately from token configuration
- warn when using raw selectors
- support optional route scoping
- disallow this for low-privilege users

### Layer 5: Controlled JS Extensions

JS should be optional and tightly controlled.

Allowed use cases:

- add route-aware body classes
- toggle layout behaviors
- attach lightweight visual behaviors
- initialize approved UI enhancements

Not allowed by default:

- arbitrary external script URLs
- code that bypasses permissions
- code that mutates business logic in standard doctypes

## Recommended Feature Set

### V1 Core

- Theme doctype
- Theme preset support
- Global token editor
- Light / dark mode support
- Workspace/page override rules
- Live preview mode
- Publish / unpublish
- Role-based assignment
- Generated CSS variable injection
- Route change listener on Desk

### V1.1 Practical Enhancements

- Import/export JSON
- Theme history and rollback
- Draft vs published versions
- CSS linting and selector warning
- Mobile-specific overrides

### V2 Advanced

- JS extension registry
- Theme conditions by user role and company
- Scheduled theme activation
- A/B or seasonal campaigns
- Theme analytics such as active theme usage

## Suggested Data Model

Use separate doctypes for stability and clarity.

### 1. Desk Theme

Main document representing a theme.

Fields:

- `theme_name`
- `enabled`
- `is_default`
- `status` (`Draft`, `Published`, `Archived`)
- `description`
- `base_preset`
- `mode_strategy` (`Single`, `Light Only`, `Dark Only`, `Dual`)
- `default_mode` (`Light`, `Dark`, `System`)
- `allow_custom_css`
- `allow_custom_js`
- `custom_css`
- `custom_js`
- `generated_css`
- `version`

### 2. Desk Theme Token

Child table or JSON field for design tokens.

Fields:

- `token_name`
- `token_value`
- `mode_scope` (`All`, `Light`, `Dark`)
- `device_scope` (`All`, `Desktop`, `Tablet`, `Mobile`)

### 3. Desk Theme Rule

Route and context overrides.

Fields:

- `priority`
- `enabled`
- `match_type` (`Workspace`, `Route Prefix`, `Exact Route`, `View Type`, `Doctype`, `Role`)
- `match_value`
- `mode_scope` (`All`, `Light`, `Dark`)
- `override_tokens`
- `override_css`

### 4. Desk Theme Assignment

Optional explicit assignment table.

Fields:

- `assignment_type` (`Global`, `Role`, `User`, `Company`)
- `reference`
- `theme`
- `priority`

### 5. Desk Theme Revision

Immutable revision history.

Fields:

- `theme`
- `revision_no`
- `snapshot_json`
- `published_by`
- `published_on`

## How It Should Work

## Server Side

### Hooks

Use these Frappe hooks:

- `app_include_js` to load the Desk theming runtime
- `app_include_css` for a minimal base stylesheet
- `extend_bootinfo` or `boot_session` to send active theme config to Desk

`extend_bootinfo` is preferable for attaching a structured theme payload to boot info.

### Theme Resolution

At session boot, compute an `active_theme_context`:

- default published theme
- assignments based on role/user/company
- active mode preference and allowed mode strategy
- allowed advanced features for the current user

Send to `bootinfo`, for example:

```json
{
  "desk_theme_manager": {
    "active_mode": "Dark",
    "theme": {...},
    "rules": [...],
    "permissions": {
      "can_use_custom_css": true,
      "can_use_custom_js": false
    }
  }
}
```

### Generation Strategy

Do not generate a static CSS file per request.

Instead:

1. store theme config as structured data
2. compile token maps into CSS text on save/publish with mode-aware outputs
3. ship compiled CSS in boot payload or fetch through a cached endpoint
4. inject or update a `<style>` tag on the client

This avoids rebuild complexity and allows live switching.

## Client Side

### Runtime Loader

Global JS loaded via `app_include_js` should:

1. read `frappe.boot.desk_theme_manager`
2. resolve active mode from theme config, system preference, and any user toggle
3. inject root CSS variables into `document.documentElement`
4. inject generated CSS in a dedicated style tag
5. subscribe to `frappe.router.on("change", ...)`
6. evaluate matching theme rules on each route change
7. update body classes and override tokens/CSS dynamically

The runtime should set explicit body or root attributes such as:

- `data-desk-theme-mode="light"`
- `data-desk-theme-mode="dark"`

This gives both generated CSS and advanced CSS a stable selector contract.

### Mode Resolution

Mode selection should be deterministic.

Recommended priority:

1. explicit user toggle inside Desk Theme controls
2. theme `default_mode`
3. browser or OS `prefers-color-scheme` when theme mode is `System`
4. fallback to `Light`

Mode changes should not require a page reload.

### Route Detection

Because Desk is SPA-based, use route-aware resolution.

Useful route dimensions:

- current route array from `frappe.router.current_route`
- route subpath
- view type like `Workspaces`, `Form`, `List`, `Report`
- doctype for form/list/report pages

### Preview Flow

For theme editing:

1. open a Desk Theme form/page
2. user changes token values
3. client regenerates preview CSS immediately for the current mode
4. preview applies only for that session until publish
5. publish creates a revision and marks compiled theme active

## Page Targeting Strategy

Support targeting in a structured order:

1. global active theme
2. role/user/company assignment override
3. active mode resolution
4. route-specific rules
5. custom CSS for matching rules
6. optional JS enhancement hooks

Priority must be deterministic.

Recommended ordering:

- exact route
- workspace
- doctype + view type
- generic view type
- role
- global

## Security Model

This app can become dangerous if custom JS is unrestricted. Enforce hard boundaries.

### Safe by Default

- visual editor available to System Manager / allowed role
- light and dark variants must be previewable separately before publish
- CSS editor restricted to trusted admins
- JS editor disabled by default
- no external script URLs
- no anonymous runtime eval of server-fetched strings for low-trust modes

### Recommended JS Strategy

Do not store arbitrary executable JS as plain text for general use.

Prefer:

- a registry of approved client modules bundled with the app
- config flags that enable those modules per theme/rule

If you still support raw JS:

- restrict it to `System Manager`
- log every change
- add strong warnings
- make it opt-in via app setting

## UX Design for the App

The app itself should have two operating modes.

### Simple Mode

For non-technical admins.

Sections:

- brand colors
- mode selector: Light, Dark, System
- top bar
- sidebar
- typography
- borders
- cards
- tables
- scrollbar
- buttons

Use:

- color pickers
- spacing sliders where needed
- font dropdowns
- live preview pane

### Advanced Mode

For technical admins.

Sections:

- token JSON
- mode-scoped token editing
- route rules
- custom CSS editor
- JS module toggles
- raw output preview

## Implementation Approach

## Phase 1: Foundations

- create doctypes for themes, rules, revisions
- add hooks for Desk asset loading
- extend boot info with active theme payload
- build client runtime that applies CSS variables globally
- add light and dark mode token resolution

Outcome:

- one published theme can style top bar, sidebar, typography, borders, scrollbar in light and dark modes

## Phase 2: Rule Engine

- add route-aware rule matching
- add workspace and view-specific overrides
- add role-based assignments
- add preview support
- add mode-specific rule overrides

Outcome:

- different pages/workspaces can have different appearances across light and dark modes

## Phase 3: Admin Experience

- build visual theme editor
- add preset templates
- add publish workflow and rollback
- add import/export
- add mode switcher and dual-palette preview

Outcome:

- non-technical users can manage light and dark themes safely

## Phase 4: Advanced Extensions

- add approved JS module registry
- add CSS linting / diagnostics
- add device-specific rules

## Recommended Technical Structure

Suggested package layout:

```text
crm_desk_theme/
  api/
    theme.py
  desk_theming/
    doctype/
      desk_theme/
      desk_theme_rule/
      desk_theme_revision/
  public/
    js/
      desk_theme_runtime.js
      desk_theme_preview.js
    css/
      desk_theme_base.css
  services/
    resolver.py
    compiler.py
    permissions.py
  hooks.py
```

## Rendering Strategy Recommendation

Prefer CSS custom properties plus a thin runtime over heavy DOM patching.

Why:

- easier to keep compatible with Frappe upgrades
- simpler preview behavior
- lower performance overhead
- safer than selector-heavy mutation scripts

Only use DOM-manipulating JS for cases tokens cannot cover.

## Risks

### 1. Frappe Markup Drift

Internal Desk class names can change across versions.

Mitigation:

- center V1 on stable shell selectors
- rely on CSS variables and wrapper classes where possible
- keep selector maps isolated in one file

### 2. Custom CSS Breaking Usability

Bad contrast or hidden elements can make Desk unusable.

Mitigation:

- add preview mode
- add reset-to-default action
- run contrast checks for key text/background pairs

### 3. Arbitrary JS Risk

Custom JS can create security and support issues.

Mitigation:

- default to approved modules only
- restrict raw JS to high-trust users
- version and audit everything

### 4. Performance

Too many rules or DOM scans on route change can slow Desk.

Mitigation:

- precompile rule matchers
- keep runtime stateless and small
- only update styles when active rule set changes

## Recommended MVP

If the goal is to ship fast and prove value, the MVP should be:

- one published global Desk theme
- token-based customization for top bar, sidebar, text, headings, borders, scrollbar
- workspace-specific overrides
- live preview
- publish/rollback
- no raw JS in MVP
- custom CSS only for System Manager

This is the right balance between usefulness and safety.

## Decision Summary

Build this as a configuration-driven theming engine for Desk, not as a one-off CSS injector.

The correct foundation is:

- server-managed theme docs
- boot-delivered theme payload
- global Desk runtime via `app_include_js`
- CSS variable based rendering
- route-aware overrides using `frappe.router.on("change")`

That will support both simple branding use cases and future advanced page-specific theming without patching Frappe core.
