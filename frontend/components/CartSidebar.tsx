"use client";
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { getCart, removeFromCart, getCheckoutLinks } from "@/lib/apiClient";
import type { Cart } from "@/lib/types";

export default function CartSidebar() {
  const { user, token } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [checkoutLinks, setCheckoutLinks] = useState<string[]>([]);

  const fetchCart = useCallback(async () => {
    if (!token) return;
    const data = await getCart(token);
    if (data) setCart(data);
  }, [token]);

  useEffect(() => { fetchCart(); }, [fetchCart]);

  useEffect(() => {
    window.addEventListener("cart-updated", fetchCart);
    return () => window.removeEventListener("cart-updated", fetchCart);
  }, [fetchCart]);

  const handleRemove = async (partNumber: string) => {
    if (!token) return;
    const updated = await removeFromCart(token, partNumber);
    setCart(updated);
  };

  const handleCheckout = async () => {
    if (!token) return;
    const { links } = await getCheckoutLinks(token);
    setCheckoutLinks(links);
    setShowModal(true);
  };

  const confirmCheckout = () => {
    checkoutLinks.forEach(url => window.open(url, "_blank", "noopener,noreferrer"));
    setShowModal(false);
  };

  const total = cart?.items.reduce((sum, item) => sum + (item.price ?? 0) * item.quantity, 0) ?? 0;
  const itemCount = cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-[#1d6b64] px-3 py-3 shrink-0">
        <p className="text-white font-semibold text-sm">Your Cart ({itemCount})</p>
        {user && <p className="text-[#a8d5d1] text-xs">{user.username}</p>}
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {(!cart || cart.items.length === 0) && (
          <p className="text-xs text-gray-400 text-center mt-6">Cart is empty</p>
        )}
        {cart?.items.map((item) => (
          <div key={item.part_number} className="flex gap-2 bg-white border border-gray-200 rounded-lg p-2">
            {item.image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={item.image_url} alt={item.name} className="w-12 h-12 object-contain rounded shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-800 truncate">{item.name}</p>
              <p className="text-xs text-gray-500">{item.part_number}</p>
              {item.price != null && (
                <p className="text-xs font-semibold text-[#1a1a1a]">${item.price.toFixed(2)} &times; {item.quantity}</p>
              )}
            </div>
            <button
              onClick={() => handleRemove(item.part_number)}
              className="text-gray-400 hover:text-red-500 text-lg leading-none shrink-0 self-start"
              title="Remove"
            >&times;</button>
          </div>
        ))}
      </div>

      {/* Footer */}
      {cart && cart.items.length > 0 && (
        <div className="border-t border-gray-200 p-3 shrink-0">
          <div className="flex justify-between text-sm font-semibold text-gray-800 mb-3">
            <span>Estimated Total</span>
            <span>${total.toFixed(2)}</span>
          </div>
          <button
            onClick={handleCheckout}
            className="w-full bg-[#f0a020] hover:bg-[#d4890e] text-white font-semibold py-2 rounded-lg text-sm transition-colors"
          >
            Checkout on PartSelect
          </button>
        </div>
      )}

      {/* Checkout modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h2 className="font-bold text-gray-900 mb-2">Open on PartSelect?</h2>
            <p className="text-sm text-gray-600 mb-4">
              This will open {checkoutLinks.length} tab{checkoutLinks.length !== 1 ? "s" : ""} — one per item.
            </p>
            <div className="flex gap-2">
              <button onClick={confirmCheckout} className="flex-1 bg-[#1d6b64] text-white py-2 rounded-lg text-sm font-medium hover:bg-[#165a54]">
                Open tabs
              </button>
              <button onClick={() => setShowModal(false)} className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-200">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
