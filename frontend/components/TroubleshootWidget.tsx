"use client";

import { useState } from "react";
import type { TroubleshootingResponse } from "@/lib/types";
import { ChevronDown } from "@/components/Icons";

interface Props {
  data: TroubleshootingResponse;
}

export default function TroubleshootWidget({ data }: Props) {
  const [openStep, setOpenStep] = useState<number | null>(0);

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-700">{data.text}</p>

      {data.issue && (
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Issue: {data.issue}
        </p>
      )}

      {data.steps.length > 0 && (
        <div className="flex flex-col gap-1">
          {data.steps.map((step, idx) => (
            <div
              key={step.step_number}
              className="rounded-lg border border-gray-200 overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-left bg-white hover:bg-gray-50 transition-colors"
                onClick={() => setOpenStep(openStep === idx ? null : idx)}
              >
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#0066cc] text-white text-xs font-bold flex items-center justify-center">
                  {step.step_number}
                </span>
                <span className="text-sm text-gray-800 flex-1">
                  {step.title || `Step ${step.step_number}`}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-gray-400 transition-transform ${openStep === idx ? "rotate-180" : ""}`}
                />
              </button>
              {openStep === idx && (
                <div className="px-4 pb-3 pt-1 bg-gray-50 border-t border-gray-100">
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {data.part_suggestions && data.part_suggestions.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
          <span className="text-xs font-semibold text-gray-500">Related Parts</span>
          <div className="flex flex-wrap gap-2">
            {data.part_suggestions.map((part) => (
              <a
                key={part.part_number}
                href={part.url ?? `https://www.partselect.com/search.aspx?SearchTerm=${part.part_number}`}
                target="_blank"
                rel="noreferrer noopener"
                className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 hover:border-[#0066cc] hover:shadow-sm transition-all"
              >
                {part.image_url && (
                  <img
                    src={part.image_url}
                    alt={part.name}
                    className="w-10 h-10 object-contain flex-shrink-0"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                )}
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-[#0066cc]">{part.part_number}</span>
                  <span className="text-xs text-gray-600 max-w-[120px] truncate">{part.name}</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {data.sources.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
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
