/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package thirdapi

import (
	"encoding/json"
	"net/http"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	infreq "k8s-dbs/infrastructure/request"
)

// testInstance{1,2} 使用回环地址段，仅用于单元测试，不代表任何真实主机。
const (
	testInstance1 = "127.0.0.1#6333"
	testInstance2 = "127.0.0.2#6333"
)

func newCreateDomainRequest() *infreq.CreateDomainRequest {
	return &infreq.CreateDomainRequest{
		BkCloudID:   0,
		BkBizID:     100,
		ClusterType: "k8s_qdrant",
		Name:        "my-cluster",
		Domain:      "k8s-qdrant.my-cluster.bkapp.db",
		Instances:   []string{testInstance1, testInstance2},
		Role:        "master_entry",
		Operator:    "admin",
	}
}

func TestSyncDomainCreated_Success(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/apis/proxypass/k8s/domain/create/", r.URL.Path)
		assert.Equal(t, http.MethodPost, r.Method)

		var body map[string]interface{}
		require.NoError(t, json.NewDecoder(r.Body).Decode(&body))
		assert.Equal(t, "k8s_qdrant", body["cluster_type"])
		assert.Equal(t, "my-cluster", body["name"])
		assert.Equal(t, "k8s-qdrant.my-cluster.bkapp.db", body["domain"])
		assert.Equal(t, "master_entry", body["role"])

		respondJSON(w, map[string]interface{}{
			"result":  true,
			"code":    0,
			"data":    nil,
			"message": "",
		})
	})
	defer srv.Close()

	resp, err := svc.SyncDomainCreated(newCreateDomainRequest())
	require.NoError(t, err)
	assert.True(t, resp.Result)
}

func TestSyncDomainCreated_RequestBodyFields(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		var body map[string]interface{}
		require.NoError(t, json.NewDecoder(r.Body).Decode(&body))

		assert.Contains(t, body, "bk_cloud_id")
		assert.Contains(t, body, "bk_biz_id")
		assert.Contains(t, body, "cluster_type")
		assert.Contains(t, body, "name")
		assert.Contains(t, body, "domain")
		assert.Contains(t, body, "instances")
		assert.Contains(t, body, "role")
		assert.Contains(t, body, "operator")

		instances, ok := body["instances"].([]interface{})
		require.True(t, ok)
		assert.Len(t, instances, 2)

		respondJSON(w, map[string]interface{}{"result": true, "code": 0, "data": nil, "message": ""})
	})
	defer srv.Close()

	_, err := svc.SyncDomainCreated(newCreateDomainRequest())
	require.NoError(t, err)
}

func TestSyncDomainCreated_DBMAPIError(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		respondJSON(w, map[string]interface{}{
			"result":  false,
			"code":    8700500,
			"data":    nil,
			"message": "域名已存在",
		})
	})
	defer srv.Close()

	_, err := svc.SyncDomainCreated(newCreateDomainRequest())
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "DBM API request failed")
}

func TestSyncDomainCreated_HTTPError(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	defer srv.Close()

	_, err := svc.SyncDomainCreated(newCreateDomainRequest())
	assert.Error(t, err)
}

func TestSyncDomainCreated_URLContainsDomainCreate(t *testing.T) {
	srv, svc := newTestServer(t, func(w http.ResponseWriter, r *http.Request) {
		assert.True(t, strings.Contains(r.URL.Path, "domain/create"),
			"URL 应包含 domain/create，实际: %s", r.URL.Path)
		respondJSON(w, map[string]interface{}{"result": true, "code": 0, "data": nil, "message": ""})
	})
	defer srv.Close()

	_, err := svc.SyncDomainCreated(newCreateDomainRequest())
	require.NoError(t, err)
}
