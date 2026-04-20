class ForwardSearch {
    constructor() {
        this.input = document.getElementById('search-query');
        this.btn = document.getElementById('search-btn');
        this.container = document.getElementById('search-results');
        
        this.btn.addEventListener('click', () => this.performSearch());
    }

    async performSearch() {
        const query = this.input.value.trim();
        if (!query) return;
        
        this.showLoading();
        this.btn.disabled = true;
        this.btn.textContent = 'Searching...';

        try {
            const data = await ApiClient.search(query, 5);
            if (data.found && data.results.length > 0) {
                this.renderResults(data.results);
            } else {
                this.showEmpty(data.message || "No matches found.");
            }
        } catch (e) {
            this.showEmpty("Error performing search.");
        } finally {
            this.btn.disabled = false;
            this.btn.textContent = 'Search Database';
        }
    }

    showLoading() {
        this.container.innerHTML = `
            <div class="empty-state">
                <span class="pulsing-dot" style="margin-bottom: 8px;"></span>
                <p>Searching vectors & AI analyzing...</p>
            </div>
        `;
    }

    showEmpty(msg) {
        this.container.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <p>${msg}</p>
            </div>
        `;
    }

    renderResults(results) {
        this.container.innerHTML = '';
        
        results.forEach(res => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            const confPercent = Math.round(res.relevance_score * 100);
            
            card.innerHTML = `
                <div class="card-header">
                    <span class="card-title">${res.title || 'Unknown Title'}</span>
                    <span class="card-meta">Match: ${confPercent}%</span>
                </div>
                <div class="card-passage">"...${res.passage}..."</div>
                <div class="card-explanation">
                    <strong>AI Analysis:</strong> ${res.llm_explanation || 'No analysis provided.'}
                </div>
            `;
            this.container.appendChild(card);
        });
    }
}
