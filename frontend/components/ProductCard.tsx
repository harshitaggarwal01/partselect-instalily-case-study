"use client";
import { useState } from "react";
import type { Product } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import { addToCart } from "@/lib/apiClient";

interface Props {
  product: Product;
}

export default function ProductCard({ product }: Props) {
  const { token } = useAuth();
  const [added, setAdded] = useState(false);
  const [adding, setAdding] = useState(false);

  const handleAddToCart = async () => {
    if (!token) return;
    setAdding(true);
    try {
      await addToCart(token, product.part_number);
      window.dispatchEvent(new CustomEvent("cart-updated"));
      setAdded(true);
      setTimeout(() => setAdded(false), 2000);
    } catch {
      // silently fail — user not logged in or network error
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="flex gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm max-w-sm">
      {product.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={product.image_url}
          alt={product.name}
          className="w-16 h-16 object-contain rounded-lg bg-gray-50 shrink-0"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      )}
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-xs font-mono text-gray-400">{product.part_number}</span>
        <span className="text-sm font-semibold text-gray-900 leading-snug">{product.name}</span>
        {product.price != null && (
          <span className="text-sm font-bold text-[#0066cc]">${product.price.toFixed(2)}</span>
        )}
        {product.url && (
          <a
            href={product.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 text-xs text-[#0066cc] hover:underline"
          >
            View on PartSelect &rarr;
          </a>
        )}
        {token && (
          <button
            onClick={handleAddToCart}
            disabled={adding}
            className={`mt-2 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors disabled:opacity-50 ${
              added
                ? "bg-green-100 text-green-700"
                : "bg-[#1d6b64] hover:bg-[#165a54] text-white"
            }`}
          >
            {added ? "Added!" : adding ? "Adding…" : "Add to Cart"}
          </button>
        )}
      </div>
    </div>
  );
}
