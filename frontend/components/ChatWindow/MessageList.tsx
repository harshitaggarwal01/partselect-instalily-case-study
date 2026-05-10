import type { FrontendMessage } from "@/lib/types";
import CompatWidget from "../CompatWidget";
import InstallWidget from "../InstallWidget";
import ProductCard from "../ProductCard";
import TroubleshootWidget from "../TroubleshootWidget";

interface Props {
  messages: FrontendMessage[];
}

export default function MessageList({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center gap-3 px-6 py-12">
        <div className="w-12 h-12 rounded-full bg-[#e6f0fa] flex items-center justify-center">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0066cc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">
          Ask me about refrigerator or dishwasher parts
        </p>
        <p className="text-xs text-gray-400 max-w-xs">
          Try asking how to install a part, check compatibility, or troubleshoot an issue.
        </p>
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
