"use client";

import { useEffect, useRef, useState } from "react";
import { sendChat } from "@/lib/apiClient";
import type { FrontendMessage } from "@/lib/types";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

let idCounter = 0;
function uid() {
  return `msg-${++idCounter}`;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<FrontendMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSubmit(text: string) {
    setError(null);

    const userMsg: FrontendMessage = {
      id: uid(),
      role: "user",
      content: text,
    };

    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setIsLoading(true);

    try {
      const response = await sendChat(nextMessages);
      const assistantMsg: FrontendMessage = {
        id: uid(),
        role: "assistant",
        content: response.text,
        response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setError("Something went wrong. Please check that the backend is running and try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} />

        {isLoading && (
          <div className="flex justify-start px-4 pb-2">
            <div className="rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3">
              <span className="flex gap-1 items-center">
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="mx-4 mb-2 rounded-xl bg-red-50 border border-red-200 px-4 py-2.5 text-sm text-red-700">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <MessageInput onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}
