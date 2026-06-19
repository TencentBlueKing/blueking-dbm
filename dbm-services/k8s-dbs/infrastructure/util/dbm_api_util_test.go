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

package util

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	metaentity "k8s-dbs/metadata/entity"
)

// testAddr{1,2,3,9} 使用回环地址段，仅用于单元测试，不代表任何真实主机。
const (
	testAddr1 = "127.0.0.1"
	testAddr2 = "127.0.0.2"
	testAddr3 = "127.0.0.3"
	testAddr9 = "127.0.0.9"
)

// --- SanitizeForDomain ---

func TestSanitizeForDomain(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"hello", "hello"},
		{"Hello_World", "hello-world"},
		{"k8s_vm", "k8s-vm"},
		{"UPPER-CASE", "upper-case"},
		{"abc123", "abc123"},
		{"foo.bar", "foobar"},
		{"foo@bar!", "foobar"},
		{"__leading__", "--leading--"},
		{"", ""},
	}
	for _, c := range cases {
		t.Run(c.input, func(t *testing.T) {
			assert.Equal(t, c.want, SanitizeForDomain(c.input))
		})
	}
}

// --- BuildDomainName ---

func TestBuildDomainName(t *testing.T) {
	cases := []struct {
		clusterType string
		clusterName string
		bkAppAbbr   string
		want        string
	}{
		{
			"k8s_vm", "my-cluster", "bkapp",
			"k8s-vm.my-cluster.bkapp.db",
		},
		{
			"k8s_qdrant", "qdrant_cluster", "myapp",
			"k8s-qdrant.qdrant-cluster.myapp.db",
		},
		{
			"K8S_GREPTIMEDB", "TestCluster", "AppAbbr",
			"k8s-greptimedb.testcluster.appabbr.db",
		},
		{
			// 点号不在 [a-zA-Z0-9-] 范围内，会被直接移除
			"k8s_vm", "cluster.with.dots", "app",
			"k8s-vm.clusterwithdots.app.db",
		},
	}
	for _, c := range cases {
		t.Run(c.want, func(t *testing.T) {
			got := BuildDomainName(c.clusterType, c.clusterName, c.bkAppAbbr)
			assert.Equal(t, c.want, got)
		})
	}
}

// --- BuildDomainInstances ---

func TestBuildDomainInstances_SingleAddr(t *testing.T) {
	result := BuildDomainInstances(testAddr1 + ":9000")
	require.Len(t, result, 1)
	assert.Equal(t, testAddr1+"#0", result[0])
}

// 同一 LoadBalancer Service 的多个端口共用同一 VIP，
// BuildDomainInstances 仅取第一个地址的 IP 生成一条 instance 记录。
func TestBuildDomainInstances_MultipleAddrs(t *testing.T) {
	result := BuildDomainInstances(testAddr1 + ":9000," + testAddr2 + ":9001")
	require.Len(t, result, 1)
	assert.Equal(t, testAddr1+"#0", result[0])
}

// 首个地址非法时新实现会跳过并尝试后续地址。
func TestBuildDomainInstances_InvalidAddrSkipped(t *testing.T) {
	result := BuildDomainInstances("invalid," + testAddr1 + ":9000")
	require.Len(t, result, 1)
	assert.Equal(t, testAddr1+"#0", result[0])
}

// 首个地址非法时应遍历后续地址，直到找到可解析的 host:port。
func TestBuildDomainInstances_FallbackToNextValidAddr(t *testing.T) {
	// net.SplitHostPort("nohostport") 返回 error → 跳过；取下一个
	result := BuildDomainInstances("nohostport," + testAddr2 + ":9001," + testAddr3 + ":9002")
	require.Len(t, result, 1)
	assert.Equal(t, testAddr2+"#0", result[0])
}

// 空白字符串和空 token 应被跳过而不是当作错误阻断整个解析。
func TestBuildDomainInstances_SkipEmptyTokens(t *testing.T) {
	result := BuildDomainInstances(" , ," + testAddr9 + ":9000")
	require.Len(t, result, 1)
	assert.Equal(t, testAddr9+"#0", result[0])
}

// IPv6 地址按 RFC 3986 要求应使用方括号包裹，net.SplitHostPort 原生支持。
func TestBuildDomainInstances_IPv6Bracketed(t *testing.T) {
	result := BuildDomainInstances("[2001:db8::1]:9000")
	require.Len(t, result, 1)
	assert.Equal(t, "2001:db8::1#0", result[0])
}

func TestBuildDomainInstances_EmptyString(t *testing.T) {
	result := BuildDomainInstances("")
	assert.Empty(t, result)
}

func TestBuildDomainInstances_IPv6StyleAddr(t *testing.T) {
	// net.SplitHostPort 能正确处理带方括号的 IPv6 地址，剥出纯 host 部分
	result := BuildDomainInstances("[::1]:9000")
	require.Len(t, result, 1)
	assert.Equal(t, "::1#0", result[0])
}

// --- BuildCreateDomainRequest ---

func newTestClusterEntity(addonType, clusterName, bkAppAbbr string, bkBizID uint64) *metaentity.K8sCrdClusterEntity {
	return &metaentity.K8sCrdClusterEntity{
		ClusterName: clusterName,
		BkBizID:     bkBizID,
		BkAppAbbr:   bkAppAbbr,
		CreatedBy:   "admin",
		AddonInfo:   &metaentity.K8sCrdStorageAddonEntity{AddonType: addonType},
	}
}

func newTestServiceEntity(externalAddrs string) *metaentity.K8sClusterServiceEntity {
	return &metaentity.K8sClusterServiceEntity{
		ServiceName:   "test-svc",
		ExternalAddrs: externalAddrs,
	}
}

func TestBuildCreateDomainRequest_Success(t *testing.T) {
	cluster := newTestClusterEntity("qdrant", "my-cluster", "bkapp", 100)
	service := newTestServiceEntity(testAddr1 + ":6333," + testAddr2 + ":6333")

	req, err := BuildCreateDomainRequest(cluster, service)
	require.NoError(t, err)
	require.NotNil(t, req)

	assert.Equal(t, "k8s_qdrant", req.ClusterType)
	assert.Equal(t, "k8s-qdrant.my-cluster.bkapp.db", req.Domain)
	assert.Equal(t, "my-cluster", req.Name)
	assert.Equal(t, uint64(100), req.BkBizID)
	assert.Equal(t, uint64(0), req.BkCloudID)
	assert.Equal(t, "master_entry", req.Role)
	assert.Equal(t, "admin", req.Operator)
	// 同一 LoadBalancer Service 的多端口共用 VIP，只保留一条 instance
	require.Len(t, req.Instances, 1)
	assert.Equal(t, testAddr1+"#0", req.Instances[0])
}

func TestBuildCreateDomainRequest_UnknownAddonType(t *testing.T) {
	cluster := newTestClusterEntity("unknown_addon", "my-cluster", "bkapp", 100)
	service := newTestServiceEntity(testAddr1 + ":6333")

	req, err := BuildCreateDomainRequest(cluster, service)
	assert.Error(t, err)
	assert.Nil(t, req)
	assert.Contains(t, err.Error(), "GetDbmClusterType failed")
}

func TestBuildCreateDomainRequest_EmptyExternalAddrs(t *testing.T) {
	cluster := newTestClusterEntity("qdrant", "my-cluster", "bkapp", 100)
	service := newTestServiceEntity("")

	req, err := BuildCreateDomainRequest(cluster, service)
	assert.Error(t, err)
	assert.Nil(t, req)
	assert.Contains(t, err.Error(), "instances is empty")
}

func TestBuildCreateDomainRequest_AllInvalidAddrs(t *testing.T) {
	cluster := newTestClusterEntity("qdrant", "my-cluster", "bkapp", 100)
	service := newTestServiceEntity("no-port,also-no-port")

	req, err := BuildCreateDomainRequest(cluster, service)
	assert.Error(t, err)
	assert.Nil(t, req)
}

func TestBuildCreateDomainRequest_AllSupportedAddonTypes(t *testing.T) {
	supportedAddons := []string{
		"surrealdb", "victoriametrics", "risingwave",
		"greptimedb", "milvus", "qdrant",
	}
	service := newTestServiceEntity(testAddr1 + ":9000")

	for _, addonType := range supportedAddons {
		t.Run(addonType, func(t *testing.T) {
			cluster := newTestClusterEntity(addonType, "test-cluster", "app", 1)
			req, err := BuildCreateDomainRequest(cluster, service)
			require.NoError(t, err)
			assert.NotEmpty(t, req.ClusterType)
			assert.NotEmpty(t, req.Domain)
			assert.Equal(t, "master_entry", req.Role)
		})
	}
}
