import type { InstallResponse } from "@/lib/types";
import ProductCard from "./ProductCard";

interface Props {
  data: InstallResponse;
}

export default function InstallWidget({ data }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-gray-700">{data.text}</p>

      {data.part ? (
        <ProductCard product={data.part} />
      ) : data.part_image_url ? (
        <img
          src={data.part_image_url}
          alt="Part"
          className="w-16 h-16 object-contain rounded border border-gray-200"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      ) : null}

      {data.steps.length > 0 && (
        <ol className="flex flex-col gap-3">
          {data.steps.map((step) => (
            <li key={step.step_number} className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#0066cc] text-white text-xs font-bold flex items-center justify-center mt-0.5">
                {step.step_number}
              </span>
              <div className="flex flex-col gap-1">
                <p className="text-sm text-gray-800">{step.instruction}</p>
                {step.caution && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                    ⚠ {step.caution}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {data.sources.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-gray-500">Sources</span>
          {data.sources.map((src, i) => (
            <a
              key={src}
              href={src}
              target="_blank"
              rel="noreferrer noopener"
              className="text-xs text-[#0066cc] hover:underline"
            >
              PartSelect Guide {i + 1} →
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
