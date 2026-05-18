from __future__ import annotations

from collections import defaultdict

MODE_SELECTORS = {
	"All": ":root",
	"Light": ':root[data-desk-theme-mode="light"], body[data-desk-theme-mode="light"]',
	"Dark": ':root[data-desk-theme-mode="dark"], body[data-desk-theme-mode="dark"]',
}

MEDIA_QUERIES = {
	"Desktop": "@media (min-width: 992px)",
	"Tablet": "@media (min-width: 768px) and (max-width: 991.98px)",
	"Mobile": "@media (max-width: 767.98px)",
}


def compile_theme_css(theme_doc) -> str:
	tokens_by_scope = defaultdict(lambda: defaultdict(dict))

	for token in getattr(theme_doc, "tokens", []) or []:
		token_name = (token.token_name or "").strip()
		token_value = (token.token_value or "").strip()
		mode_scope = (getattr(token, "mode_scope", None) or "All").strip() or "All"
		device_scope = (token.device_scope or "All").strip() or "All"

		if not token_name or not token_value:
			continue

		tokens_by_scope[mode_scope][device_scope][token_name] = token_value

	css_blocks = []
	for mode_scope, device_tokens in tokens_by_scope.items():
		selector = MODE_SELECTORS.get(mode_scope, MODE_SELECTORS["All"])
		for device_scope, tokens in device_tokens.items():
			if not tokens:
				continue

			block = _format_css_block(selector, tokens)
			if device_scope == "All":
				css_blocks.append(block)
				continue

			media_query = MEDIA_QUERIES.get(device_scope)
			if media_query:
				css_blocks.append(f"{media_query} {{\n{_indent(block)}\n}}")

	if getattr(theme_doc, "allow_custom_css", 0) and getattr(theme_doc, "custom_css", None):
		css_blocks.append(theme_doc.custom_css.strip())

	return "\n\n".join(block for block in css_blocks if block).strip()


def _format_css_block(selector: str, tokens: dict[str, str]) -> str:
	lines = [f"{selector} {{"]
	for token_name in sorted(tokens):
		lines.append(f"  {token_name}: {tokens[token_name]};")
	lines.append("}")
	return "\n".join(lines)


def _indent(block: str) -> str:
	return "\n".join(f"  {line}" for line in block.splitlines())
