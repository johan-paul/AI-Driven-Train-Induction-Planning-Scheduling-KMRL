// src/pages/LoginPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaUser, FaLock } from "react-icons/fa";

/**
 * LoginPage
 *
 * Optional prop:
 *   - onLogin: async function({ email, password, isSignup }) -> { ok: boolean, message?: string }
 *              If provided, component will await it and use the result to proceed.
 *
 * Fallback behavior (no onLogin): simple client-side validation and navigate to /config.
 */
function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const validateEmail = (e) => {
    const s = String(e || "").trim();
    // simple email regex (not perfect but practical)
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const trimmedEmail = String(email || "").trim();
    const pwd = String(password || "");
    const conf = String(confirm || "");

    if (!trimmedEmail || !pwd) {
      setError("Please enter email and password");
      return;
    }
    if (!validateEmail(trimmedEmail)) {
      setError("Please enter a valid email address");
      return;
    }
    if (pwd.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }
    if (isSignup && pwd !== conf) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      if (typeof onLogin === "function") {
        // allow parent to handle actual auth (API call)
        const result = await onLogin({ email: trimmedEmail, password: pwd, isSignup });
        if (result && result.ok) {
          localStorage.setItem("kmrl_authenticated", "1");
          navigate("/config");
        } else {
          setError(result?.message || "Authentication failed");
        }
      } else {
        // fallback local behavior: mark as 'authenticated' and continue
        localStorage.setItem("kmrl_authenticated", "1");
        navigate("/config");
      }
    } catch (err) {
      console.error("Login error", err);
      setError(err?.message ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden font-sans bg-gradient-to-br from-[#0b0f14] via-[#1a103d] to-[#0b0f14]">
      {/* Floating orbs */}
      <div className="absolute w-72 h-72 bg-purple-600/30 rounded-full blur-3xl top-20 left-10 animate-pulse" />
      <div className="absolute w-96 h-96 bg-blue-500/20 rounded-full blur-3xl bottom-10 right-10 animate-pulse" />

      <div className="relative backdrop-blur-lg bg-white/10 border border-white/20 rounded-2xl shadow-2xl p-10 w-[400px]">
        <h2 className="text-3xl font-bold mb-8 text-center text-white drop-shadow-lg">
          {isSignup ? "📝 Sign Up" : "🚆 Train Induction Login"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-5" aria-live="polite">
          <div className="flex items-center bg-white/10 px-4 py-2 rounded-lg border border-white/20">
            <FaUser className="text-gray-300 mr-3" />
            <input
              type="email"
              placeholder="Email"
              className="w-full bg-transparent outline-none text-white placeholder-gray-400"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-label="Email"
              required
            />
          </div>

          <div className="flex items-center bg-white/10 px-4 py-2 rounded-lg border border-white/20">
            <FaLock className="text-gray-300 mr-3" />
            <input
              type="password"
              placeholder="Password"
              className="w-full bg-transparent outline-none text-white placeholder-gray-400"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-label="Password"
              required
              minLength={6}
            />
          </div>

          {isSignup && (
            <div className="flex items-center bg-white/10 px-4 py-2 rounded-lg border border-white/20">
              <FaLock className="text-gray-300 mr-3" />
              <input
                type="password"
                placeholder="Confirm Password"
                className="w-full bg-transparent outline-none text-white placeholder-gray-400"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                aria-label="Confirm password"
                required={isSignup}
                minLength={6}
              />
            </div>
          )}

          {error && <p className="text-red-400 text-sm" role="alert">{error}</p>}

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-purple-600 hover:bg-purple-700 transition shadow-lg shadow-purple-500/30 text-white font-semibold text-lg disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? "Please wait…" : isSignup ? "Sign Up" : "Login"}
          </button>
        </form>

        <p
          className="text-sm text-center mt-6 text-gray-300 cursor-pointer hover:underline select-none"
          onClick={() => setIsSignup((s) => !s)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setIsSignup((s) => !s); }}
        >
          {isSignup ? "Already have an account? Login" : "Don’t have an account? Sign Up"}
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
