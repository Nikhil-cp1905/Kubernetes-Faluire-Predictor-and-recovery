// src/App.jsx
import React from 'react';
import { useState } from "react";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!query.trim()) return;

    const userMessage = { type: "user", text: query };
    setChatHistory((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      const response = await fetch("https://kubernetes-failure-predictor.onrender.com/k8s-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userQuery: query }),
      });

      const data = await response.json();
      const botMessage = { type: "bot", text: data.reply || "No response received." };
      setChatHistory((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMsg = { type: "bot", text: "Error contacting backend." };
      setChatHistory((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">Kubernetes ChatBot</div>

      <div className="chat-body">
        {chatHistory.map((msg, index) => (
          <div key={index} className={`chat-bubble ${msg.type}`}>
            {msg.type === "user" ? "🧑‍💻" : "🤖"} {msg.text}
          </div>
        ))}
        {loading && (
          <div className="chat-bubble bot">🤖 Typing...</div>
        )}
      </div>

      <div className="chat-footer">
        <input
          type="text"
          placeholder="Type your Kubernetes issue..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
        />
        <button onClick={handleAsk} disabled={loading}>
          {loading ? "..." : "➤"}
        </button>
      </div>
    </div>
  );
}

export default App;

