import { useState, useRef } from 'react';
import { Send, Clock, Cloud, Trash2, StopCircle, RefreshCw, ChevronDown, Search as SearchIcon } from 'lucide-react';
import { semanticSearch, type DrugResult } from '../api/search';
import { DrugCard } from './DrugCard';

const MODELS = [
    "gemma3:27b",
    "qwen3.5:397b",
    "gpt-oss:120b",
    "devstral-2:123b",
    "qwen3-next:80b",
    "mistral-large-3:675b",
    "deepseek-v3.2"
].sort((a, b) => a.localeCompare(b));

interface LLMResponseState {
    model: string;
    response: string;
    isLoading: boolean;
    time: number;
    error: string | null;
}

interface ComparisonBaseProps {
    title: string;
    endpoint: string;
    placeholder?: string;
}

export const ComparisonBase = ({ title, endpoint, placeholder }: ComparisonBaseProps) => {
    const [question, setQuestion] = useState('');
    const [llmState, setLlmState] = useState<LLMResponseState>({
        model: MODELS[0],
        response: '',
        isLoading: false,
        time: 0,
        error: null
    });

    const [searchResults, setSearchResults] = useState<DrugResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searchError, setSearchError] = useState<string | null>(null);

    const [totalTime, setTotalTime] = useState(0);
    const [isConsulting, setIsConsulting] = useState(false);

    const timerInterval = useRef<any>(null);
    const startTimeRef = useRef<number>(0);

    const stopTimer = () => {
        if (timerInterval.current) clearInterval(timerInterval.current);
    };

    const startConsultation = async () => {
        if (!question.trim()) return;

        setIsConsulting(true);
        setTotalTime(0);
        startTimeRef.current = Date.now();

        // Reset state
        setLlmState(prev => ({ ...prev, response: '', isLoading: true, time: 0, error: null }));

        let hasTriggeredSearch = false;

        // Start individual timer
        const start = Date.now();
        timerInterval.current = setInterval(() => {
            setLlmState(prev => ({ ...prev, time: (Date.now() - start) / 1000 }));
        }, 100);

        try {
            await doFetch(llmState.model, (text) => {
                if (!hasTriggeredSearch && text.trim()) {
                    handleSearch();
                    hasTriggeredSearch = true;
                }
                setLlmState(prev => ({ ...prev, response: prev.response + text }));
            }, () => {
                stopTimer();
                setLlmState(prev => ({ ...prev, isLoading: false }));
            }, (err) => {
                stopTimer();
                setLlmState(prev => ({ ...prev, isLoading: false, error: err }));
            });
        } catch (error) {
            console.error(error);
        } finally {
            setTotalTime((Date.now() - startTimeRef.current) / 1000);
            setIsConsulting(false);
        }
    };

    const handleSearch = async () => {
        if (!question.trim()) return;
        setIsSearching(true);
        setSearchError(null);
        try {
            const results = await semanticSearch(question);
            setSearchResults(results);
        } catch (error: any) {
            setSearchError(error.message || 'Error en la búsqueda semántica');
        } finally {
            setIsSearching(false);
        }
    };

    const doFetch = async (
        model: string,
        onChunk: (text: string) => void,
        onDone: () => void,
        onError: (err: string) => void
    ) => {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pregunta: question,
                    inference_model: `${model}-cloud`,
                    instancia: 'nube'
                })
            });

            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error('No readable stream available');

            const decoder = new TextDecoder();
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                onChunk(chunk);
            }
            onDone();
        } catch (err: any) {
            console.error(err);
            onError(err.message || 'Error en la conexión');
        }
    };

    const handleClear = () => {
        setQuestion('');
        setLlmState(prev => ({ ...prev, response: '', time: 0, error: null }));
        setSearchResults([]);
        setSearchError(null);
        setTotalTime(0);
        stopTimer();
    };

    return (
        <div className="w-full max-w-[1400px] mx-auto px-4 py-6">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden flex flex-col min-h-[80vh]">
                {/* Header Section */}
                <div className="bg-gradient-to-r from-[#005CA9] to-[#003d73] py-6 px-8 text-white">
                    <div className="flex flex-col md:flex-row md:items-end gap-6">
                        <div className="flex-1">
                            <label htmlFor="question" className="block text-sm font-medium text-blue-100 mb-2 uppercase tracking-wider">
                                {title}
                            </label>
                            <div className="relative group">
                                <textarea
                                    id="question"
                                    rows={3}
                                    className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-blue-200/60 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:bg-white/15 transition-all resize-none"
                                    placeholder={placeholder || "Escribe tu pregunta aquí..."}
                                    value={question}
                                    onChange={(e) => setQuestion(e.target.value)}
                                />
                                <div className="absolute top-2 right-2 flex gap-2">
                                    <button
                                        onClick={handleClear}
                                        className="p-2 text-blue-200 hover:text-white hover:bg-white/10 rounded-lg transition-all"
                                        title="Limpiar consulta"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            <button
                                onClick={startConsultation}
                                disabled={isConsulting || !question.trim()}
                                className={`flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-bold transition-all shadow-lg hover:shadow-blue-500/20 active:scale-95 ${isConsulting || !question.trim()
                                    ? 'bg-blue-300 text-blue-100 cursor-not-allowed'
                                    : 'bg-white text-[#005CA9] hover:bg-blue-50'
                                    }`}
                            >
                                {isConsulting ? (
                                    <>
                                        <RefreshCw className="h-5 w-5 animate-spin" />
                                        Consultando...
                                    </>
                                ) : (
                                    <>
                                        <Send className="h-5 w-5" />
                                        Consultar
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {totalTime > 0 && !isConsulting && (
                        <div className="mt-4 flex items-center gap-2 text-blue-100 text-sm animate-fade-in">
                            <Clock className="h-4 w-4" />
                            <span>Tiempo de respuesta: <strong>{totalTime.toFixed(2)}s</strong></span>
                        </div>
                    )}
                </div>

                {/* Main Content Section */}
                <div className="flex-1 flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x divide-gray-200">
                    {/* Left Panel: LLM Response */}
                    <div className="flex-1 flex flex-col min-w-0">
                        <div className="px-6 py-2 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                            <span className="text-[10px] font-bold text-[#005CA9] uppercase tracking-widest">Respuesta IA</span>
                            <div className="flex items-center gap-2 text-xs font-bold text-blue-600">
                                <Clock className="h-3 w-3" />
                                {llmState.time.toFixed(2)}s
                            </div>
                        </div>

                        <div className="px-8 py-6 bg-gray-50/50 border-b border-gray-200">
                            <div className="flex flex-col gap-2 max-w-[260px]">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-1">Modelo de IA</span>
                                <div className="relative">
                                    <select
                                        className="w-full pl-3 pr-10 py-2.5 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 appearance-none focus:ring-2 focus:ring-blue-100 focus:border-[#005CA9] outline-none transition-all cursor-pointer shadow-sm hover:border-gray-300"
                                        value={llmState.model}
                                        onChange={(e) => setLlmState(prev => ({ ...prev, model: e.target.value }))}
                                        disabled={llmState.isLoading}
                                    >
                                        {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#005CA9] pointer-events-none" />
                                </div>
                            </div>
                        </div>

                        <div className="flex-1 p-6 overflow-y-auto bg-white relative">
                            {llmState.error ? (
                                <div className="flex flex-col items-center justify-center h-full text-red-500 gap-2">
                                    <StopCircle className="h-10 w-10 text-red-200" />
                                    <p className="font-medium">{llmState.error}</p>
                                </div>
                            ) : llmState.isLoading && !llmState.response ? (
                                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
                                    <div className="flex gap-1.5">
                                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                        <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                                    </div>
                                    <p className="text-sm">Generando respuesta...</p>
                                </div>
                            ) : llmState.response ? (
                                <div className="prose prose-blue max-w-none animate-fade-in">
                                    <div className="whitespace-pre-wrap text-gray-800 leading-relaxed font-sans">
                                        {llmState.response}
                                        {llmState.isLoading && <span className="inline-block w-2 h-5 bg-blue-400 ml-1 animate-pulse align-middle"></span>}
                                    </div>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full text-gray-300 gap-3 grayscale opacity-40">
                                    <Cloud className="h-12 w-12" />
                                    <p className="text-sm font-medium">La respuesta de la IA aparecerá aquí</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right Panel: Semantic Search Results */}
                    <div className="flex-1 flex flex-col min-w-0 bg-gray-50/30">
                        <div className="px-6 py-2 bg-gray-50 border-b border-gray-200">
                            <span className="text-[10px] font-bold text-[#005CA9] uppercase tracking-widest">Medicamentos Relacionados</span>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4">
                            {isSearching ? (
                                <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
                                    <RefreshCw className="h-8 w-8 animate-spin text-blue-400" />
                                    <p className="text-sm">Buscando en catálogo...</p>
                                </div>
                            ) : searchError ? (
                                <div className="p-4 bg-red-50 border border-red-100 rounded-xl text-red-600 text-sm flex gap-3">
                                    <StopCircle className="h-5 w-5 flex-shrink-0" />
                                    <p>{searchError}</p>
                                </div>
                            ) : searchResults.length > 0 ? (
                                <div className="flex flex-col gap-3">
                                    {searchResults.map((drug) => (
                                        <DrugCard key={drug.id} drug={drug} />
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-full text-gray-300 gap-4 text-center px-8">
                                    <div className="p-4 bg-white rounded-full shadow-sm">
                                        <SearchIcon className="h-8 w-8 text-blue-200" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-gray-400">Sin resultados</p>
                                        <p className="text-xs text-gray-400 mt-1">Se mostrarán medicamentos mencionados en tu consulta</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
