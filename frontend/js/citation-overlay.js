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
        // Listen for continuous mousemove to hit sub-span accuracy
        container.addEventListener('mousemove', (e) => {
            const target = e.target;
            
            if (target.tagName === 'SPAN' && target.parentElement.classList.contains('textLayer')) {
                let charOffset = 0;
                
                // Fetch exact character index under cursor for 1-to-1 parsing
                if (document.caretPositionFromPoint) {
                    const caret = document.caretPositionFromPoint(e.clientX, e.clientY);
                    if (caret && caret.offsetNode && caret.offsetNode.parentNode === target) {
                        charOffset = caret.offset;
                    }
                } else if (document.caretRangeFromPoint) {
                    const range = document.caretRangeFromPoint(e.clientX, e.clientY);
                    if (range && range.startContainer && range.startContainer.parentNode === target) {
                        charOffset = range.startOffset;
                    }
                }

                const parsed = this.getSentenceAndCitation(target.parentElement, target, charOffset);
                
                if (parsed && parsed.marker) {
                    // Prevent flickering
                    if (this.activeMarker === parsed.marker && this.activeContext === parsed.context && !this.tooltip.classList.contains('hidden')) {
                        return;
                    }
                    this.activeMarker = parsed.marker;
                    this.activeContext = parsed.context;
                    // Position directly at cursor pointer to fix DOM shifting
                    this.showAt(e.clientX, e.clientY, parsed.marker, parsed.context);
                } else {
                    // If we shifted to a "dead" zone in a span with no citation, hide it naturally
                    if (!this.tooltip.matches(':hover') && this.activeMarker) {
                         if (!this.hideTimeout) {
                             this.hideTimeout = setTimeout(() => {
                                 this.hide();
                                 this.activeMarker = null;
                                 this.activeContext = null;
                             }, 300);
                         }
                    }
                }
            }
        });

        container.addEventListener('mouseout', (e) => {
            if (e.target.tagName === 'SPAN') {
                if (!this.hideTimeout) {
                    this.hideTimeout = setTimeout(() => {
                        this.hide();
                        this.activeMarker = null;
                        this.activeContext = null;
                    }, 300);
                }
            }
        });
    }

    getSentenceAndCitation(textLayer, targetSpan, charOffset = 0) {
        // Cache text mapping per page to avoid massive string building on every mouse tick
        if (!textLayer._textCache) {
            const spans = Array.from(textLayer.querySelectorAll('span'));
            let fullText = "";
            let offsets = [];
            for (let i = 0; i < spans.length; i++) {
                offsets.push({ span: spans[i], start: fullText.length });
                let text = spans[i].textContent;
                fullText += text;
                // Add natural spacing unless there's a hyphen
                if (!text.endsWith('-') && !text.endsWith(' ')) fullText += ' ';
            }
            textLayer._textCache = { fullText, offsets };
        }

        const cache = textLayer._textCache;
        const targetOffsetData = cache.offsets.find(o => o.span === targetSpan);
        if (!targetOffsetData) return null;

        // Base + the calculated offset inside the span guarantees 100% 1-to-1 character accuracy
        const targetPos = Math.min(targetOffsetData.start + charOffset, cache.fullText.length - 1);
        const fullText = cache.fullText;

        // Traverse backward to find sentence start
        let sentenceStart = targetPos;
        while (sentenceStart >= 0) {
            if (sentenceStart >= 2 && fullText.substring(sentenceStart - 2, sentenceStart) === '. ') {
                const prev1 = fullText[sentenceStart - 3] || '';
                const prev2 = sentenceStart >= 4 ? fullText[sentenceStart - 4] : '';
                if (prev1 !== 'l' && prev2 !== 'a' && prev1 !== 'g') {
                    break;
                }
            }
            sentenceStart--;
        }
        if (sentenceStart < 0) sentenceStart = 0;

        // Traverse forward to find sentence end
        let sentenceEnd = targetPos;
        while (sentenceEnd < fullText.length - 1) {
            if (fullText.substring(sentenceEnd, sentenceEnd + 2) === '. ') {
                const prev1 = fullText[sentenceEnd - 1] || '';
                const prev2 = sentenceEnd >= 2 ? fullText[sentenceEnd - 2] : '';
                if (prev1 !== 'l' && prev2 !== 'a' && prev1 !== 'g') {
                    sentenceEnd += 1; // Include the period
                    break;
                }
            }
            sentenceEnd++;
        }

        let sentence = fullText.substring(sentenceStart, sentenceEnd).trim();
        
        // Find ALL citation markers inside this unified sentence chunk
        const regex = /\[\s*([\d,\s\-–]+)\s*\]/g;
        const matches = [...sentence.matchAll(regex)];
        
        if (matches.length > 0) {
            // Find which sub-segment of the sentence we are hovering over
            // targetPos maps to an offset within the extracted sentence
            const localTargetPos = targetPos - sentenceStart;
            
            // By default, assume the entire sentence belongs to the first match
            let bestMatch = matches[0];
            let bestContext = sentence;
            
            // If the sentence has multiple citations, chop it into territorial boundary chunks
            if (matches.length > 1) {
                for (let i = 0; i < matches.length; i++) {
                    let m = matches[i];
                    // Territory starts right after the PREVIOUS marker, or 0 if first
                    let territoryStart = i === 0 ? 0 : matches[i - 1].index + matches[i - 1][0].length;
                    let markerEnd = m.index + m[0].length;
                    
                    // If the mouse is before or exactly on this marker, it belongs to this chunk
                    if (localTargetPos >= territoryStart && localTargetPos <= markerEnd) {
                        bestMatch = m;
                        // Slice just this chunk so the backend only searches for the exact local context
                        bestContext = sentence.substring(territoryStart, markerEnd).trim();
                        break;
                    }
                }
                
                // If hovered past the final marker, it belongs to the final snippet
                if (localTargetPos > matches[matches.length - 1].index + matches[matches.length - 1][0].length) {
                    let lastIdx = matches.length - 1;
                    bestMatch = matches[lastIdx];
                    let territoryStart = lastIdx === 0 ? 0 : matches[lastIdx - 1].index + matches[lastIdx - 1][0].length;
                    bestContext = sentence.substring(territoryStart).trim();
                }
            } 
            
            return {
                context: bestContext,
                marker: bestMatch[0]
            };
        }
        
        return null;
    }

    async showAt(x, y, marker, context) {
        if (this.hideTimeout) clearTimeout(this.hideTimeout);

        // Position directly at the cursor coordinates, creating a tight physical link 
        // to exactly what the user is inspecting.
        this.tooltip.style.left = x + 'px';
        this.tooltip.style.top = (y + 15) + 'px'; // 15px below cursor

        // Handle screen edge collisions
        if (y + 300 > window.innerHeight) {
            this.tooltip.style.top = (y - 15) + 'px';
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
