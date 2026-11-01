import "./instrument";
import React from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "@sentry/react";
import App from "./App";
import "./style.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary
      fallback={
        <main>
          <section className="panel page-heading">
            <h1>Let's take that from the top.</h1>
            <p>
              Something unexpected happened. Refresh to start a new interview.
            </p>
            <button
              className="primary"
              onClick={() => window.location.reload()}
            >
              Start fresh
            </button>
          </section>
        </main>
      }
    >
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
