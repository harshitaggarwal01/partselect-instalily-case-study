import type { CompatibilityResponse } from "@/lib/types";
import ProductCard from "./ProductCard";

interface Props {
  data: CompatibilityResponse;
}

const STATUS_CONFIG = {
  compatible: {
    label: "Compatible",
    bg: "bg-green-100",
    text: "text-green-800",
    border: "border-green-300",
    dot: "bg-green-500",
  },
  not_compatible: {
    label: "Not Compatible",
    bg: "bg-red-100",
    text: "text-red-800",
    border: "border-red-300",
    dot: "bg-red-500",
  },
  unknown: {
    label: "Unknown",
    bg: "bg-gray-100",
    text: "text-gray-700",
    border: "border-gray-300",
    dot: "bg-gray-400",
  },
};

export default function CompatWidget({ data }: Props) {
  const cfg = STATUS_CONFIG[data.status];

  return (
    <div className="flex flex-col gap-4">
      {/* Status pill */}
      <div
        className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 w-fit ${cfg.bg} ${cfg.border}`}
      >
        <span className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
        <span className={`text-sm font-bold ${cfg.text}`}>{cfg.label}</span>
        {data.model_number && (
          <span className={`text-sm ${cfg.text} opacity-70`}>
            for model {data.model_number}
          </span>
        )}
      </div>

      {data.part && <ProductCard product={data.part} />}

      {data.details && (
        <p className="text-sm text-gray-700 leading-relaxed">{data.details}</p>
      )}
    </div>
  );
}
