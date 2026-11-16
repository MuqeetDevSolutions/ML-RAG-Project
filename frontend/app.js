/* ============================================================
   RAG Document QA — frontend logic
   ============================================================ */

const API_BASE = "";

// ---------- State ----------
let conversationId = null;      // naya chat = null, baad me server se milega

// ---------- DOM refs ----------
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const newChatBtn = document.getElementById("new-chat-btn");
const docStats = document.getElementById("doc-stats");
const docList = document.getElementById("doc-list");
const fileInput = document.getElementById("file-input");
const uploadLabel = document.getElementById("upload-label");
const uploadLabelText = document.getElementById("upload-label-text");
const uploadStatus = document.getElementById("upload-status");
const askForm = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const askBtn = document.getElementById("ask-btn");
const chatLog = document.getElementById("chat-log");

// ================================================================
// Helpers
// ================================================================

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function scrollToBottom() {
    chatLog.scrollTop = chatLog.scrollHeight;
}

function setStatus(ok, text) {
    statusDot.classList.remove("online", "offline");
    statusDot.classList.add(ok ? "online" : "offline");
    statusText.textContent = text;
}

// ================================================================
// Health check
// ================================================================

async function checkHealth() {
    try {
        const r = await fetch(`${API_BASE}/health`);
        if (!r.ok) throw new Error("bad status");
        setStatus(true, "Online");
    } catch (e) {
        setStatus(false, "Offline");
    }
}

// ================================================================
// Documents
// ================================================================

async function loadDocuments() {
    try {
        const r = await fetch(`${API_BASE}/api/documents`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        renderDocuments(data);
    } catch (e) {
        docStats.textContent = `Load error: ${e.message}`;
        docList.innerHTML = `<li class="empty">Load nahi ho saki.</li>`;
    }
}

function renderDocuments(data) {
    docStats.innerHTML =
        `<strong>${data.total_documents}</strong> document(s)<br>` +
        `<strong>${data.total_chunks}</strong> chunks total`;

    if (!data.documents || data.documents.length === 0) {
        docList.innerHTML = `<li class="empty">Koi document upload nahi hua.</li>`;
        return;
    }

    docList.innerHTML = "";
    for (const d of data.documents) {
        const li = document.createElement("li");
        const pagesCount = d.pages ? d.pages.length : 0;

        li.innerHTML = `
            <div class="doc-meta">
                <span class="doc-name" title="${escapeHtml(d.file_name)}">
                    ${escapeHtml(d.file_name)}
                </span>
                <span class="doc-sub">${d.chunks} chunks · ${pagesCount} pages</span>
            </div>
            <button class="doc-delete" title="Delete">✕</button>
        `;

        li.querySelector(".doc-delete").addEventListener("click", () => {
            deleteDocument(d.document_id, d.file_name);
        });

        docList.appendChild(li);
    }
}

async function uploadFile(file) {
    if (!file) return;

    uploadLabel.classList.add("busy");
    uploadLabelText.textContent = "Processing…";
    uploadStatus.textContent = "";
    uploadStatus.className = "upload-status";

    const form = new FormData();
    form.append("file", file);

    try {
        const r = await fetch(`${API_BASE}/api/documents/upload`, {
            method: "POST",
            body: form,
        });
        const data = await r.json();

        if (!r.ok) {
            const detail = data.detail || `HTTP ${r.status}`;
            throw new Error(detail);
        }

        if (data.status === "skipped") {
            uploadStatus.className = "upload-status";
            uploadStatus.textContent = data.message || "Skipped.";
        } else {
            uploadStatus.className = "upload-status success";
            uploadStatus.textContent =
                `${data.chunks_added} chunks add hue (${data.elapsed_seconds}s)`;
        }

        await loadDocuments();
    } catch (e) {
        uploadStatus.className = "upload-status error";
        uploadStatus.textContent = `Error: ${e.message}`;
    } finally {
        uploadLabel.classList.remove("busy");
        uploadLabelText.textContent = "Upload PDF";
        fileInput.value = "";
    }
}

fileInput.addEventListener("change", (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) uploadFile(f);
});

const sidebar = document.querySelector(".sidebar");
if (sidebar) {
    sidebar.addEventListener("dragover", (e) => e.preventDefault());
    sidebar.addEventListener("drop", (e) => {
        e.preventDefault();
        const f = e.dataTransfer.files && e.dataTransfer.files[0];
        if (f && f.name.toLowerCase().endsWith(".pdf")) {
            uploadFile(f);
        }
    });
}

async function deleteDocument(docId, fileName) {
    const ok = confirm(`Delete "${fileName}"? Is ke saare chunks hata jayenge.`);
    if (!ok) return;

    try {
        const r = await fetch(
            `${API_BASE}/api/documents/${encodeURIComponent(docId)}`,
            { method: "DELETE" }
        );
        if (!r.ok) {
            const data = await r.json().catch(() => ({}));
            throw new Error(data.detail || `HTTP ${r.status}`);
        }
        await loadDocuments();
    } catch (e) {
        alert(`Delete error: ${e.message}`);
    }
}

// ================================================================
// Chat
// ================================================================

function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "msg user";
    div.innerHTML = `<div class="label">You</div><div>${escapeHtml(text)}</div>`;
    chatLog.appendChild(div);
    scrollToBottom();
}

function appendLoadingMessage() {
    const div = document.createElement("div");
    div.className = "msg bot";
    div.id = "loading-msg";
    div.innerHTML = `
        <div class="label">Assistant</div>
        <div class="loading"><span></span><span></span><span></span></div>
    `;
    chatLog.appendChild(div);
    scrollToBottom();
    return div;
}

function removeLoadingMessage() {
    const el = document.getElementById("loading-msg");
    if (el) el.remove();
}

function appendBotMessage(data) {
    const div = document.createElement("div");
    div.className = "msg bot";

    let sourcesHtml = "";
    if (data.sources && data.sources.length > 0) {
        const items = data.sources
            .map((s) => {
                const preview = s.chunks && s.chunks[0] ? s.chunks[0].preview : "";
                return `
                    <div class="source-item">
                        <div class="source-head">
                            <span class="source-file">📄 ${escapeHtml(s.file_name)}</span>
                            <span class="source-page">page ${s.page_number}</span>
                            <span class="source-score">score ${s.best_score.toFixed(3)}</span>
                        </div>
                        <div class="source-preview">${escapeHtml(preview)}</div>
                    </div>
                `;
            })
            .join("");
        sourcesHtml = `
            <div class="sources">
                <h4>Sources (${data.sources.length})</h4>
                ${items}
            </div>
        `;
    }

    const notFound = !data.found_in_documents;
    const metaLine = notFound
        ? `<span>⚠ Not found in documents</span><span>top score ${data.top_score.toFixed(3)}</span>`
        : `<span>✓ Found</span><span>top score ${data.top_score.toFixed(3)}</span><span>${data.elapsed_seconds}s</span>`;

    div.innerHTML = `
        <div class="label">Assistant</div>
        <div class="answer">${escapeHtml(data.answer)}</div>
        <div class="meta">${metaLine}</div>
        ${sourcesHtml}
    `;
    chatLog.appendChild(div);
    scrollToBottom();
}

function appendErrorMessage(msg) {
    const div = document.createElement("div");
    div.className = "msg error";
    div.innerHTML = `<div class="label">Error</div><div>${escapeHtml(msg)}</div>`;
    chatLog.appendChild(div);
    scrollToBottom();
}

async function askQuestion(question) {
    appendUserMessage(question);
    questionInput.value = "";
    questionInput.disabled = true;
    askBtn.disabled = true;
    newChatBtn.disabled = true;
    appendLoadingMessage();

    try {
        const payload = {
            question,
            top_k: 8,
        };
        if (conversationId) {
            payload.conversation_id = conversationId;
        }

        const r = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        removeLoadingMessage();

        const data = await r.json();

        if (!r.ok) {
            const detail =
                typeof data.detail === "string"
                    ? data.detail
                    : JSON.stringify(data.detail);
            appendErrorMessage(detail || `HTTP ${r.status}`);
            return;
        }

        // Save conversation id (naya ya same)
        conversationId = data.conversation_id;

        appendBotMessage(data);
    } catch (e) {
        removeLoadingMessage();
        appendErrorMessage(e.message);
    } finally {
        questionInput.disabled = false;
        askBtn.disabled = false;
        newChatBtn.disabled = false;
        questionInput.focus();
    }
}

askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (!q) return;
    askQuestion(q);
});

// ================================================================
// New Chat
// ================================================================

function startNewChat() {
    if (conversationId) {
        const ok = confirm(
            "Naya chat shuru karein? Purani conversation memory se hata jayegi."
        );
        if (!ok) return;
    }
    conversationId = null;
    chatLog.innerHTML = `
        <div class="welcome">
            <h2>Kya jaanna chahte ho?</h2>
            <p>
                Apni PDF upload karo aur uske bare me sawaal poocho.
                Main sirf aap ke documents ke andar mojood maloomat
                ke aadhar par jawab dunga.
            </p>
            <p class="welcome-hint">
                💡 Follow-up sawaal pooch sakte ho — jaise
                "Who is Carl?" ke baad "What about Susan?"
            </p>
        </div>
    `;
    questionInput.focus();
}

newChatBtn.addEventListener("click", startNewChat);

// ================================================================
// Bootstrap
// ================================================================

checkHealth();
loadDocuments();
setInterval(checkHealth, 30000);