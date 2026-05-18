(() => {
  const GLOBAL_STYLE_ID = "crm-desk-theme-global";
  const OVERRIDE_STYLE_ID = "crm-desk-theme-overrides";
  const BODY_THEME_ATTR = "data-desk-theme";
  const BODY_ROUTE_ATTR = "data-desk-theme-route";
  const MODE_ATTR = "data-desk-theme-mode";
  const app = window.frappe;

  if (!app?.boot?.desk_theme_manager) {
    return;
  }

  const payload = app.boot.desk_theme_manager;
  const theme = payload.theme;
  if (!theme) {
    return;
  }

  let subscribed = false;
  let subscribeAttempts = 0;

  function ensureStyleTag(id) {
    let tag = document.getElementById(id);
    if (!tag) {
      tag = document.createElement("style");
      tag.id = id;
      document.head.appendChild(tag);
    }

    return tag;
  }

  function slugify(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function resolveActiveMode() {
    if (payload.active_mode === "Light" || payload.active_mode === "Dark") {
      return payload.active_mode.toLowerCase();
    }

    if (theme.default_mode === "Dark") {
      return "dark";
    }

    if (theme.default_mode === "Follow System" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    return "light";
  }

  function isThemeApplicableForMode(activeMode) {
    switch (theme.mode_strategy) {
      case "Shared":
        return true;
      case "Light Only":
        return activeMode === "light";
      case "Dark Only":
        return activeMode === "dark";
      case "Light and Dark":
        return activeMode === "light" || activeMode === "dark";
      default:
        return true;
    }
  }

  function getRouteParts() {
    const route =
      typeof app.get_route === "function"
        ? app.get_route()
        : app.router?.current_route || [];

    const routeParts = Array.isArray(route) ? route : [];
    return routeParts.filter(Boolean).map((part) => decodeURIComponent(String(part)));
  }

  function getRouteString(parts) {
    return `/app/${parts.map((part) => encodeURIComponent(part)).join("/")}`.replace(/\/+$/, "");
  }

  function getViewType(parts) {
    const lastPart = (parts[parts.length - 1] || "").toLowerCase();
    const firstPart = (parts[0] || "").toLowerCase();
    const lowerParts = parts.map((part) => String(part).toLowerCase());

    if (!parts.length) {
      return "Workspace";
    }

    if (firstPart === "query-report" || firstPart === "report") {
      return "Report";
    }

    if (lowerParts.includes("view")) {
      const viewIndex = lowerParts.indexOf("view");
      const viewName = (parts[viewIndex + 1] || "").toLowerCase();
      if (viewName === "list") {
        return "List";
      }

      if (viewName === "report") {
        return "Report";
      }

      if (viewName) {
        return viewName.charAt(0).toUpperCase() + viewName.slice(1);
      }
    }

    if (parts.length >= 2 && lastPart !== "view") {
      return "Form";
    }

    return "Workspace";
  }

  function getDoctype(parts, viewType) {
    if (!parts.length) {
      return "";
    }

    if (viewType === "Report") {
      return parts[1] || "";
    }

    if (viewType === "Workspace") {
      return "";
    }

    return parts[0] || "";
  }

  function matchesRule(rule, context) {
    if (!rule?.enabled) {
      return false;
    }

    if (rule.mode_scope && rule.mode_scope !== "All" && rule.mode_scope.toLowerCase() !== context.activeMode) {
      return false;
    }

    const matchValue = String(rule.match_value || "").trim();
    if (!matchValue) {
      return false;
    }

    switch (rule.match_type) {
      case "Exact Route":
        return context.routeString === normaliseRouteValue(matchValue);
      case "Route Prefix":
        return context.routeString.startsWith(normaliseRouteValue(matchValue));
      case "Workspace":
        return (
          context.viewType === "Workspace" &&
          slugify(context.workspace) === slugify(matchValue)
        );
      case "View Type":
        return context.viewType.toLowerCase() === matchValue.toLowerCase();
      case "Doctype":
        return context.doctype.toLowerCase() === matchValue.toLowerCase();
      case "Role":
        return context.roles.some((role) => role.toLowerCase() === matchValue.toLowerCase());
      default:
        return false;
    }
  }

  function normaliseRouteValue(routeValue) {
    if (routeValue.startsWith("/app")) {
      return routeValue.replace(/\/+$/, "");
    }

    return `/app/${routeValue.replace(/^\/+/, "").replace(/\/+$/, "")}`;
  }

  function buildOverrideCss(ruleSet, activeMode) {
    const overrideTokens = {};
    const cssChunks = [];

    ruleSet.forEach((rule) => {
      if (
        rule.theme_override_mode === "Override Tokens" &&
        rule.override_tokens &&
        typeof rule.override_tokens === "object"
      ) {
        Object.assign(overrideTokens, rule.override_tokens);
      }

      if (rule.theme_override_mode === "Inject CSS" && rule.override_css) {
        cssChunks.push(rule.override_css);
      }
    });

    const tokenLines = Object.entries(overrideTokens).map(
      ([tokenName, tokenValue]) => `  ${tokenName}: ${tokenValue};`
    );

    if (tokenLines.length) {
      cssChunks.unshift(
        `:root[${MODE_ATTR}="${activeMode}"], body[${MODE_ATTR}="${activeMode}"] {\n${tokenLines.join("\n")}\n}`
      );
    }

    return cssChunks.join("\n\n").trim();
  }

  function applyRouteOverrides() {
    const routeParts = getRouteParts();
    const viewType = getViewType(routeParts);
    const routeString = getRouteString(routeParts);
    const activeMode = resolveActiveMode();
    const context = {
      routeString,
      routeParts,
      viewType,
      doctype: getDoctype(routeParts, viewType),
      workspace: routeParts[0] || "",
      roles: app.boot.user?.roles || app.user_roles || [],
      activeMode,
    };

    const matchingRules = (payload.rules || [])
      .filter((rule) => matchesRule(rule, context))
      .sort((left, right) => (left.priority || 100) - (right.priority || 100));

    ensureStyleTag(OVERRIDE_STYLE_ID).textContent = buildOverrideCss(matchingRules, activeMode);

    document.documentElement.setAttribute(MODE_ATTR, activeMode);
    const themeIsApplicable = isThemeApplicableForMode(activeMode);
    if (document.body) {
      if (themeIsApplicable) {
        document.body.setAttribute(BODY_THEME_ATTR, slugify(theme.theme_name || theme.name));
        document.body.setAttribute(BODY_ROUTE_ATTR, routeString);
      } else {
        document.body.removeAttribute(BODY_THEME_ATTR);
        document.body.removeAttribute(BODY_ROUTE_ATTR);
      }
      document.body.setAttribute(MODE_ATTR, activeMode);
    }
  }

  function subscribeRouteChanges() {
    if (subscribed) {
      return;
    }

    if (app.router?.on) {
      app.router.on("change", applyRouteOverrides);
      subscribed = true;
      return;
    }

    if (subscribeAttempts >= 20) {
      return;
    }

    subscribeAttempts += 1;
    window.setTimeout(subscribeRouteChanges, 250);
  }

  function init() {
    ensureStyleTag(GLOBAL_STYLE_ID).textContent = theme.generated_css || "";
    applyRouteOverrides();
    subscribeRouteChanges();

    if (window.matchMedia && theme.default_mode === "Follow System") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const listener = () => applyRouteOverrides();
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener("change", listener);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(listener);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
