package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/joho/godotenv"

	"github.com/gbrlcruz/tudim/backend/internal/meta"
)

func scrubbedLogger(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
        defer func() {
            slog.Info("http",
                "method", r.Method,
                "path", r.URL.Path,     // path only, no raw query
                "status", ww.Status(),
                "bytes", ww.BytesWritten(),
                "duration_ms", time.Since(start).Milliseconds(),
                "request_id", middleware.GetReqID(r.Context()),
            )
        }()
        next.ServeHTTP(ww, r)
    })
}

func main() {
    // Load .env in dev (no-op in prod where envs come from Cloud Run)
    _ = godotenv.Load()

    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
    slog.SetDefault(logger)

    r := chi.NewRouter()
    r.Use(middleware.Recoverer) // recovers from panics
    r.Use(middleware.RequestID)
    r.Use(scrubbedLogger)

    r.Get("/healthz", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("ok"))
    })

    r.Get("/webhooks/whatsapp", meta.VerifyWebhook)
    r.Post("/webhooks/whatsapp", meta.ReceiveWebhook)

    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    srv := &http.Server{
        Addr:              ":" + port,
        Handler:           r,
        ReadHeaderTimeout: 5 * time.Second,
        ReadTimeout:       30 * time.Second,  // total time to read body
        WriteTimeout:      30 * time.Second,  // total time to write response
        IdleTimeout:       60 * time.Second,  // for keepalive connections
    }

    // Graceful shutdown — Cloud Run sends SIGTERM 10s before kill
    go func() {
        slog.Info("listening", "port", port)
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            slog.Error("server error", "err", err)
            os.Exit(1)
        }
    }()

    stop := make(chan os.Signal, 1)
    signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
    <-stop

    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()
    _ = srv.Shutdown(ctx)
    slog.Info("bye 🐹")
}