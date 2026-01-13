/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
package hanet

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNewHttpClient(t *testing.T) {
	cli := NewHttpClient()
	if cli == nil {
		t.Fatal("NewHttpClient() returned nil")
	}
	if cli.timeout != 5*time.Second {
		t.Fatalf("default timeout = %v, want 5s", cli.timeout)
	}
	if cli.headers == nil {
		t.Fatal("headers should not be nil")
	}
	if cli.cli == nil {
		t.Fatal("http.Client should not be nil")
	}
}

func TestNewHttpClientWithHeaders(t *testing.T) {
	headers := map[string]string{
		"Content-Type":  "application/json",
		"Authorization": "Bearer token123",
	}

	cli := NewHttpClientWithHeaders(headers)
	if cli == nil {
		t.Fatal("NewHttpClientWithHeaders() returned nil")
	}
	if cli.headers["Content-Type"] != "application/json" {
		t.Fatalf("Content-Type = %v, want application/json", cli.headers["Content-Type"])
	}
	if cli.headers["Authorization"] != "Bearer token123" {
		t.Fatalf("Authorization = %v, want Bearer token123", cli.headers["Authorization"])
	}
}

func TestHttpClient_SetHeader(t *testing.T) {
	cli := NewHttpClient()
	result := cli.SetHeader("X-Custom-Header", "custom-value")

	if result != cli {
		t.Fatal("SetHeader() should return the same client for chaining")
	}
	if cli.headers["X-Custom-Header"] != "custom-value" {
		t.Fatalf("X-Custom-Header = %v, want custom-value", cli.headers["X-Custom-Header"])
	}
}

func TestHttpClient_SetTimeout(t *testing.T) {
	cli := NewHttpClient()
	result := cli.SetTimeout(10 * time.Second)

	if result != cli {
		t.Fatal("SetTimeout() should return the same client for chaining")
	}
	if cli.timeout != 10*time.Second {
		t.Fatalf("timeout = %v, want 10s", cli.timeout)
	}
}

func TestHttpMethod_String(t *testing.T) {
	tests := []struct {
		method HttpMethod
		want   string
	}{
		{HttpMethodPost, "POST"},
		{HttpMethodGet, "GET"},
		{HttpMethodPut, "PUT"},
		{HttpMethodDelete, "DELETE"},
	}

	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			if got := tt.method.String(); got != tt.want {
				t.Fatalf("HttpMethod.String() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestHttpClient_verifyMethod(t *testing.T) {
	cli := NewHttpClient()

	validMethods := []HttpMethod{HttpMethodPost, HttpMethodGet, HttpMethodPut, HttpMethodDelete}
	for _, method := range validMethods {
		if err := cli.verifyMethod(method); err != nil {
			t.Fatalf("verifyMethod(%v) unexpected error: %v", method, err)
		}
	}

	invalidMethod := HttpMethod("PATCH")
	if err := cli.verifyMethod(invalidMethod); err == nil {
		t.Fatal("verifyMethod(PATCH) expected error, got nil")
	}
}

func TestHttpClient_Get(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Fatalf("expected GET method, got %s", r.Method)
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	}))
	defer server.Close()

	cli := NewHttpClient()
	code, resp, err := cli.Get(context.Background(), server.URL, nil)

	if err != nil {
		t.Fatalf("Get() error: %v", err)
	}
	if code != http.StatusOK {
		t.Fatalf("Get() code = %v, want %v", code, http.StatusOK)
	}
	if string(resp) != `{"status":"ok"}` {
		t.Fatalf("Get() resp = %v, want %v", string(resp), `{"status":"ok"}`)
	}
}

func TestHttpClient_Post(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Fatalf("expected POST method, got %s", r.Method)
		}
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte(`{"id":1}`))
	}))
	defer server.Close()

	cli := NewHttpClient()
	data := []byte(`{"name":"test"}`)
	code, resp, err := cli.Post(context.Background(), server.URL, data)

	if err != nil {
		t.Fatalf("Post() error: %v", err)
	}
	if code != http.StatusCreated {
		t.Fatalf("Post() code = %v, want %v", code, http.StatusCreated)
	}
	if string(resp) != `{"id":1}` {
		t.Fatalf("Post() resp = %v, want %v", string(resp), `{"id":1}`)
	}
}

func TestHttpClient_Put(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "PUT" {
			t.Fatalf("expected PUT method, got %s", r.Method)
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"updated":true}`))
	}))
	defer server.Close()

	cli := NewHttpClient()
	data := []byte(`{"name":"updated"}`)
	code, resp, err := cli.Put(context.Background(), server.URL, data)

	if err != nil {
		t.Fatalf("Put() error: %v", err)
	}
	if code != http.StatusOK {
		t.Fatalf("Put() code = %v, want %v", code, http.StatusOK)
	}
	if string(resp) != `{"updated":true}` {
		t.Fatalf("Put() resp = %v, want %v", string(resp), `{"updated":true}`)
	}
}

func TestHttpClient_Delete(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "DELETE" {
			t.Fatalf("expected DELETE method, got %s", r.Method)
		}
		w.WriteHeader(http.StatusNoContent)
	}))
	defer server.Close()

	cli := NewHttpClient()
	code, _, err := cli.Delete(context.Background(), server.URL, nil)

	if err != nil {
		t.Fatalf("Delete() error: %v", err)
	}
	if code != http.StatusNoContent {
		t.Fatalf("Delete() code = %v, want %v", code, http.StatusNoContent)
	}
}

func TestHttpClient_RequestWithHeaders(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		contentType := r.Header.Get("Content-Type")
		auth := r.Header.Get("Authorization")

		if contentType != "application/json" {
			t.Fatalf("Content-Type = %v, want application/json", contentType)
		}
		if auth != "Bearer test-token" {
			t.Fatalf("Authorization = %v, want Bearer test-token", auth)
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`ok`))
	}))
	defer server.Close()

	cli := NewHttpClient().
		SetHeader("Content-Type", "application/json").
		SetHeader("Authorization", "Bearer test-token")

	code, _, err := cli.Get(context.Background(), server.URL, nil)

	if err != nil {
		t.Fatalf("Request with headers error: %v", err)
	}
	if code != http.StatusOK {
		t.Fatalf("code = %v, want %v", code, http.StatusOK)
	}
}

func TestHttpClient_RequestInvalidMethod(t *testing.T) {
	cli := NewHttpClient()
	_, _, err := cli.Request(context.Background(), "http://localhost", HttpMethod("INVALID"), nil)

	if err == nil {
		t.Fatal("Request with invalid method expected error, got nil")
	}
}

func TestHttpClient_RequestWithData(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body := make([]byte, r.ContentLength)
		r.Body.Read(body)

		if string(body) != `{"key":"value"}` {
			t.Fatalf("request body = %v, want %v", string(body), `{"key":"value"}`)
		}

		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`received`))
	}))
	defer server.Close()

	cli := NewHttpClient()
	data := []byte(`{"key":"value"}`)
	code, resp, err := cli.Post(context.Background(), server.URL, data)

	if err != nil {
		t.Fatalf("Post with data error: %v", err)
	}
	if code != http.StatusOK {
		t.Fatalf("code = %v, want %v", code, http.StatusOK)
	}
	if string(resp) != "received" {
		t.Fatalf("resp = %v, want received", string(resp))
	}
}

func TestHttpClient_ChainedMethods(t *testing.T) {
	cli := NewHttpClient().
		SetHeader("X-Header-1", "value1").
		SetHeader("X-Header-2", "value2").
		SetTimeout(15 * time.Second)

	if cli.headers["X-Header-1"] != "value1" {
		t.Fatalf("X-Header-1 = %v, want value1", cli.headers["X-Header-1"])
	}
	if cli.headers["X-Header-2"] != "value2" {
		t.Fatalf("X-Header-2 = %v, want value2", cli.headers["X-Header-2"])
	}
	if cli.timeout != 15*time.Second {
		t.Fatalf("timeout = %v, want 15s", cli.timeout)
	}
}
