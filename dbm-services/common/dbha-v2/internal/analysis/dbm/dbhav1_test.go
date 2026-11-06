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
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

func TestDbhav1BlackWhitelistQueryArgsMarshalExplicitZeroAndEmpty(t *testing.T) {
	t.Parallel()

	zero := 0
	empty := ""
	req := Dbhav1BlackWhitelistGetRequest{
		Name: "get_black_white_list",
		QueryArgs: Dbhav1BlackWhitelistQueryArgs{
			BkBizID:     &zero,
			BkCloudID:   &zero,
			ClusterID:   &zero,
			ClusterName: &empty,
		},
	}

	queryArgs := marshalQueryArgs(t, req)

	for _, key := range []string{"bk_biz_id", "bk_cloud_id", "cluster_id"} {
		got, ok := queryArgs[key]
		if !ok {
			t.Fatalf("query_args.%s omitted for explicit 0: %v", key, queryArgs)
		}
		if got != float64(0) {
			t.Fatalf("query_args.%s = %v, want 0", key, got)
		}
	}
	got, ok := queryArgs["cluster_name"]
	if !ok {
		t.Fatalf("query_args.cluster_name omitted for explicit empty string: %v", queryArgs)
	}
	if got != "" {
		t.Fatalf("query_args.cluster_name = %v, want empty string", got)
	}
}

func TestDbhav1BlackWhitelistQueryArgsMarshalOmitsUnset(t *testing.T) {
	t.Parallel()

	req := Dbhav1BlackWhitelistGetRequest{
		Name:      "get_black_white_list",
		QueryArgs: Dbhav1BlackWhitelistQueryArgs{},
	}

	queryArgs := marshalQueryArgs(t, req)
	if len(queryArgs) != 0 {
		t.Fatalf("unset query_args should be omitted, got %v", queryArgs)
	}
}

func TestGetBlackWhiteListFromDbhaV1QueryArgsMatchV1(t *testing.T) {
	var captured Dbhav1BlackWhitelistGetRequest
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Errorf("read request body: %s", err)
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		if err := json.Unmarshal(body, &captured); err != nil {
			t.Errorf("unmarshal request body: %s", err)
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(&Dbhav1BlackWhiteListResponse{Code: 0, Message: "ok"})
	}))
	t.Cleanup(server.Close)

	old := config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Api = server.URL
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Token = "test-token"
	config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet.Timeout = time.Second
	t.Cleanup(func() {
		config.Cfg.Workflow.Dbhav1ApiBlackWhitelistGet = old
	})

	if _, err := (&Client{}).GetBlackWhiteListFromDbhaV1(context.Background(), 0); err != nil {
		t.Fatalf("GetBlackWhiteListFromDbhaV1: %s", err)
	}

	if captured.QueryArgs.BkCloudID == nil || *captured.QueryArgs.BkCloudID != 0 {
		t.Fatalf("query_args.bk_cloud_id = %v, want 0", captured.QueryArgs.BkCloudID)
	}
	if captured.QueryArgs.SwitchVersion == nil || *captured.QueryArgs.SwitchVersion != string(hamodel.SwitchVersionV2) {
		t.Fatalf("query_args.switch_version = %v, want %s", captured.QueryArgs.SwitchVersion, hamodel.SwitchVersionV2)
	}
	if captured.QueryArgs.Status == nil || *captured.QueryArgs.Status != string(hamodel.StatusTypeEnabled) {
		t.Fatalf("query_args.status = %v, want %s", captured.QueryArgs.Status, hamodel.StatusTypeEnabled)
	}
	if captured.QueryArgs.BkBizID != nil {
		t.Fatalf("query_args.bk_biz_id should be unset like v1, got %d", *captured.QueryArgs.BkBizID)
	}
	if captured.QueryArgs.ClusterID != nil {
		t.Fatalf("query_args.cluster_id should be unset, got %d", *captured.QueryArgs.ClusterID)
	}
	if captured.QueryArgs.ClusterName != nil {
		t.Fatalf("query_args.cluster_name should be unset, got %q", *captured.QueryArgs.ClusterName)
	}
}

func marshalQueryArgs(t *testing.T, req Dbhav1BlackWhitelistGetRequest) map[string]any {
	t.Helper()

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal request: %s", err)
	}

	var decoded map[string]any
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("unmarshal request: %s", err)
	}

	queryArgs, ok := decoded["query_args"].(map[string]any)
	if !ok {
		t.Fatalf("query_args missing or not an object: %s", data)
	}
	return queryArgs
}
