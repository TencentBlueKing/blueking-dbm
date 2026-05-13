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

package keepalive

import (
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestPingServerPing(t *testing.T) {
	svr := NewPingServer("127.0.0.1:0")
	if err := svr.Start(); err != nil {
		t.Fatalf("start ping server failed, errmsg: %s", err)
	}
	defer func() {
		if err := svr.Close(); err != nil {
			t.Fatalf("close ping server failed, errmsg: %s", err)
		}
	}()

	client := &http.Client{Timeout: 3 * time.Second}
	resp, err := client.Get("http://" + svr.Addr() + pingPath)
	if err != nil {
		t.Fatalf("request ping api failed, errmsg: %s", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("unexpected status code, expected: %d, actual: %d", http.StatusOK, resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read ping response body failed, errmsg: %s", err)
	}
	if string(body) != pingResponse {
		t.Fatalf("unexpected ping response body, expected: %s, actual: %s", pingResponse, string(body))
	}
}

func TestPingServerMethodNotAllowed(t *testing.T) {
	svr := NewPingServer("127.0.0.1:0")
	if err := svr.Start(); err != nil {
		t.Fatalf("start ping server failed, errmsg: %s", err)
	}
	defer func() {
		if err := svr.Close(); err != nil {
			t.Fatalf("close ping server failed, errmsg: %s", err)
		}
	}()

	client := &http.Client{Timeout: 3 * time.Second}
	req, err := http.NewRequest(http.MethodPost, "http://"+svr.Addr()+pingPath, nil)
	if err != nil {
		t.Fatalf("build ping api request failed, errmsg: %s", err)
	}

	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("call ping api failed, errmsg: %s", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf(
			"unexpected status code, expected: %d, actual: %d",
			http.StatusMethodNotAllowed,
			resp.StatusCode,
		)
	}
}

func TestSetCommNameValidateLength(t *testing.T) {
	longName := strings.Repeat("a", 16)
	err := SetCommName(longName)
	if err == nil {
		t.Fatalf("set comm name should fail when name exceeds 15 chars")
	}
}
