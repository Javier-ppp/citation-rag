const API_BASE = 'http://localhost:8000/api';

class ApiClient {
    static async ingestPdf(file, role = "source") {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE}/ingest?role=${role}`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) throw new Error(await response.text());
            return await response.json();
        } catch (error) {
            console.error('Ingest error:', error);
            throw error;
        }
    }

    static async search(query, topK = 5) {
        try {
            const response = await fetch(`${API_BASE}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: topK })
            });
            if (!response.ok) throw new Error(await response.text());
            return await response.json();
        } catch (error) {
            console.error('Search error:', error);
            throw error;
        }
    }

    static async checkCitation(citationMarker, context, pdfId) {
        try {
            const response = await fetch(`${API_BASE}/cite-check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    citation_marker: citationMarker, 
                    context: context, 
                    pdf_id: pdfId 
                })
            });
            if (!response.ok) throw new Error(await response.text());
            return await response.json();
        } catch (error) {
            console.error('Cite check error:', error);
            throw error;
        }
    }

    static async getPapers() {
        try {
            const response = await fetch(`${API_BASE}/papers`);
            if (!response.ok) throw new Error(await response.text());
            return await response.json();
        } catch (error) {
            console.error('Fetch papers error:', error);
            throw error;
        }
    }

    static async resetSession() {
        try {
            const response = await fetch(`${API_BASE}/session/reset`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error(await response.text());
            return await response.json();
        } catch (error) {
            console.error('Reset error:', error);
            throw error;
        }
    }
}
