"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function Header() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <header className="w-full shrink-0">
      {/* Row 1: Logo + utility */}
      <div className="bg-white px-4 py-2 flex items-center justify-between border-b border-gray-200">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-9 h-9 bg-[#f0a020] rounded-sm flex items-center justify-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9,22 9,12 15,12 15,22"/>
            </svg>
          </div>
          <div>
            <span className="font-bold text-[#1a1a1a] text-lg leading-tight">PartSelect</span>
            <div className="bg-[#f0a020] text-white text-[10px] font-medium px-1.5 py-0.5 rounded-sm leading-tight">
              Here to help since 1999
            </div>
          </div>
        </Link>
        <div className="hidden md:flex items-center gap-5 text-sm text-gray-700">
          <Link href="/support" className="flex items-center gap-1 hover:text-[#1d6b64]">
            <span>&#128172;</span> Start Chat
          </Link>
          <span className="flex items-center gap-1 text-gray-500 cursor-default">
            <span>&#128230;</span> Order Status
          </span>
          {user ? (
            <span className="flex items-center gap-2 text-gray-700">
              <span>&#128100;</span>
              <span className="font-medium">{user.username}</span>
              <button
                onClick={handleLogout}
                className="text-xs text-red-500 hover:text-red-700 underline"
              >
                Logout
              </button>
            </span>
          ) : (
            <Link href="/login" className="flex items-center gap-1 hover:text-[#1d6b64]">
              <span>&#128100;</span> Sign In
            </Link>
          )}
          <span className="text-gray-500 cursor-default">&#128722;</span>
        </div>
      </div>

      {/* Row 2: Nav + search */}
      <div className="bg-[#1d6b64] px-4 py-2 flex items-center justify-between">
        <nav className="hidden md:flex items-center gap-5 text-sm text-white font-medium">
          <span className="cursor-default hover:text-[#a8d5d1] flex items-center gap-1">Departments &#9660;</span>
          <span className="cursor-default hover:text-[#a8d5d1] flex items-center gap-1">Brands &#9660;</span>
          <Link href="#" className="hover:text-[#a8d5d1]">Symptoms</Link>
          <Link href="#" className="hover:text-[#a8d5d1]">Blog</Link>
          <Link href="#" className="hover:text-[#a8d5d1]">Repair Help</Link>
          <Link href="https://www.partselect.com/Refrigerators/" target="_blank" rel="noopener noreferrer" className="hover:text-[#a8d5d1]">Refrigerator Finder</Link>
          <Link href="https://www.partselect.com/Dishwashers/" target="_blank" rel="noopener noreferrer" className="hover:text-[#a8d5d1]">Dishwasher Finder</Link>
        </nav>
        <form className="flex items-center gap-0 max-w-xs w-full md:w-auto" onSubmit={e => e.preventDefault()}>
          <input
            type="text"
            placeholder="Search model or part number"
            className="flex-1 px-3 py-1.5 text-sm rounded-l border-0 outline-none text-gray-800"
            style={{ minWidth: 0 }}
          />
          <button
            type="submit"
            className="bg-[#155a54] hover:bg-[#0f4540] px-3 py-1.5 rounded-r text-white text-sm"
          >
            &#128269;
          </button>
        </form>
      </div>

      {/* Row 3: Trust bar */}
      <div className="bg-[#f5f5f5] border-b border-gray-200 px-4 py-1.5 hidden md:flex items-center justify-center gap-8 text-xs text-gray-600">
        <span>$ Price Match Guarantee</span>
        <span>&#128666; Fast Shipping</span>
        <span>&#10003; All Original Manufacturer Parts</span>
        <span>&#127885; 1 Year Warranty</span>
      </div>
    </header>
  );
}
