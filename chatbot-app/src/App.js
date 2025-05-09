import React, { useState } from 'react';
import './App.css';

function App() {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    setLoading(true);
    const res = await fetch('https://kubernetes-failure-predictor.onrender.com', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userQuery: input })
    });
    const data = await res.json();
    setResponse(data.reply);
    setLoading(false);
  };

  return (
    <div className="container">
      <h1>Kubernetes Chatbot</h1>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask your Kubernetes question..."
      />
      <button onClick={handleSend}>Send</button>
      {loading && <p>⏳ Getting advice...</p>}
      {response && <div className="response"><b>Remedies:</b><br />{response}</div>}
    </div>
  );
}

export default App;
