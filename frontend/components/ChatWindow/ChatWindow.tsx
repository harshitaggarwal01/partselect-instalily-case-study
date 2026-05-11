"use client";

import { useEffect, useRef, useState } from "react";
import { sendChat } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import type { FrontendMessage } from "@/lib/types";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

let idCounter = 0;
function uid() {
  return `msg-${++idCounter}`;
}

interface Props {
  currentThreadId?: string | null;
  initialMessages?: { role: string; content: string }[];
  onThreadCreated?: (id: string) => void;
}

export default function ChatWindow({ currentThreadId, initialMessages, onThreadCreated }: Props) {
  const { token } = useAuth();
  const [messages, setMessages] = useState<FrontendMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Session ID persists for the lifetime of this component instance (backward compat)
  const sessionId = useRef<string>(crypto.randomUUID());
  // Keep a ref to the latest initialMessages so the effect below can read it without being a dep
  const initialMessagesRef = useRef(initialMessages);
  useEffect(() => { initialMessagesRef.current = initialMessages; }, [initialMessages]);

  // When the thread switches, reload messages from initialMessages
  useEffect(() => {
    const msgs = initialMessagesRef.current;
    if (msgs && msgs.length > 0) {
      const hydrated: FrontendMessage[] = msgs.map((m) => ({
        id: uid(),
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      setMessages(hydrated);
    } else {
      setMessages([]);
    }
  }, [currentThreadId]); // re-run whenever the thread changes

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
      const response = await sendChat(
        nextMessages,
        sessionId.current,
        token ?? undefined,
        currentThreadId ?? undefined
      );
      const assistantMsg: FrontendMessage = {
        id: uid(),
        role: "assistant",
        content: response.text,
        response,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Notify parent if backend assigned a new thread
      if (response.thread_id && onThreadCreated && response.thread_id !== currentThreadId) {
        onThreadCreated(response.thread_id);
      }
    } catch {
      setError("Something went wrong. Please check that the backend is running and try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleExampleClick(text: string) {
    if (!isLoading) {
      handleSubmit(text);
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} onExampleClick={handleExampleClick} />

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
