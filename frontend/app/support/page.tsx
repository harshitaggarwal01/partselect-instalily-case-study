"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { listThreads, createThread, getThreadMessages } from "@/lib/threadClient";
import ThreadList from "@/components/ThreadList";
import CartSidebar from "@/components/CartSidebar";
import ChatWindow from "@/components/ChatWindow/ChatWindow";
import type { Thread } from "@/lib/types";

export default function SupportPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [initialMessages, setInitialMessages] = useState<{ role: string; content: string }[]>([]);
  const initialized = useRef(false);

  // Auth guard
  useEffect(() => {
    if (user === null && typeof window !== "undefined") {
      const t = setTimeout(() => {
        if (!localStorage.getItem("auth_token")) {
          router.replace("/login");
        }
      }, 100);
      return () => clearTimeout(t);
    }
  }, [user, router]);

  // Load threads on mount
  useEffect(() => {
    if (!token || initialized.current) return;
    initialized.current = true;
    (async () => {
      const fetched = await listThreads(token);
      setThreads(fetched);
      const lastId = localStorage.getItem("lastThreadId");
      const found = fetched.find(t => t.id === lastId) ?? fetched[0];
      if (found) {
        setCurrentThreadId(found.id);
        const msgs = await getThreadMessages(token, found.id);
        setInitialMessages(msgs);
      }
    })();
  }, [token]);

  const handleSelectThread = async (id: string) => {
    if (!token) return;
    setCurrentThreadId(id);
    localStorage.setItem("lastThreadId", id);
    const msgs = await getThreadMessages(token, id);
    setInitialMessages(msgs);
  };

  const handleCreateThread = async () => {
    if (!token) return;
    const thread = await createThread(token);
    setThreads(prev => [thread, ...prev]);
    setCurrentThreadId(thread.id);
    setInitialMessages([]);
    localStorage.setItem("lastThreadId", thread.id);
  };

  const handleThreadCreated = (newId: string) => {
    setCurrentThreadId(newId);
    localStorage.setItem("lastThreadId", newId);
    if (token) listThreads(token).then(setThreads);
  };

  if (!user) {
    return <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">Loading&hellip;</div>;
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left: Thread list */}
      <aside className="hidden md:flex flex-col w-56 border-r border-gray-200 bg-white shrink-0">
        <div className="px-3 py-2 border-b border-gray-200 bg-[#f5f5f5]">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Conversations</p>
        </div>
        <ThreadList
          threads={threads}
          currentThreadId={currentThreadId}
          onSelectThread={handleSelectThread}
          onCreateThread={handleCreateThread}
        />
      </aside>

      {/* Center: Chat */}
      <main className="flex flex-col flex-1 overflow-hidden">
        {/* Amber banner */}
        <div className="bg-[#f0a020] px-4 py-2 shrink-0 flex items-center justify-between">
          <span className="text-white font-semibold text-sm">PartSelect Support</span>
          <span className="text-white/80 text-xs">Refrigerator &amp; Dishwasher Parts</span>
        </div>
        <ChatWindow
          currentThreadId={currentThreadId}
          initialMessages={initialMessages}
          onThreadCreated={handleThreadCreated}
        />
      </main>

      {/* Right: Cart */}
      <aside className="hidden md:flex flex-col w-64 border-l border-gray-200 bg-white shrink-0">
        <CartSidebar />
      </aside>
    </div>
  );
}
