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
        // Very basic DOM parsing to find [1], [2,3] etc.
        // We iterate over textLayer spans. Since PDF.js breaks spans arbitrarily,
        // this is a simplified approach assuming markers like [1] fit in a single node.
        
        const walker = document.createTreeWalker(textLayerElement, NodeFilter.SHOW_TEXT, null, false);
        let node;
        const nodesToWrap = [];

        while (node = walker.nextNode()) {
            const regex = /\[\s*([\d,\s\-–]+)\s*\]/g;
            if (regex.test(node.nodeValue)) {
                nodesToWrap.push(node);
            }
        }

        nodesToWrap.forEach(textNode => {
            const regex = /(\[\s*[\d,\s\-–]+\s*\])/g;
            const parent = textNode.parentNode;
            const text = textNode.nodeValue;
            
            // Fragment to replace text node with mixed text/span
            const fragment = document.createDocumentFragment();
            let lastIdx = 0;
            let match;
            
            regex.lastIndex = 0;
            while ((match = regex.exec(text)) !== null) {
                // Add preceding text
                if (match.index > lastIdx) {
                    fragment.appendChild(document.createTextNode(text.substring(lastIdx, match.index)));
                }
                
                // Add wrapped marker
                const span = document.createElement('span');
                span.className = 'citation-marker';
                span.textContent = match[0];
                
                // We need the surrounding text for context
                const context = this.extractContext(parent.textContent || text);
                
                span.addEventListener('mouseenter', (e) => this.show(e, match[0], context));
                span.addEventListener('mouseleave', () => {
                    this.hideTimeout = setTimeout(() => this.hide(), 300);
                });
                
                fragment.appendChild(span);
                lastIdx = regex.lastIndex;
            }
            
            // Add remaining text
            if (lastIdx < text.length) {
                fragment.appendChild(document.createTextNode(text.substring(lastIdx)));
            }
            
            parent.replaceChild(fragment, textNode);
            // Fix PDF.js absolute positioning which sometimes acts weird with multiple children
            // Usually the parent span is absolute, so the child chunks flow inline.
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
}
