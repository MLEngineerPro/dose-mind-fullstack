import { ComparisonBase } from './ComparisonBase';

export const LLMComparison = () => {
    return (
        <ComparisonBase
            title="Consulta Multimodelo"
            endpoint="/api/chat/stream"
            placeholder="Escribe tu pregunta aquí..."
        />
    );
};
