package meta

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "log/slog"
    "net/http"
    "os"
    "time"
)

var httpClient = &http.Client{Timeout: 10 * time.Second}

type outMsg struct {
    MessagingProduct string `json:"messaging_product"`
    To               string `json:"to"`
    Type             string `json:"type"`
    Text             struct {
        Body string `json:"body"`
    } `json:"text"`
}

func SendText(to, body string) error {
    phoneID := os.Getenv("META_PHONE_NUMBER_ID")
    token := os.Getenv("META_ACCESS_TOKEN")
    url := fmt.Sprintf("https://graph.facebook.com/v20.0/%s/messages", phoneID)

    payload := outMsg{MessagingProduct: "whatsapp", To: to, Type: "text"}
    payload.Text.Body = body

    buf, _ := json.Marshal(payload)
    req, _ := http.NewRequest("POST", url, bytes.NewReader(buf))
    req.Header.Set("Authorization", "Bearer "+token)
    req.Header.Set("Content-Type", "application/json")

    resp, err := httpClient.Do(req)
    if err != nil {
        return fmt.Errorf("meta send: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode >= 300 {
        b, _ := io.ReadAll(resp.Body)
        slog.Error("meta non-2xx", "status", resp.StatusCode, "body", string(b))
        return fmt.Errorf("meta returned %d", resp.StatusCode)
    }
    return nil
}