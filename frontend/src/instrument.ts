import * as Sentry from "@sentry/react";

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    dataCollection: { userInfo: false, cookies: false, httpBodies: [] },
    tracesSampleRate: 0,
  });
}
