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
            this.showError("Error connecting to backend.");
        }
    }

    renderContent(data) {
        document.getElementById('tooltip-loading').classList.add('hidden');
        document.getElementById('tooltip-content').classList.remove('hidden');

        document.getElementById('tooltip-title').textContent = data.cited_paper?.title || "Unknown Title";
        document.getElementById('tooltip-authors').textContent = `${data.cited_paper?.authors || ''} (${data.cited_paper?.year || ''})`;
        document.getElementById('tooltip-passage').textContent = `"...${data.best_passage}..."`;
        document.getElementById('tooltip-page').textContent = data.page_num !== undefined ? data.page_num + 1 : "?";

        if (data.confidence) {
            document.getElementById('tooltip-confidence').textContent = `Relevance Match: ${Math.round(data.confidence * 100)}%`;
        }
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
