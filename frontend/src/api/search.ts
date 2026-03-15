import axios from 'axios';

// Define a flexible interface for the API response based on typical GoodRx data
export interface DrugResult {
    id: string | number;
    name: string;
    code?: string;
    dosage?: string;
    price?: number;
    stock?: number;
    pharmacy?: string;
    location?: string;
    group?: string;
    score?: number;
    // Add other fields as expected from the actual API
}

const API_URL = '/api';

export const searchDrugs = async (query: string): Promise<DrugResult[]> => {
    try {
        const response = await axios.get<Array<[string, string, string]> | { value: Array<[string, string, string]> }>(`${API_URL}/search`, {
            params: { q: query },
        });

        // The API may return a raw array or an object with a "value" property
        const data = Array.isArray(response.data) ? response.data : (response.data as any).value || [];

        // Map the array response to our object structure
        return data.map((item: [string, string, string]) => ({
            id: item[0],
            name: item[1],
            code: item[0], // Use drug ID for checking rates
            group: item[2],
            pharmacy: 'disponible en droguería',
            location: 'Medellin',
            price: undefined,
            stock: undefined
        }));
    } catch (error) {
        console.error('Error searching drugs:', error);
        throw error;
    }
};

export interface RateResult {
    sku: string;
    descripcion: string;
    precio: number;
    saldo: number;
}

export const getRates = async (codes: string[]): Promise<RateResult[]> => {
    try {
        // The API now expects codigos_medicamentos as a string representation of a list: "['code1', 'code2']"
        const formattedCodes = `['${codes.join("','")}']`;

        const response = await axios.post<{ data: RateResult[] }>(`${API_URL}/rates`, {
            codigos_medicamentos: formattedCodes
        });

        // The API returns data inside a "data" property as an array of objects
        return response.data.data;
    } catch (error) {
        console.error('Error fetching rates:', error);
        // Return empty array on error to not block UI
        return [];
    }
};

export const semanticSearch = async (query: string, limit: number = 10): Promise<DrugResult[]> => {
    try {
        const response = await axios.post<{ results: any[] }>(`${API_URL}/semantic_search`, null, {
            params: { query, limit },
            headers: { 'accept': 'application/json' }
        });

        // The API returns an object with a "results" array
        const results = response.data.results || [];

        // Map the API fields to our DrugResult structure and include score
        return results
            .map((item: any) => ({
                id: item.codigo,
                name: item.nombre,
                code: item.codigo,
                group: item['Accion Terapeutica'], // Map therapeutic action if useful
                score: item.score,
                pharmacy: 'disponible en droguería',
                location: 'Medellin',
                price: undefined,
                stock: undefined
            }))
            .filter((item: DrugResult) => item.score === undefined || item.score < 0.5);
    } catch (error) {
        console.error('Error in semantic search:', error);
        throw error;
    }
};


