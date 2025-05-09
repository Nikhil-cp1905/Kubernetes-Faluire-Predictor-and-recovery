import React, { useEffect, useState, useRef } from "react";
import { io } from "socket.io-client";

//updattte this when hosting it
const socket = io("http://localhost:5000");

function App() {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [stats, setStats] = useState({
    total_samples: 0,
    failures: 0,
    success_rate: "0%"
  });
  const [currentMetrics, setCurrentMetrics] = useState(null);
  const [remediationSteps, setRemediationSteps] = useState([]);
  const [currentSample, setCurrentSample] = useState(null);
  const logsEndRef = useRef(null);

  //autoscroll
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    socket.on("connect", () => {
      console.log("Connected to server");
      setIsConnected(true);
      setLogs(prev => [...prev, "🔌 Connected to backend server"]);
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
      setIsConnected(false);
      setLogs(prev => [...prev, "❌ Disconnected from backend server"]);//included the emoji to differentiate
    });

    socket.on("log", (data) => {
      setLogs((prevLogs) => [...prevLogs, data.message]);
    });

    socket.on("stats", (data) => {
      setStats(data);
    });

    socket.on("metrics", (data) => {
      setCurrentMetrics(data.metrics);
      setCurrentSample(data.sample);
    });

    socket.on("remediation", (data) => {
      setRemediationSteps(data.steps);
      setCurrentSample(data.sample);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("log");
      socket.off("stats");
      socket.off("metrics");
      socket.off("remediation");
    };
  }, []);

  const startAnalysis = () => {
    setIsAnalyzing(true);
    setLogs([]);
    setRemediationSteps([]);
    setCurrentMetrics(null);
    socket.emit("start_analysis");
  };

  const downloadLogs = () => {
    const blob = new Blob([logs.join("\n")], { type: "text/plain" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "k8s_remediation_logs.txt";
    a.click();
  };

  const formatPercentage = (value) => {
    if (typeof value === 'number') {
      return value.toFixed(2) + '%';
    }
    return value;
  };

  return (
    <div style={{ 
      padding: "2rem", 
      fontFamily: "monospace", 
      background: "#0f172a", 
      color: "#f8fafc", 
      minHeight: "100vh" 
    }}>
      <header style={{ 
        marginBottom: "2rem", 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center" 
      }}>
        <div>
          <h1 style={{ margin: 0, color: "#38bdf8" }}>Kubernetes Auto-Remediation Dashboard</h1>
          <div style={{ 
            fontSize: "0.9rem", 
            color: isConnected ? "#4ade80" : "#ef4444", 
            marginTop: "0.5rem" 
          }}>
            {isConnected ? "✅ Connected to server" : "❌ Not connected to server"}
          </div>
        </div>
        <div style={{ display: "flex", gap: "1rem" }}>
          <button
            onClick={startAnalysis}
            disabled={isAnalyzing || !isConnected}
            style={{
              padding: "0.75rem 1.5rem",
              background: isAnalyzing ? "#475569" : "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: "0.375rem",
              cursor: isAnalyzing ? "not-allowed" : "pointer",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem"
            }}
          >
            {isAnalyzing ? "Analysis Running..." : "Start Analysis"}
          </button>
          <button
            onClick={downloadLogs}
            disabled={logs.length === 0}
            style={{
              padding: "0.75rem 1.5rem",
              background: logs.length === 0 ? "#475569" : "#10b981",
              color: "#fff",
              border: "none",
              borderRadius: "0.375rem",
              cursor: logs.length === 0 ? "not-allowed" : "pointer",
              fontWeight: "bold"
            }}
          >
            ⬇️ Download Logs
          </button>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginBottom: "2rem" }}>
        {/* Stats Panel */}
        <div style={{ 
          backgroundColor: "#1e293b", 
          borderRadius: "0.5rem", 
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
        }}>
          <h2 style={{ margin: "0 0 1rem 0", color: "#38bdf8" }}>Analysis Statistics</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Total Samples</div>
              <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#f8fafc" }}>{stats.total_samples}</div>
            </div>
            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Failures</div>
              <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#ef4444" }}>{stats.failures}</div>
            </div>
            <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
              <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Success Rate</div>
              <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#4ade80" }}>{stats.success_rate}</div>
            </div>
          </div>
        </div>

        {/* Current Sample Metrics */}
        <div style={{ 
          backgroundColor: "#1e293b", 
          borderRadius: "0.5rem", 
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
        }}>
          <h2 style={{ margin: "0 0 1rem 0", color: "#38bdf8" }}>
            {currentSample ? `Sample #${currentSample} Metrics` : "Current Sample Metrics"}
          </h2>
          {currentMetrics ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
              <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
                <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>CPU Usage</div>
                <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#f8fafc" }}>{currentMetrics.cpu_usage}</div>
              </div>
              <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
                <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Memory Usage</div>
                <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#f8fafc" }}>{currentMetrics.memory_usage}</div>
              </div>
              <div style={{ textAlign: "center", padding: "1rem", backgroundColor: "#0f172a", borderRadius: "0.375rem" }}>
                <div style={{ fontSize: "0.875rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Container Restarts</div>
                <div style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#f8fafc" }}>{currentMetrics.container_restarts_avg}</div>
              </div>
            </div>
          ) : (
            <div style={{ color: "#94a3b8", textAlign: "center", padding: "2rem" }}>
              No metrics available
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginBottom: "2rem" }}>
        {/* Gemini Recommendations */}
        <div style={{ 
          backgroundColor: "#1e293b", 
          borderRadius: "0.5rem", 
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
          height: "300px",
          overflowY: "auto"
        }}>
          <h2 style={{ margin: "0 0 1rem 0", color: "#38bdf8" }}>
            Gemini AI Recommendations
          </h2>
          {remediationSteps.length > 0 ? (
            <ul style={{ paddingLeft: "1.5rem", margin: "0" }}>
              {remediationSteps.map((step, idx) => (
                <li key={idx} style={{ marginBottom: "0.75rem", color: "#f8fafc" }}>{step}</li>
              ))}
            </ul>
          ) : (
            <div style={{ color: "#94a3b8", textAlign: "center", padding: "2rem" }}>
              No recommendations available
            </div>
          )}
        </div>

        {/* System Logs */}
        <div style={{ 
          backgroundColor: "#1e293b", 
          borderRadius: "0.5rem", 
          padding: "1.5rem",
          boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
          height: "300px",
          overflowY: "auto",
          position: "relative"
        }}>
          <h2 style={{ margin: "0 0 1rem 0", color: "#38bdf8", position: "sticky", top: 0, zIndex: 1, backgroundColor: "#1e293b", paddingBottom: "0.5rem" }}>
            System Logs
          </h2>
          <div>
            {logs.map((msg, idx) => (
              <div key={idx} style={{ 
                marginBottom: "0.5rem",
                color: 
                  msg.includes("❌") ? "#ef4444" :
                  msg.includes("✅") ? "#4ade80" :
                  msg.includes("💡") ? "#fbbf24" : "#f8fafc"
              }}>
                ▶ {msg}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Full System Logs */}
      <div style={{ 
        backgroundColor: "#1e293b", 
        borderRadius: "0.5rem", 
        padding: "1.5rem",
        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        maxHeight: "400px",
        overflowY: "auto"
      }}>
        <h2 style={{ margin: "0 0 1rem 0", color: "#38bdf8" }}>
          Complete Logs
        </h2>
        <pre style={{ 
          margin: 0, 
          whiteSpace: "pre-wrap", 
          wordBreak: "break-word", 
          color: "#f8fafc", 
          fontSize: "0.875rem",
          backgroundColor: "#0f172a",
          padding: "1rem",
          borderRadius: "0.375rem",
          fontFamily: "monospace"
        }}>
          {logs.join('\n')}
        </pre>
      </div>
    </div>
  );
}

export default App;
