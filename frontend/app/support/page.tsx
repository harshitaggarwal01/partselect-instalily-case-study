"use client";

import ChatWindow from "@/components/ChatWindow/ChatWindow";
import { MessageCircle } from "@/components/Icons";
import Link from "next/link";
import { useRef } from "react";

const INTENT_HINTS = [
  "How do I install part PS11752778?",
  "Is PS11752778 compatible with model WDT780SAEM1?",
  "My refrigerator ice maker is not working",
  "What is part W10195682?",
];

const TIPS = [
  "Use part numbers like PS11752778 for exact results",
  "Describe symptoms in plain language",
  "Mention your appliance model for compatibility checks",
];

export default function SupportPage() {
  const chatWindowRef = useRef<{ submit: (text: string) => void } | null>(null);

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white shrink-0">
        <Link href="/" className="flex items-center gap-2 text-[#0066cc] font-bold text-lg">
          <div className="w-7 h-7 rounded-full bg-[#0066cc] flex items-center justify-center">
            <MessageCircle className="w-[14px] h-[14px] text-white" />
          </div>
          PartSelect Support
        </Link>
        <span className="text-xs text-gray-400">Refrigerator &amp; Dishwasher Parts</span>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <main className="flex flex-col flex-1 overflow-hidden">
          <ChatWindow />
        </main>

        {/* Sidebar */}
        <aside className="hidden md:flex flex-col w-72 border-l border-gray-200 bg-gray-50 p-4 gap-6 shrink-0">
          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Try asking
            </h2>
            <ul className="flex flex-col gap-2">
              {INTENT_HINTS.map((hint) => (
                <li key={hint}>
                  <button
                    className="w-full text-left text-sm text-[#0066cc] bg-[#e6f0fa] hover:bg-[#cce0f5] rounded-lg px-3 py-2 transition-colors cursor-pointer"
                    onClick={() => {
                      const textarea = document.querySelector<HTMLTextAreaElement>(
                        "textarea[data-chat-input]"
                      );
                      if (textarea) {
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                          window.HTMLTextAreaElement.prototype,
                          "value"
                        )?.set;
                        nativeInputValueSetter?.call(textarea, hint);
                        textarea.dispatchEvent(new Event("input", { bubbles: true }));
                        textarea.focus();
                      }
                    }}
                  >
                    {hint}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Tips
            </h2>
            <ul className="flex flex-col gap-2">
              {TIPS.map((tip) => (
                <li key={tip} className="flex items-start gap-2 text-xs text-gray-500">
                  <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-[#0066cc] shrink-0" />
                  {tip}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Scope
            </h2>
            <p className="text-xs text-gray-500 leading-relaxed">
              This assistant covers <strong>refrigerator</strong> and{" "}
              <strong>dishwasher</strong> parts only. For other appliances,
              visit{" "}
              <a
                href="https://www.partselect.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#0066cc] underline"
              >
                partselect.com
              </a>
              .
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
