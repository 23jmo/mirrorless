"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { socket } from "@/lib/socket";

type MessageRole = "user" | "mira" | "system";

interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
}

interface ProductItem {
  title: string;
  price: string;
  source: string;
  image_url: string;
  link: string;
  rating?: number;
  rating_count?: number;
}

interface ProductCard {
  id: string;
  query: string;
  items: ProductItem[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPage() {
  const [mirrorId, setMirrorId] = useState(
    process.env.NEXT_PUBLIC_MIRROR_ID || "MIRROR-A1"
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, products, scrollToBottom]);

  // Socket connection, auto-join, & listeners
  useEffect(() => {
    socket.connect();

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("join_room", { mirror_id: mirrorId });
    });
    socket.on("disconnect", () => setConnected(false));

    // Poke messages arrive as mirror_text events (complete messages, not chunks)
    socket.on("mirror_text", (data: { text: string }) => {
      setMessages((prev) => [
        ...prev,
        { id: `mira-${Date.now()}`, role: "mira", text: data.text },
      ]);
    });

    // Product cards from Poke's present_items tool
    socket.on(
      "tool_result",
      (data: { type: string; query?: string; items: ProductItem[] }) => {
        if (data.type === "clothing_results" && data.items?.length > 0) {
          setProducts((prev) => [
            ...prev,
            {
              id: `product-${Date.now()}`,
              query: data.query || "",
              items: data.items,
            },
          ]);
        }
      }
    );

    // Confirmation that our message was relayed to Poke
    socket.on("chat_sent", (data: { text: string }) => {
      setSending(false);
      console.log("[chat] Message relayed to Poke:", data.text);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("mirror_text");
      socket.off("tool_result");
      socket.off("chat_sent");
      socket.disconnect();
    };
  }, [mirrorId]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput("");

    // Show user message immediately
    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", text },
    ]);

    setSending(true);
    try {
      const resp = await fetch(`${API_URL}/api/mirror/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mirror_id: mirrorId, text }),
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
    } catch (err) {
      setSending(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: "system",
          text: `Failed to send: ${err instanceof Error ? err.message : "Unknown error"}`,
        },
      ]);
    }
  }, [input, sending, mirrorId]);

  return (
    <main
      style={{
        maxWidth: 640,
        margin: "0 auto",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "#0a0a0a",
        color: "#e0e0e0",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid #222",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "1.25rem", color: "#fff" }}>
            Chat with Mira
          </h1>
          <span
            style={{
              fontSize: "0.75rem",
              color: connected ? "#4caf50" : "#f44336",
            }}
          >
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>

        {/* Mirror ID */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label
            style={{ fontSize: "0.8rem", color: "#888", whiteSpace: "nowrap" }}
          >
            Mirror ID
          </label>
          <input
            type="text"
            value={mirrorId}
            onChange={(e) => setMirrorId(e.target.value)}
            style={{
              flex: 1,
              padding: "6px 10px",
              background: "#1a1a1a",
              border: "1px solid #333",
              borderRadius: 6,
              color: "#e0e0e0",
              fontSize: "0.8rem",
              fontFamily: "monospace",
            }}
          />
        </div>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              alignSelf:
                msg.role === "user"
                  ? "flex-end"
                  : msg.role === "system"
                    ? "center"
                    : "flex-start",
              maxWidth: msg.role === "system" ? "90%" : "80%",
              padding: "10px 14px",
              borderRadius: 12,
              fontSize: "0.9rem",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              ...(msg.role === "user"
                ? { background: "#6b21a8", color: "#fff" }
                : msg.role === "mira"
                  ? {
                      background: "#1a1a2e",
                      color: "#e0e0e0",
                      border: "1px solid #2a2a4e",
                    }
                  : {
                      background: "#111",
                      color: "#888",
                      fontSize: "0.8rem",
                      fontStyle: "italic",
                    }),
            }}
          >
            {msg.role === "mira" && (
              <div
                style={{
                  fontSize: "0.7rem",
                  color: "#9b59b6",
                  marginBottom: 4,
                  fontWeight: 600,
                }}
              >
                Mira
              </div>
            )}
            {msg.text}
          </div>
        ))}

        {/* Product cards */}
        {products.map((card) => (
          <div key={card.id} style={{ alignSelf: "flex-start", maxWidth: "90%" }}>
            {card.query && (
              <div style={{ fontSize: "0.75rem", color: "#888", marginBottom: 6 }}>
                Results for &quot;{card.query}&quot;
              </div>
            )}
            <div
              style={{
                display: "flex",
                gap: 10,
                overflowX: "auto",
                paddingBottom: 4,
              }}
            >
              {card.items.map((item, i) => (
                <a
                  key={i}
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    minWidth: 160,
                    background: "#1a1a2e",
                    border: "1px solid #2a2a4e",
                    borderRadius: 10,
                    padding: 10,
                    textDecoration: "none",
                    color: "#e0e0e0",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}
                >
                  {item.image_url && (
                    <img
                      src={item.image_url}
                      alt={item.title}
                      style={{
                        width: "100%",
                        height: 120,
                        objectFit: "contain",
                        borderRadius: 6,
                        background: "#fff",
                      }}
                    />
                  )}
                  <div style={{ fontSize: "0.8rem", fontWeight: 600 }}>
                    {item.title.length > 50
                      ? item.title.slice(0, 50) + "..."
                      : item.title}
                  </div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      color: "#9b59b6",
                      fontWeight: 700,
                    }}
                  >
                    {item.price}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "#888" }}>
                    {item.source}
                    {item.rating ? ` | ${item.rating}★` : ""}
                  </div>
                </a>
              ))}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Text input — always active */}
      <div
        style={{
          display: "flex",
          gap: 8,
          padding: "12px 20px 20px",
          borderTop: "1px solid #222",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Type a message..."
          style={{
            flex: 1,
            padding: "10px 14px",
            background: "#1a1a1a",
            border: "1px solid #333",
            borderRadius: 8,
            color: "#e0e0e0",
            fontSize: "0.9rem",
          }}
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || sending}
          style={btnStyle(!input.trim() || sending ? "#333" : "#6b21a8")}
        >
          {sending ? "..." : "Send"}
        </button>
      </div>
    </main>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    padding: "8px 16px",
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: bg === "#333" ? "default" : "pointer",
    fontSize: "0.85rem",
    fontWeight: 600,
    whiteSpace: "nowrap",
  };
}
