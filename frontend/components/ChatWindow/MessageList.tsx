import type { FrontendMessage } from "@/lib/types";
import CompatWidget from "../CompatWidget";
import { MessageCircle } from "../Icons";
import InstallWidget from "../InstallWidget";
import ProductCard from "../ProductCard";
import TroubleshootWidget from "../TroubleshootWidget";

const EXAMPLE_PROMPTS = [
  "How do I install part PS11752778?",
  "Is PS11752778 compatible with model WDT780SAEM1?",
  "My refrigerator ice maker is not working",
  "What is part W10195682?",
];

interface Props {
  messages: FrontendMessage[];
  onExampleClick: (text: string) => void;
}

export default function MessageList({ messages, onExampleClick }: Props) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center gap-5 px-6 py-12">
        <div className="w-12 h-12 rounded-full bg-[#e6f0fa] flex items-center justify-center">
          <MessageCircle className="w-[22px] h-[22px] text-[#0066cc]" />
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-gray-700">
            Ask me about refrigerator or dishwasher parts
          </p>
          <p className="text-xs text-gray-400">
            Try one of the examples below or type your own question.
          </p>
        </div>
        <div className="flex flex-col gap-2 w-full max-w-sm">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onExampleClick(prompt)}
              className="w-full text-left text-sm text-[#0066cc] bg-[#e6f0fa] hover:bg-[#cce0f5] rounded-xl px-4 py-2.5 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 px-4 py-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          {msg.role === "user" ? (
            <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-[#0066cc] px-4 py-2.5 text-sm text-white leading-relaxed">
              {msg.content}
            </div>
          ) : (
            <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3 flex flex-col gap-3">
              {msg.response ? (
                <>
                  {msg.response.type === "install" && (
                    <InstallWidget data={msg.response} />
                  )}
                  {msg.response.type === "compatibility" && (
                    <CompatWidget data={msg.response} />
                  )}
                  {msg.response.type === "troubleshooting" && (
                    <TroubleshootWidget data={msg.response} />
                  )}
                  {msg.response.type === "product_info" && (
                    <div className="flex flex-col gap-3">
                      <p className="text-sm text-gray-700">{msg.response.text}</p>
                      {msg.response.products.map((p) => (
                        <ProductCard key={p.part_number} product={p} />
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-gray-700 leading-relaxed">{msg.content}</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
