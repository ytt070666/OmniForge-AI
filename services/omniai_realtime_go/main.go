package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/nats-io/nats.go"
)

type event struct {
	Type    string         `json:"type"`
	TraceID string         `json:"trace_id"`
	Payload map[string]any `json:"payload"`
}

type hub struct {
	mu      sync.RWMutex
	clients map[chan []byte]struct{}
}

func newHub() *hub { return &hub{clients: map[chan []byte]struct{}{}} }

func (h *hub) subscribe() chan []byte {
	ch := make(chan []byte, 32)
	h.mu.Lock()
	h.clients[ch] = struct{}{}
	h.mu.Unlock()
	return ch
}

func (h *hub) unsubscribe(ch chan []byte) {
	h.mu.Lock()
	delete(h.clients, ch)
	close(ch)
	h.mu.Unlock()
}

func (h *hub) publish(data []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	for ch := range h.clients {
		select {
		case ch <- data:
		default:
			// Backpressure: a slow client loses an event instead of blocking all clients.
		}
	}
}

func writeError(w http.ResponseWriter, req *http.Request, status int, code string, message string) {
	requestID := middleware.GetReqID(req.Context())
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Request-ID", requestID)
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"error": map[string]string{
		"code": code, "message": message, "request_id": requestID,
	}})
}

func main() {
	h := newHub()
	var nc *nats.Conn
	if url := os.Getenv("OMNIAI_NATS_URL"); url != "" {
		conn, err := nats.Connect(url, nats.Timeout(2*time.Second))
		if err != nil {
			log.Printf("NATS disabled: %v", err)
		} else {
			nc = conn
			defer nc.Close()
			_, _ = nc.Subscribe("omniai.>", func(msg *nats.Msg) { h.publish(msg.Data) })
		}
	}

	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Recoverer)

	r.Get("/health", func(w http.ResponseWriter, req *http.Request) {
		requestID := middleware.GetReqID(req.Context())
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Request-ID", requestID)
		_ = json.NewEncoder(w).Encode(map[string]any{"ok": true, "service": "omniai-realtime-go", "version": "0.1.0", "request_id": requestID, "runtime": "go", "nats": nc != nil})
	})

	r.Get("/events", func(w http.ResponseWriter, req *http.Request) {
		flusher, ok := w.(http.Flusher)
		if !ok {
			writeError(w, req, http.StatusInternalServerError, "STREAM_UNAVAILABLE", "streaming unsupported")
			return
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		ch := h.subscribe()
		defer h.unsubscribe(ch)
		_, _ = fmt.Fprint(w, ": connected\n\n")
		flusher.Flush()
		keepalive := time.NewTicker(15 * time.Second)
		defer keepalive.Stop()
		for {
			select {
			case <-req.Context().Done():
				return
			case data := <-ch:
				_, _ = fmt.Fprintf(w, "event: omniai\ndata: %s\n\n", data)
				flusher.Flush()
			case <-keepalive.C:
				_, _ = fmt.Fprint(w, ": keepalive\n\n")
				flusher.Flush()
			}
		}
	})

	r.With(middleware.Timeout(15*time.Second)).Post("/publish", func(w http.ResponseWriter, req *http.Request) {
		var value event
		if err := json.NewDecoder(bufio.NewReader(req.Body)).Decode(&value); err != nil {
			writeError(w, req, http.StatusBadRequest, "INVALID_JSON", "invalid JSON")
			return
		}
		data, _ := json.Marshal(value)
		if nc != nil {
			if err := nc.Publish("omniai.realtime.event", data); err != nil {
				h.publish(data)
			}
		} else {
			h.publish(data)
		}
		w.WriteHeader(http.StatusAccepted)
		_ = json.NewEncoder(w).Encode(map[string]bool{"accepted": true})
	})

	addr := os.Getenv("OMNIAI_REALTIME_ADDR")
	if addr == "" {
		addr = ":8092"
	}
	server := &http.Server{Addr: addr, Handler: r, ReadHeaderTimeout: 5 * time.Second}
	log.Printf("OmniAI realtime gateway listening on %s", addr)
	log.Fatal(server.ListenAndServe())
}
