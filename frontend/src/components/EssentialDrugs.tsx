import { ComparisonBase } from './ComparisonBase';

export const EssentialDrugs = () => {
    return (
        <ComparisonBase
            title="Medicamentos Esenciales"
            endpoint="/api/chat"
            placeholder="Ej: cuales son las indicaciones de Gluconato de CALCIO inyectable..."
        />
    );
};
