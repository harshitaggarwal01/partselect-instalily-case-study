import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-white px-6">
      <main className="flex flex-col items-center text-center max-w-2xl gap-8 py-24">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#0066cc] flex items-center justify-center">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-[#0066cc] tracking-wide uppercase">
            PartSelect Support
          </span>
        </div>

        <h1 className="text-4xl font-bold text-gray-900 leading-tight">
          Smart Assistant for Refrigerator &amp; Dishwasher Parts
        </h1>

        <p className="text-lg text-gray-500 max-w-lg">
          Get instant help finding parts, checking compatibility, installing
          components, and troubleshooting common appliance issues.
        </p>

        <ul className="flex flex-col sm:flex-row gap-4 text-sm text-gray-700 font-medium">
          <li className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-[#e6f0fa] text-[#0066cc] flex items-center justify-center text-xs font-bold">
              ✓
            </span>
            Step-by-step install guides
          </li>
          <li className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-[#e6f0fa] text-[#0066cc] flex items-center justify-center text-xs font-bold">
              ✓
            </span>
            Compatibility checks
          </li>
          <li className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-[#e6f0fa] text-[#0066cc] flex items-center justify-center text-xs font-bold">
              ✓
            </span>
            Troubleshooting help
          </li>
        </ul>

        <Link
          href="/support"
          className="inline-flex items-center gap-2 rounded-full bg-[#0066cc] px-8 py-3 text-white font-semibold text-base hover:bg-[#0055aa] transition-colors"
        >
          Start a conversation
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </Link>

        <p className="text-xs text-gray-400">
          Refrigerator &amp; dishwasher parts only &mdash; powered by AI
        </p>
      </main>
    </div>
  );
}
