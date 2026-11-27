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

package dbm

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
)

func marshalRequestToMap(t *testing.T, req *Request) map[string]any {
	t.Helper()

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal request failed, errmsg: %s", err)
	}

	fields := map[string]any{}
	if err := json.Unmarshal(data, &fields); err != nil {
		t.Fatalf("unmarshal request failed, errmsg: %s", err)
	}

	return fields
}

// The DBM API only shards when both hash_cnt and hash_value are present,
// so shard 0 must still carry hash_value or it returns the full data set.
func TestRequestMarshalKeepsZeroHashValue(t *testing.T) {
	fields := marshalRequestToMap(t, &Request{BkCloudId: 0, HashCnt: 200, HashValue: 0})

	hashValue, ok := fields["hash_value"]
	if !ok {
		t.Fatal("hash_value missing when it is 0")
	}
	if hashValue != float64(0) {
		t.Fatalf("hash_value: %v, want: 0", hashValue)
	}

	if fields["hash_cnt"] != float64(200) {
		t.Fatalf("hash_cnt: %v, want: 200", fields["hash_cnt"])
	}
}

func TestRequestMarshalWithoutHashCnt(t *testing.T) {
	fields := marshalRequestToMap(t, &Request{BkCloudId: 0, Addresses: []string{"127.0.0.1"}})

	if _, ok := fields["hash_cnt"]; ok {
		t.Fatal("hash_cnt should be omitted when it is 0")
	}
}

func TestRequestMetadataSendsZeroHashValue(t *testing.T) {
	bodyC := make(chan []byte, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		bodyC <- body

		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"result":true,"code":0,"data":[{"ip":"127.0.0.1","port":3306}]}`))
	}))
	t.Cleanup(server.Close)

	old := config.Cfg.Workflow.DbmApiMetadata
	config.Cfg.Workflow.DbmApiMetadata.Api = server.URL
	config.Cfg.Workflow.DbmApiMetadata.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Workflow.DbmApiMetadata = old
	})

	req := DefaultRequest
	req.HashCnt = 200
	req.HashValue = 0

	if _, _, err := (&Client{}).RequestMetadata(context.Background(), &req); err != nil {
		t.Fatalf("request metadata failed, errmsg: %s", err)
	}

	fields := map[string]any{}
	if err := json.Unmarshal(<-bodyC, &fields); err != nil {
		t.Fatalf("unmarshal request body failed, errmsg: %s", err)
	}

	hashValue, ok := fields["hash_value"]
	if !ok {
		t.Fatal("hash_value missing in request body")
	}
	if hashValue != float64(0) {
		t.Fatalf("hash_value: %v, want: 0", hashValue)
	}
}
