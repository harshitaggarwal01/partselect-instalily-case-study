"use client";

import { useState } from "react";
import type { TroubleshootingResponse } from "@/lib/types";

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
                <span className="text-sm text-gray-800 line-clamp-1 flex-1">
                  {step.description.length > 80
                    ? step.description.slice(0, 80) + "…"
                    : step.description}
                </span>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${openStep === idx ? "rotate-180" : ""}`}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
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

      {data.sources.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
          <span className="text-xs font-semibold text-gray-500">Sources</span>
          {data.sources.map((src) => (
            <a
              key={src}
              href={src}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#0066cc] hover:underline truncate"
            >
              {src}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
