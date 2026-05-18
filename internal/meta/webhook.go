package meta

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"
)

// Meta sends GET ?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
// We must echo back hub.challenge if hub.verify_token matches what we set in the dashboard.
func VerifyWebhook(w http.ResponseWriter, r *http.Request) {
    mode := r.URL.Query().Get("hub.mode")
    token := r.URL.Query().Get("hub.verify_token")
    challenge := r.URL.Query().Get("hub.challenge")

    if mode == "subscribe" && token == os.Getenv("META_VERIFY_TOKEN") {
        w.Write([]byte(challenge))
        return
    }
    http.Error(w, "forbidden", http.StatusForbidden)
}

// Validate X-Hub-Signature-256 header against app secret + body
func ValidateSignature(body []byte, signature string) bool {
    if !strings.HasPrefix(signature, "sha256=") {
        return false
    }
    expected := signature[7:]
    mac := hmac.New(sha256.New, []byte(os.Getenv("META_APP_SECRET")))
    mac.Write(body)
    got := hex.EncodeToString(mac.Sum(nil))
    return hmac.Equal([]byte(expected), []byte(got))
}

// Minimal struct for the inbound message we care about
type WebhookPayload struct {
    Entry []struct {
        Changes []struct {
            Value struct {
                Messages []InboundMessage `json:"messages"`
            } `json:"value"`
        } `json:"changes"`
    } `json:"entry"`
}

type InboundMessage struct {
    From      string `json:"from"`        // phone number
    ID        string `json:"id"`          // message id (for dedupe)
    Timestamp string `json:"timestamp"`
    Type      string `json:"type"`        // "text" | "audio" | "image" | ...
    Text      struct {
        Body string `json:"body"`
    } `json:"text"`
}

func ReceiveWebhook(w http.ResponseWriter, r *http.Request) {
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MiB cap
    body, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "request too large", http.StatusRequestEntityTooLarge)
        return
    }
    defer r.Body.Close()

    if !ValidateSignature(body, r.Header.Get("X-Hub-Signature-256")) {
        http.Error(w, "bad signature", http.StatusUnauthorized)
        return
    }

    var payload WebhookPayload
    if err := json.Unmarshal(body, &payload); err != nil {
        http.Error(w, "bad json", http.StatusBadRequest)
        return
    }

    // ALWAYS respond 200 fast, then process. For now we process inline; later we publish to Pub/Sub.
	for _, entry := range payload.Entry {
		for _, change := range entry.Changes {
			for _, msg := range change.Value.Messages {
				handleMessage(msg) // synchronous
			}
		}
	}
	w.WriteHeader(http.StatusOK)
}

func handleMessage(msg InboundMessage) {
    if msg.Type != "text" {
        SendText(msg.From, "Por enquanto eu só rolo com texto 😅")
        return
    }
    SendText(msg.From, "Você disse: "+msg.Text.Body)
}