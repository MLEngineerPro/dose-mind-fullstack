import type { DrugResult } from '../api/search';
import { Tag, MapPin, MessageCircle } from 'lucide-react';

interface DrugCardProps {
    drug: DrugResult;
}

export const DrugCard = ({ drug }: DrugCardProps) => {
    return (
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-4 rounded-lg border border-gray-100 hover:bg-blue-50 transition-colors cursor-pointer group">
            <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-gray-800 group-hover:text-[#005CA9] transition-colors">{drug.name}</h3>
                    {drug.code && (
                        <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-mono">
                                {drug.code}
                            </span>
                            {drug.score !== undefined && (
                                <span className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-bold border border-indigo-100">
                                    {(drug.score * 100).toFixed(2)}%
                                </span>
                            )}
                            {drug.group && (
                                <span className="text-[10px] bg-blue-50 text-[#005CA9] px-2 py-0.5 rounded-full font-medium border border-blue-100 italic">
                                    {drug.group}
                                </span>
                            )}
                        </div>
                    )}
                </div>
                {drug.dosage && (
                    <p className="text-sm text-gray-500">{drug.dosage}</p>
                )}
                {drug.stock !== 0 && (
                    <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                        <MapPin size={14} />
                        <span>{drug.pharmacy}</span>
                    </div>
                )}
                {drug.name.includes('[AR]') && drug.group !== 'N08' && (
                    <div className="mt-2 bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded-md text-xs font-semibold flex items-center gap-2">
                        <Tag size={12} className="text-amber-600" />
                        La venta solo se hace con fórmula médica
                    </div>
                )}
            </div>

            <div className="mt-3 sm:mt-0 flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                {drug.group === 'N08' ? (
                    <div className="text-right flex flex-col items-end">
                        <p className="text-xs text-gray-400 uppercase font-semibold mb-1">Información</p>
                        <a
                            href={`https://wa.me/573025869845?text=Deseo%20más%20información%20sobre%20${encodeURIComponent(drug.name)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-full text-xs font-bold transition-colors shadow-sm"
                        >
                            <MessageCircle size={14} />
                            Mayor información en...
                        </a>
                    </div>
                ) : (
                    <div className="text-right">
                        <p className="text-xs text-gray-400 uppercase font-semibold">Precio</p>
                        <p className="text-lg font-bold text-[#005CA9]">
                            {drug.price ? `$ ${drug.price.toLocaleString()}` : <span className="text-sm font-normal text-blue-400 italic">Consultar en droguería</span>}
                        </p>
                        {drug.stock !== undefined && (
                            drug.stock === 0 ? (
                                <p className="text-xs text-red-600 font-bold mt-1">No hay stock</p>
                            ) : drug.stock < 5 ? (
                                <p className="text-xs text-amber-600 font-bold mt-1">¡Disponibilidad baja!</p>
                            ) : (
                                <p className="text-xs text-green-600 mt-1">Disponible</p>
                            )
                        )}
                    </div>
                )}
                <button className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-full shadow-sm transition-all sm:hidden group-hover:block">
                    <Tag size={16} />
                </button>
            </div>
        </div>
    );
};
