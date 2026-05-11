"use client";
import type { Thread } from "@/lib/types";

interface Props {
  threads: Thread[];
  currentThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
}

export default function ThreadList({ threads, currentThreadId, onSelectThread, onCreateThread }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-3 border-b border-gray-200">
        <button
          onClick={onCreateThread}
          className="w-full bg-[#1d6b64] hover:bg-[#165a54] text-white text-sm font-medium rounded-lg px-3 py-2 transition-colors"
        >
          + New Conversation
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {threads.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-6">No conversations yet</p>
        )}
        {threads.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelectThread(t.id)}
            className={`w-full text-left px-3 py-3 border-b border-gray-100 hover:bg-[#f0f9f8] transition-colors ${
              t.id === currentThreadId ? "bg-[#e0f2f0] border-l-2 border-l-[#1d6b64]" : ""
            }`}
          >
            <p className="text-sm font-medium text-gray-800 truncate">{t.title}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {new Date(t.updated_at).toLocaleDateString()}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
