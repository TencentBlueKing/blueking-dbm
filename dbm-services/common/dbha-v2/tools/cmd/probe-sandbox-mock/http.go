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

package main

import (
	"encoding/json"
	"io"
	"net"
	"net/http"
	"time"
)

const maxAdminControlBody = 1 << 20

func startHTTP(addr string, st *appStats, ctl *adminControl) (func(), error) {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/stats", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, st.snapshot())
	})
	mux.HandleFunc("/last", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, st.lastPayloads())
	})
	mux.HandleFunc("/admin/payload", func(w http.ResponseWriter, r *http.Request) {
		handleAdminPayload(w, r, ctl)
	})
	mux.HandleFunc("/admin/mode", func(w http.ResponseWriter, r *http.Request) {
		handleAdminMode(w, r, ctl)
	})
	mux.HandleFunc("/admin/last-request", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		writeJSON(w, ctl.lastRequest())
	})

	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	svr := &http.Server{
		Handler:           mux,
		ReadHeaderTimeout: 3 * time.Second,
	}
	go func() {
		_ = svr.Serve(lis)
	}()
	return func() {
		_ = svr.Close()
		_ = lis.Close()
	}, nil
}

func handleAdminPayload(w http.ResponseWriter, r *http.Request, ctl *adminControl) {
	switch r.Method {
	case http.MethodGet:
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(ctl.snapshotPayload())
	case http.MethodPost:
		body, err := io.ReadAll(io.LimitReader(r.Body, maxAdminControlBody+1))
		if err != nil {
			http.Error(w, "read body failed", http.StatusBadRequest)
			return
		}
		if len(body) > maxAdminControlBody {
			http.Error(w, "body too large", http.StatusRequestEntityTooLarge)
			return
		}
		if err := ctl.setPayload(body); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		writeJSON(w, map[string]string{"status": "ok"})
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func handleAdminMode(w http.ResponseWriter, r *http.Request, ctl *adminControl) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, map[string]string{"mode": ctl.snapshotMode()})
	case http.MethodPost:
		body, err := io.ReadAll(io.LimitReader(r.Body, maxAdminControlBody+1))
		if err != nil {
			http.Error(w, "read body failed", http.StatusBadRequest)
			return
		}
		var req struct {
			Mode string `json:"mode"`
		}
		if err := json.Unmarshal(body, &req); err != nil || req.Mode == "" {
			http.Error(w, "body must be {\"mode\":\"success|no_data|fail\"}", http.StatusBadRequest)
			return
		}
		if err := ctl.setMode(req.Mode); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		writeJSON(w, map[string]string{"mode": ctl.snapshotMode()})
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	_ = enc.Encode(v)
}
