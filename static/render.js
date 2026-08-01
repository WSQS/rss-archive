// render.js — cell-level DOM rendering helpers.
//
// This is the single shared interface for every page type. Each page owns its
// own inline orchestration (build the <table> skeleton, iterate its data, call
// these helpers to fill cells) and render.js stays free of any business
// knowledge of what a FeedItem or FeedSource looks like.

/**
 * Append a text <td> to `row`. `value` of null/undefined renders as "".
 * An optional className is applied when given.
 */
function appendTextCell(row, value, className) {
    const cell = document.createElement("td");
    if (className) {
        cell.className = className;
    }
    cell.textContent = value ?? "";
    row.appendChild(cell);
}

/**
 * Append a <td> to `row`. If `value` is an http(s) URL it becomes an <a>
 * (opened in a new tab); otherwise it is rendered as plain text.
 */
function appendLinkCell(row, value) {
    const cell = document.createElement("td");
    if (typeof value === "string" && (value.startsWith("https://") || value.startsWith("http://"))) {
        const link = document.createElement("a");
        link.href = value;
        link.textContent = value;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        cell.appendChild(link);
    } else {
        cell.textContent = value ?? "";
    }
    row.appendChild(cell);
}
