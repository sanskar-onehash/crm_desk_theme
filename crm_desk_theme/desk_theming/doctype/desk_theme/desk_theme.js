const VISUAL_FIELDS = [
	"topbar_bg",
	"sidebar_bg",
	"content_bg",
	"card_bg",
	"text_color",
	"heading_color",
	"border_color",
	"link_color",
	"primary_accent",
	"button_bg",
	"button_text_color",
	"scrollbar_thumb",
	"scrollbar_track",
	"font_family",
	"radius_md",
	"dark_topbar_bg",
	"dark_sidebar_bg",
	"dark_content_bg",
	"dark_card_bg",
	"dark_text_color",
	"dark_heading_color",
	"dark_border_color",
	"dark_link_color",
	"dark_primary_accent",
	"dark_button_bg",
	"dark_button_text_color",
	"dark_scrollbar_thumb",
	"dark_scrollbar_track",
	"dark_font_family",
	"dark_radius_md",
	"default_mode",
	"preview_mode",
	"mode_strategy",
];
const DARK_VISUAL_FIELDS = [
	"dark_topbar_bg",
	"dark_sidebar_bg",
	"dark_content_bg",
	"dark_card_bg",
	"dark_text_color",
	"dark_heading_color",
	"dark_border_color",
	"dark_link_color",
	"dark_primary_accent",
	"dark_button_bg",
	"dark_button_text_color",
	"dark_scrollbar_thumb",
	"dark_scrollbar_track",
	"dark_font_family",
	"dark_radius_md",
];

frappe.ui.form.on("Desk Theme", {
	refresh(frm) {
		frm.events.add_action_buttons(frm);
		frm.events.toggle_editor_sections(frm);
	},

	editor_mode(frm) {
		frm.events.toggle_editor_sections(frm);
	},

	async mode_strategy(frm) {
		await frm.events.normalize_shared_mode_fields(frm);
		frm.events.toggle_editor_sections(frm);
	},

	add_action_buttons(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.add_custom_button(__("Preview Theme"), () => frm.events.preview_theme(frm));
		frm.add_custom_button(__("Clear Preview"), () => frm.events.clear_preview(frm));
		frm.add_custom_button(__("Export Snapshot"), () => frm.events.export_snapshot(frm), __("Actions"));
		frm.add_custom_button(__("Import Snapshot"), () => frm.events.import_snapshot(frm), __("Actions"));
		frm.add_custom_button(__("Rollback"), () => frm.events.rollback_theme(frm), __("Actions"));

		if (frm.doc.status !== "Published") {
			frm.add_custom_button(__("Publish"), () => frm.events.publish_theme(frm), __("Actions"));
		}
	},

	async preview_theme(frm) {
		await frm.events.render_preview(frm, true);
	},

	clear_preview(frm) {
		const tag = document.getElementById("crm-desk-theme-form-preview");
		if (tag) {
			tag.remove();
		}

		if (document.body?.getAttribute("data-desk-theme") === "preview") {
			document.body.removeAttribute("data-desk-theme");
		}
		document.body?.removeAttribute("data-desk-theme-mode");
		document.documentElement?.removeAttribute("data-desk-theme-mode");

		frappe.show_alert({ message: __("Preview cleared"), indicator: "blue" });
	},

	async publish_theme(frm) {
		if (frm.is_dirty()) {
			await frm.save();
		}

		await frappe.call({
			method: "crm_desk_theme.api.theme.publish_theme",
			args: { name: frm.doc.name },
			freeze: true,
			freeze_message: __("Publishing theme"),
		});

		await frm.reload_doc();
		frappe.show_alert({ message: __("Theme published"), indicator: "green" });
	},

	async export_snapshot(frm) {
		const response = await frappe.call({
			method: "crm_desk_theme.api.theme.export_theme",
			args: { name: frm.doc.name },
		});

		const dialog = new frappe.ui.Dialog({
			title: __("Theme Snapshot"),
			fields: [
				{
					fieldname: "snapshot_json",
					fieldtype: "Code",
					label: __("Snapshot JSON"),
					options: "JSON",
					read_only: 1,
				},
			],
			primary_action_label: __("Close"),
			primary_action() {
				dialog.hide();
			},
		});

		dialog.set_value("snapshot_json", response.message?.snapshot_json || "");
		dialog.show();
	},

	async import_snapshot(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Import Theme Snapshot"),
			fields: [
				{
					fieldname: "snapshot_json",
					fieldtype: "Code",
					label: __("Snapshot JSON"),
					options: "JSON",
					reqd: 1,
				},
			],
			primary_action_label: __("Import"),
			primary_action: async (values) => {
				await frappe.call({
					method: "crm_desk_theme.api.theme.import_theme_snapshot",
					args: {
						name: frm.doc.name,
						snapshot_json: values.snapshot_json,
					},
					freeze: true,
					freeze_message: __("Importing snapshot"),
				});
				dialog.hide();
				await frm.reload_doc();
				frappe.show_alert({ message: __("Snapshot imported"), indicator: "green" });
			},
		});

		dialog.show();
	},

	async rollback_theme(frm) {
		const response = await frappe.call({
			method: "crm_desk_theme.api.theme.get_theme_revisions",
			args: { name: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading revisions"),
		});

		const revisions = response.message || [];
		if (!revisions.length) {
			frappe.show_alert({ message: __("No revisions available"), indicator: "orange" });
			return;
		}

		const options = revisions.map((revision) => ({
			label: `#${revision.revision_no} · ${revision.published_on || ""} · ${revision.published_by || ""}`,
			value: revision.name,
		}));

		const dialog = new frappe.ui.Dialog({
			title: __("Rollback Theme"),
			fields: [
				{
					fieldname: "revision_name",
					fieldtype: "Select",
					label: __("Revision"),
					options: options.map((option) => option.value).join("\n"),
					reqd: 1,
					description: __("Select a stored published revision to restore."),
				},
				{
					fieldname: "revision_help",
					fieldtype: "HTML",
				},
			],
			primary_action_label: __("Rollback"),
			primary_action: async (values) => {
				await frappe.call({
					method: "crm_desk_theme.api.theme.rollback_theme_to_revision",
					args: {
						name: frm.doc.name,
						revision_name: values.revision_name,
					},
					freeze: true,
					freeze_message: __("Rolling back theme"),
				});
				dialog.hide();
				await frm.reload_doc();
				frappe.show_alert({ message: __("Theme rolled back"), indicator: "green" });
			},
		});

		const firstRevision = options[0]?.value;
		if (firstRevision) {
			dialog.set_value("revision_name", firstRevision);
		}
		const helpHtml = revisions
			.map(
				(revision) =>
					`<div><strong>#${frappe.utils.escape_html(String(revision.revision_no))}</strong> ${frappe.utils.escape_html(
						String(revision.published_on || "")
					)} ${frappe.utils.escape_html(String(revision.published_by || ""))}</div>`
			)
			.join("");
		dialog.get_field("revision_help").$wrapper.html(
			`<div class="text-muted small" style="max-height: 12rem; overflow:auto;">${helpHtml}</div>`
		);
		dialog.show();
	},

	inject_preview_css(generatedCss, previewMode) {
		let tag = document.getElementById("crm-desk-theme-form-preview");
		if (!tag) {
			tag = document.createElement("style");
			tag.id = "crm-desk-theme-form-preview";
			document.head.appendChild(tag);
		}

		document.body?.setAttribute("data-desk-theme", "preview");
		document.body?.setAttribute("data-desk-theme-mode", String(previewMode || "Light").toLowerCase());
		document.documentElement?.setAttribute(
			"data-desk-theme-mode",
			String(previewMode || "Light").toLowerCase()
		);
		tag.textContent = generatedCss;
	},

	toggle_editor_sections(frm) {
		const advancedMode = frm.doc.editor_mode === "Advanced";
		frm.set_df_property("tokens", "hidden", advancedMode ? 0 : 1);
		frm.set_df_property("section_light_palette", "hidden", frm.doc.mode_strategy === "Dark Only" ? 1 : 0);
		frm.set_df_property(
			"section_dark_palette",
			"hidden",
			frm.doc.mode_strategy === "Light Only" || frm.doc.mode_strategy === "Shared" ? 1 : 0
		);
	},

	async normalize_shared_mode_fields(frm) {
		if (frm.doc.mode_strategy !== "Shared") {
			return;
		}

		const updates = {};
		for (const fieldname of DARK_VISUAL_FIELDS) {
			if (frm.doc[fieldname]) {
				updates[fieldname] = "";
			}
		}

		if (Object.keys(updates).length) {
			await frm.set_value(updates);
		}
	},

	async render_preview(frm, showAlert = false) {
		const response = await frappe.call({
			method: "crm_desk_theme.api.theme.preview_theme",
			args: { doc: frm.doc },
			freeze: showAlert,
			freeze_message: showAlert ? __("Generating preview") : undefined,
		});

		const generatedCss = response.message?.generated_css || "";
		const previewMode = response.message?.preview_mode || frm.doc.preview_mode || "Light";
		frm.set_value("generated_css", generatedCss);
		frm.events.inject_preview_css(generatedCss, previewMode);
		if (showAlert) {
			frappe.show_alert({
				message: __("Preview applied for this browser session"),
				indicator: "green",
			});
		}
	},
});

for (const fieldname of VISUAL_FIELDS) {
	frappe.ui.form.on("Desk Theme", fieldname, function (frm) {
		frm.events.render_preview(frm);
	});
}
