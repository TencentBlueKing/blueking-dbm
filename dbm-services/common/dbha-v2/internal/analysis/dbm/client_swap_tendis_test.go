package dbm

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
)

func TestSwapTendisClusterSuccess(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Fatalf("unexpected method: %s", r.Method)
		}

		req := SwapTendisClusterRequest{}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Fatalf("decode request failed: %s", err)
		}

		if req.BkCloudID != 1 {
			t.Fatalf("unexpected bk_cloud_id: %d", req.BkCloudID)
		}
		if req.DbCloudToken != "token" {
			t.Fatalf("unexpected db_cloud_token: %s", req.DbCloudToken)
		}
		if req.Payload.Domain != "redis.test.db" {
			t.Fatalf("unexpected domain: %s", req.Payload.Domain)
		}
		if req.Payload.Master.IP != "127.0.0.1" || req.Payload.Master.Port != 6379 {
			t.Fatalf("unexpected master: %+v", req.Payload.Master)
		}
		if req.Payload.Slave.IP != "127.0.0.2" || req.Payload.Slave.Port != 6380 {
			t.Fatalf("unexpected slave: %+v", req.Payload.Slave)
		}

		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"result":true,"message":"ok","code":0}`))
	}))
	defer server.Close()

	originCfg := config.Cfg.Workflow.DbmApiSwapTendisCluster
	t.Cleanup(func() {
		config.Cfg.Workflow.DbmApiSwapTendisCluster = originCfg
	})
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Api = server.URL
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Token = "token"
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Timeout = 2 * time.Second

	client := &Client{}
	err := client.SwapTendisCluster(1, "redis.test.db", "127.0.0.1", 6379, "127.0.0.2", 6380)
	if err != nil {
		t.Fatalf("SwapTendisCluster failed: %s", err)
	}
}

func TestSwapTendisClusterFailure(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"result":false,"message":"failed","code":0}`))
	}))
	defer server.Close()

	originCfg := config.Cfg.Workflow.DbmApiSwapTendisCluster
	t.Cleanup(func() {
		config.Cfg.Workflow.DbmApiSwapTendisCluster = originCfg
	})
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Api = server.URL
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Token = "token"
	config.Cfg.Workflow.DbmApiSwapTendisCluster.Timeout = 2 * time.Second

	client := &Client{}
	err := client.SwapTendisCluster(1, "redis.test.db", "127.0.0.1", 6379, "127.0.0.2", 6380)
	if err == nil {
		t.Fatalf("expected error when DBM returns result=false")
	}
}
