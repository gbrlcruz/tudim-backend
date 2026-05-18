# syntax=docker/dockerfile:1

# ----- Build stage -----
FROM golang:1.26-alpine AS build

WORKDIR /src

# Copy dep files first so Docker caches the dep download layer
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest and build a static binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/api ./cmd/api

# ----- Runtime stage -----
FROM gcr.io/distroless/static-debian12

COPY --from=build /out/api /api

# Cloud Run sets PORT=8080 by default; your main.go already reads it
EXPOSE 8080

ENTRYPOINT ["/api"]