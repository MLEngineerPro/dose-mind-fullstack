import { useState, useEffect } from 'react';
import { Search, Loader2, Pill } from 'lucide-react';
import { useDebounce } from '../hooks/useDebounce';
import { searchDrugs, getRates, semanticSearch, type DrugResult } from '../api/search';
import { DrugCard } from './DrugCard';

export const SearchCombobox = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<DrugResult[]>([]);
    const [semanticResults, setSemanticResults] = useState<DrugResult[]>([]);
    const [loading, setLoading] = useState(false);
    const [semanticLoading, setSemanticLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [semanticError, setSemanticError] = useState<string | null>(null);
    const [hasSearched, setHasSearched] = useState(false);

    const debouncedQuery = useDebounce(query, 500);

    const handleClearSearch = () => {
        setQuery('');
        setResults([]);
        setSemanticResults([]);
        setHasSearched(false);
        setError(null);
        setSemanticError(null);
    };

    useEffect(() => {
        const fetchOriginal = async () => {
            setLoading(true);
            setError(null);
            try {
                // 1. Search for drugs (Names & Codes)
                const searchData = await searchDrugs(debouncedQuery);

                // 2. Separate N08 drugs from others
                const n08Drugs = searchData.filter(drug => drug.group === 'N08');
                const otherDrugs = searchData.filter(drug => drug.group !== 'N08');

                // 3. Extract codes for other drugs to fetch real-time rates
                const codes = otherDrugs
                    .map(drug => drug.code)
                    .filter((code): code is string => !!code);

                let mergedResults: DrugResult[] = [];

                // 4. Fetch rates if we have codes for "other" drugs
                if (codes.length > 0) {
                    const rates = await getRates(codes);

                    // Merge rates into "other" search results and FILTER out items not in rates
                    const ratesResults = otherDrugs
                        .map(drug => {
                            const rate = rates.find(r => r.sku === drug.code);
                            if (rate) {
                                return {
                                    ...drug,
                                    name: (rate.descripcion && rate.descripcion.trim() !== '') ? rate.descripcion : drug.name,
                                    price: rate.precio,
                                    stock: rate.saldo
                                } as DrugResult;
                            }
                            return null;
                        })
                        .filter((drug): drug is DrugResult => drug !== null);

                    mergedResults = [...ratesResults, ...n08Drugs];
                } else {
                    // If no "other" drugs had codes, we still show N08 drugs
                    mergedResults = [...n08Drugs];
                }

                setResults(mergedResults);

            } catch (err) {
                console.error(err);
                setError('Ocurrió un error en la búsqueda tradicional.');
                setResults([]);
            } finally {
                setLoading(false);
            }
        };

        const fetchSemantic = async () => {
            setSemanticLoading(true);
            setSemanticError(null);
            try {
                const semanticData = await semanticSearch(debouncedQuery);
                setSemanticResults(semanticData);
            } catch (err) {
                console.error(err);
                setSemanticError('Ocurrió un error en la búsqueda semántica.');
                setSemanticResults([]);
            } finally {
                setSemanticLoading(false);
            }
        };

        if (debouncedQuery.length >= 8) {
            setHasSearched(true);
            // Execute both searches in parallel
            fetchOriginal();
            fetchSemantic();
        } else {
            setResults([]);
            setSemanticResults([]);
            setHasSearched(false);
            setError(null);
            setSemanticError(null);
        }
    }, [debouncedQuery]);

    return (
        <div className="w-full max-w-[1400px] mx-auto px-4 py-8">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {/* Header / Search Area - HPTU Style (Blue/White) */}
                <div className="bg-[#005CA9] p-6 md:p-8">
                    <h2 className="text-xl font-bold text-white mb-4">Consulta de Medicamentos y artículos de Droguería</h2>
                    <div className="relative max-w-3xl">
                        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                            <Search className="h-5 w-5 text-gray-400" />
                        </div>
                        <input
                            type="text"
                            className="w-full pl-10 pr-4 py-3 rounded-md text-gray-900 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-300 placeholder-gray-500"
                            placeholder="Escribe el nombre del medicamento (mínimo 8 caracteres)..."
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                        {(loading || semanticLoading) && (
                            <div className="absolute inset-y-0 right-3 flex items-center">
                                <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                            </div>
                        )}
                    </div>
                    <div className="flex justify-between items-center mt-2">
                        <p className="text-blue-100 text-sm">
                            Dose Mind es tu asistente profesional para la consulta inteligente de medicamentos
                        </p>
                        {hasSearched && (
                            <button
                                onClick={handleClearSearch}
                                className="text-xs font-medium text-white hover:text-blue-200 underline flex items-center gap-1"
                            >
                                Nueva búsqueda
                            </button>
                        )}
                    </div>
                </div>

                {/* Results Area */}
                <div className="bg-gray-50 p-6 min-h-[400px]">
                    {!hasSearched ? (
                        <div className="text-center py-16 text-gray-400">
                            <Search className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                            <p>Ingresa el nombre del medicamento arriba para ver disponibilidad.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {/* Traditional Results Column */}
                            <div className="flex flex-col gap-4">
                                <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                                    <h3 className="font-bold text-gray-700 uppercase tracking-wider text-[11px]">Búsqueda Tradicional</h3>
                                    {results.length > 0 && (
                                        <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold">
                                            {results.length} coincidencias
                                        </span>
                                    )}
                                </div>

                                {loading ? (
                                    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                                        <Loader2 className="h-8 w-8 mb-2 animate-spin text-[#005CA9]" />
                                        <p className="text-sm">Buscando...</p>
                                    </div>
                                ) : error ? (
                                    <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-100 text-sm">
                                        <p>{error}</p>
                                    </div>
                                ) : results.length > 0 ? (
                                    <div className="space-y-3">
                                        {results.map((drug, index) => (
                                            <DrugCard key={`trad-${drug.id || index}`} drug={drug} />
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-gray-400 border border-dashed border-gray-200 rounded-lg">
                                        <Pill className="h-8 w-8 mx-auto mb-2 text-gray-200" />
                                        <p className="text-sm">No se encontraron artículos</p>
                                    </div>
                                )}
                            </div>

                            {/* Semantic Results Column */}
                            <div className="flex flex-col gap-4">
                                <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                                    <h3 className="font-bold text-[#005CA9] uppercase tracking-wider text-[11px]">Búsqueda Semántica (IA)</h3>
                                    {semanticResults.length > 0 && (
                                        <span className="text-[10px] bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-bold">
                                            {semanticResults.length} resultados
                                        </span>
                                    )}
                                </div>

                                {semanticLoading ? (
                                    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                                        <Loader2 className="h-8 w-8 mb-2 animate-spin text-indigo-600" />
                                        <p className="text-sm">Analizando con IA...</p>
                                    </div>
                                ) : semanticError ? (
                                    <div className="p-4 bg-amber-50 text-amber-700 rounded-lg border border-amber-100 text-sm">
                                        <p>{semanticError}</p>
                                    </div>
                                ) : semanticResults.length > 0 ? (
                                    <div className="space-y-3">
                                        {semanticResults.map((drug, index) => (
                                            <DrugCard key={`sem-${drug.id || index}`} drug={drug} />
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-gray-400 border border-dashed border-gray-200 rounded-lg">
                                        <Pill className="h-8 w-8 mx-auto mb-2 text-gray-200" />
                                        <p className="text-sm">No se encontraron resultados semánticos</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
