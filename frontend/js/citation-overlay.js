class CitationOverlay {
    constructor(appContext) {
        this.appContext = appContext; // Needs access to current pdf_id
        this.tooltip = document.getElementById('citation-tooltip');
        this.setupTooltipEvents();
        this.activeCitation = null;
    }

    setupTooltipEvents() {
        // Prevent tooltip from disappearing when hovering over it
        this.tooltip.addEventListener('mouseenter', () => {
            if (this.hideTimeout) clearTimeout(this.hideTimeout);
        });
        this.tooltip.addEventListener('mouseleave', () => {
            this.hide();
        });
    }

    // Called by PdfViewer when textLayer is rendered
    processTextLayer(textLayerElement) {
        // No-op: We no longer mutate the DOM to avoid rendering artifacts.
        // Interactivity is now handled via Event Delegation in setupObserver.
        if (!this.observerInitialized) {
            this.setupObserver(textLayerElement.parentElement);
            this.observerInitialized = true;
        }
    }

    setupObserver(container) {
        // Listen for mousemove to find [brackets] under the cursor
        container.addEventListener('mouseover', (e) => {
            const target = e.target;
            
            // Check if we are over a text span
            if (target.tagName === 'SPAN' && target.parentElement.classList.contains('textLayer')) {
                const text = target.textContent.trim();
                const regex = /\[\s*([\d,\s\-–]+)\s*\]/;
                const match = text.match(regex);
                
                if (match) {
                    const context = this.extractContext(target.parentElement.textContent);
                    this.show({ target: target }, match[0], context);
                }
            }
        });

        container.addEventListener('mouseout', (e) => {
            if (e.target.tagName === 'SPAN') {
                this.hideTimeout = setTimeout(() => this.hide(), 300);
            }
        });
    }

    extractContext(text) {
        // Simplistic context: just grab the parent span's text. 
        // In real PDFs, context spans multiple div lines. For MVP:
        return text.trim();
    }

    async show(event, marker, context) {
        if (this.hideTimeout) clearTimeout(this.hideTimeout);

        // Position immediately
        const rect = event.target.getBoundingClientRect();
        this.tooltip.style.left = (rect.left + rect.width / 2) + 'px';
        this.tooltip.style.top = (rect.bottom + 10) + 'px'; // 10px below marker

        // Handle screen edge collisions
        if (rect.bottom + 300 > window.innerHeight) {
            this.tooltip.style.top = (rect.top - 10) + 'px';
            this.tooltip.style.transform = 'translate(-50%, -100%)';
        } else {
            this.tooltip.style.transform = 'translate(-50%, 0)';
        }

        this.tooltip.classList.remove('hidden');

        // Show loading state
        document.getElementById('tooltip-loading').classList.remove('hidden');
        document.getElementById('tooltip-content').classList.add('hidden');
        document.getElementById('tooltip-error').classList.add('hidden');

        if (!this.appContext.currentPdfId) {
            this.showError("PDF Not ingested yet.");
            return;
        }

        try {
            const data = await ApiClient.checkCitation(marker, context, this.appContext.currentPdfId);

            if (data.found === false) {
                this.showError(data.message || "Paper not found.");
            } else {
                this.renderContent(data);
            }
        } catch (e) {
            console.error("Citation Fetch Error:", e);
            this.showError("JS Exception: " + e.message);
        }
    }

    renderContent(data) {
        document.getElementById('tooltip-loading').classList.add('hidden');
        const content = document.getElementById('tooltip-content');
        content.classList.remove('hidden');

        // Clear previous content to handle results dynamically
        content.innerHTML = '';

        const results = data.results || [];

        results.forEach((item, idx) => {
            if (idx > 0) content.appendChild(document.createElement('hr'));
            
            const itemDiv = document.createElement('div');
            itemDiv.className = 'tooltip-item';
            
            if (!item.found) {
                itemDiv.innerHTML = `
                    <div class="tooltip-header">
                        <h4 class="tooltip-subtitle">Ref [${item.ref_num}]</h4>
                        <span class="tooltip-meta">${item.message}</span>
                    </div>
                `;
            } else {
                const confPercent = Math.round((item.confidence || 0) * 100);
                let evidenceHtml = '';
                
                if (item.evidences && item.evidences.length > 0) {
                    item.evidences.forEach(ev => {
                        const symbol = ev.supports ? '✅' : '❌';
                        const symbolClass = ev.supports ? 'valid' : 'invalid';
                        evidenceHtml += `
                            <div class="evidence-item">
                                <span class="evidence-symbol ${symbolClass}">${symbol}</span>
                                <div class="evidence-content">
                                    "${ev.passage}" 
                                    <span class="evidence-page">p. ${ev.page_num + 1}</span>
                                </div>
                            </div>
                        `;
                    });
                } else {
                    evidenceHtml = '<p class="passage-text">No specific evidence extracted.</p>';
                }

                itemDiv.innerHTML = `
                    <div class="tooltip-header">
                        <h4 class="tooltip-title">Ref [${item.ref_num}]: ${item.cited_paper?.title || "Unknown Title"}</h4>
                        <span class="tooltip-meta">${item.cited_paper?.authors || ''} (${item.cited_paper?.year || ''})</span>
                    </div>
                    <div class="tooltip-body">
                        ${evidenceHtml}
                    </div>
                `;
            }
            content.appendChild(itemDiv);
        });
    }

    showError(msg) {
        document.getElementById('tooltip-loading').classList.add('hidden');
        document.getElementById('tooltip-error').classList.remove('hidden');
        document.getElementById('tooltip-error-msg').textContent = msg;
    }

    hide() {
        this.tooltip.classList.add('hidden');
    }

    // Forward Mode: Highlighting passages from search results
    highlightPassage(passage) {
        if (!passage) return;
        
        const textLayer = document.getElementById('text-layer');
        if (!textLayer) return;

        // Clean up previous highlights
        const oldHighlights = textLayer.querySelectorAll('.highlight-flash');
        oldHighlights.forEach(h => h.classList.remove('highlight-flash'));

        // Simplistic fuzzy finder: find spans that contain significant chunks of the passage
        const spans = Array.from(textLayer.querySelectorAll('span'));
        
        // We look for spans that contain at least 15 chars of the passage 
        // to handle the case where the passage is split across lines.
        const passageWords = passage.split(/\s+/).filter(w => w.length > 3);
        const searchTerms = passageWords.slice(0, 4).join(' '); // First few words

        spans.forEach(span => {
            const spanText = span.textContent.toLowerCase();
            const passageLower = passage.toLowerCase();
            
            if (passageLower.includes(spanText) && spanText.length > 10) {
                span.classList.add('highlight-flash');
            } else if (searchTerms && spanText.includes(searchTerms.toLowerCase())) {
                span.classList.add('highlight-flash');
            }
        });
    }
}
