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

package harvest

import (
	"errors"
	"testing"

	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

func TestIsAuthError(t *testing.T) {
	tests := []struct {
		name string
		err  error
		want bool
	}{
		{"nil error", nil, false},
		{"noauth authentication", errors.New("NOAUTH Authentication required"), true},
		{"wrongpass invalid", errors.New("WRONGPASS invalid username-password pair"), true},
		{"invalid password", errors.New("invalid password"), true},
		{"auth permission deny", errors.New("auth permission deny"), true},
		{"connection refused", errors.New("dial tcp: connection refused"), false},
		{"io timeout", errors.New("i/o timeout"), false},
		{"unknown command", errors.New("ERR unknown command"), false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := isAuthError(tt.err); got != tt.want {
				t.Fatalf("isAuthError(%v) = %v, want %v", tt.err, got, tt.want)
			}
		})
	}
}

func TestClassifyOpenError(t *testing.T) {
	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.1", Port: 6379}}

	t.Run("auth error", func(t *testing.T) {
		event := c.classifyOpenError(errors.New("NOAUTH Authentication required"))
		if event == nil {
			t.Fatal("expected non-nil event")
		}
		if event.Name != haprobe.DbEventNameDetectRedisAuthFailureV1 {
			t.Fatalf("unexpected event name: %s", event.Name)
		}
		if event.Reason != haprobe.DbEventNameReasonAuthException {
			t.Fatalf("unexpected reason: %d", event.Reason)
		}
	})

	t.Run("connection error", func(t *testing.T) {
		event := c.classifyOpenError(errors.New("dial tcp: connection refused"))
		if event == nil {
			t.Fatal("expected non-nil event")
		}
		if event.Name != haprobe.DbEventNameDetectFailure {
			t.Fatalf("unexpected event name: %s", event.Name)
		}
		if event.Reason != haprobe.DbEventNameReasonConnectionException {
			t.Fatalf("unexpected reason: %d", event.Reason)
		}
	})
}

func TestClassifyCommandError(t *testing.T) {
	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.1", Port: 6379}}

	t.Run("auth error", func(t *testing.T) {
		event := c.classifyCommandError(errors.New("WRONGPASS invalid username-password pair"))
		if event == nil {
			t.Fatal("expected non-nil event")
		}
		if event.Name != haprobe.DbEventNameDetectRedisAuthFailureV1 {
			t.Fatalf("unexpected event name: %s", event.Name)
		}
		if event.Reason != haprobe.DbEventNameReasonAuthException {
			t.Fatalf("unexpected reason: %d", event.Reason)
		}
	})

	t.Run("non-auth error", func(t *testing.T) {
		if event := c.classifyCommandError(errors.New("ERR unknown command")); event != nil {
			t.Fatalf("expected nil event for non-auth command error, got: %+v", event)
		}
	})
}

func TestConnectionExceptionEvent(t *testing.T) {
	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.1", Port: 6379}}
	err := errors.New("dial tcp: connection refused")

	event := c.connectionExceptionEvent(err)

	if event.Name != haprobe.DbEventNameDetectFailure {
		t.Fatalf("unexpected name: %s", event.Name)
	}
	if event.Reason != haprobe.DbEventNameReasonConnectionException {
		t.Fatalf("unexpected reason: %d", event.Reason)
	}
	if event.DbTypeName != haprobe.DbTypeRedis {
		t.Fatalf("unexpected db type: %s", event.DbTypeName)
	}
	if event.Endpoint != c.endpoint {
		t.Fatalf("unexpected endpoint: %+v", event.Endpoint)
	}
	if event.Message != err.Error() {
		t.Fatalf("unexpected message: %s", event.Message)
	}
}

func TestAuthExceptionEvent(t *testing.T) {
	c := &collector{endpoint: &hanet.Endpoint{Host: "127.0.0.2", Port: 6379}}
	err := errors.New("NOAUTH Authentication required")

	event := c.authExceptionEvent(err)

	if event.Name != haprobe.DbEventNameDetectRedisAuthFailureV1 {
		t.Fatalf("unexpected name: %s", event.Name)
	}
	if event.Reason != haprobe.DbEventNameReasonAuthException {
		t.Fatalf("unexpected reason: %d", event.Reason)
	}
	if event.DbTypeName != haprobe.DbTypeRedis {
		t.Fatalf("unexpected db type: %s", event.DbTypeName)
	}
	if event.Endpoint != c.endpoint {
		t.Fatalf("unexpected endpoint: %+v", event.Endpoint)
	}
	if event.Message != err.Error() {
		t.Fatalf("unexpected message: %s", event.Message)
	}
}

func TestCollectorTypeChecks(t *testing.T) {
	tests := []struct {
		name          string
		accessLayer   haprobe.DbmMetadataAccessLayerType
		machineType   haprobe.DbmMetadataMachineType
		isTwemproxy   bool
		isPredixy     bool
		isTendisCache bool
		isTendisSSD   bool
		isTendisPlus  bool
	}{
		{
			name:        "twemproxy",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypeTwemProxy,
			isTwemproxy: true,
		},
		{
			name:        "predixy",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypePredixy,
			isPredixy:   true,
		},
		{
			name:          "tendiscache",
			accessLayer:   haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType:   haprobe.DbmMetadataMachineTypeTendisCache,
			isTendisCache: true,
		},
		{
			name:        "tendisssd",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisSSD,
			isTendisSSD: true,
		},
		{
			name:         "tendisplus",
			accessLayer:  haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType:  haprobe.DbmMetadataMachineTypeTendisPlus,
			isTendisPlus: true,
		},
		{
			name:        "unknown machine type",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeBackend,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := &collector{
				accessLayer: tt.accessLayer,
				machineType: tt.machineType,
			}
			if got := c.isTwemproxy(); got != tt.isTwemproxy {
				t.Errorf("isTwemproxy() = %v, want %v", got, tt.isTwemproxy)
			}
			if got := c.isPredixy(); got != tt.isPredixy {
				t.Errorf("isPredixy() = %v, want %v", got, tt.isPredixy)
			}
			if got := c.isTendisCache(); got != tt.isTendisCache {
				t.Errorf("isTendisCache() = %v, want %v", got, tt.isTendisCache)
			}
			if got := c.isTendisSSD(); got != tt.isTendisSSD {
				t.Errorf("isTendisSSD() = %v, want %v", got, tt.isTendisSSD)
			}
			if got := c.isTendisPlus(); got != tt.isTendisPlus {
				t.Errorf("isTendisPlus() = %v, want %v", got, tt.isTendisPlus)
			}
		})
	}
}

func TestShouldSkipStorage(t *testing.T) {
	tests := []struct {
		name        string
		accessLayer haprobe.DbmMetadataAccessLayerType
		clusterType haprobe.DbmMetadataClusterType
		want        bool
	}{
		{
			name:        "predixy redis cluster storage",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			clusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
			want:        true,
		},
		{
			name:        "predixy tendisplus cluster storage",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
			want:        true,
		},
		{
			name:        "redis instance storage",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			clusterType: haprobe.DbmMetadataClusterTypeRedis,
			want:        false,
		},
		{
			name:        "predixy tendisplus instance storage",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusInstance,
			want:        false,
		},
		{
			name:        "predixy redis cluster proxy",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			clusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
			want:        false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := &collector{
				accessLayer: tt.accessLayer,
				clusterType: tt.clusterType,
			}
			if got := c.shouldSkipStorage(); got != tt.want {
				t.Fatalf("shouldSkipStorage() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsProxyInstance(t *testing.T) {
	tests := []struct {
		name        string
		accessLayer haprobe.DbmMetadataAccessLayerType
		machineType haprobe.DbmMetadataMachineType
		clusterType haprobe.DbmMetadataClusterType
		want        bool
	}{
		{
			name:        "twemproxy redis instance",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypeTwemProxy,
			clusterType: haprobe.DbmMetadataClusterTypeTwemproxyRedis,
			want:        true,
		},
		{
			name:        "twemproxy tendisssd instance",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypeTwemProxy,
			clusterType: haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD,
			want:        true,
		},
		{
			name:        "predixy redis cluster",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypePredixy,
			clusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
			want:        true,
		},
		{
			name:        "predixy tendisplus cluster",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypePredixy,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
			want:        true,
		},
		{
			name:        "predixy tendisplus instance",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypePredixy,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusInstance,
			want:        true,
		},
		{
			name:        "twemproxy with unknown cluster",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypeTwemProxy,
			clusterType: haprobe.DbmMetadataClusterTypeRedis,
			want:        false,
		},
		{
			name:        "storage layer",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisCache,
			clusterType: haprobe.DbmMetadataClusterTypeRedis,
			want:        false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := &collector{
				accessLayer: tt.accessLayer,
				machineType: tt.machineType,
				clusterType: tt.clusterType,
			}
			if got := c.isProxyInstance(); got != tt.want {
				t.Fatalf("isProxyInstance() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestIsStorageInstance(t *testing.T) {
	tests := []struct {
		name        string
		accessLayer haprobe.DbmMetadataAccessLayerType
		machineType haprobe.DbmMetadataMachineType
		clusterType haprobe.DbmMetadataClusterType
		want        bool
	}{
		{
			name:        "twemproxy redis instance tendiscache",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisCache,
			clusterType: haprobe.DbmMetadataClusterTypeTwemproxyRedis,
			want:        true,
		},
		{
			name:        "redis instance tendiscache",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisCache,
			clusterType: haprobe.DbmMetadataClusterTypeRedis,
			want:        true,
		},
		{
			name:        "predixy redis cluster tendiscache excluded",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisCache,
			clusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
			want:        false,
		},
		{
			name:        "twemproxy tendisssd instance tendisssd",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisSSD,
			clusterType: haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD,
			want:        true,
		},
		{
			name:        "predixy tendisplus instance tendisplus",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisPlus,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusInstance,
			want:        true,
		},
		{
			name:        "predixy tendisplus cluster tendisplus excluded",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeStorage,
			machineType: haprobe.DbmMetadataMachineTypeTendisPlus,
			clusterType: haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
			want:        false,
		},
		{
			name:        "proxy layer",
			accessLayer: haprobe.DbmMetadataAccessLayerTypeProxy,
			machineType: haprobe.DbmMetadataMachineTypePredixy,
			clusterType: haprobe.DbmMetadataClusterTypePredixyRedisCluster,
			want:        false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := &collector{
				accessLayer: tt.accessLayer,
				machineType: tt.machineType,
				clusterType: tt.clusterType,
			}
			if got := c.isStorageInstance(); got != tt.want {
				t.Fatalf("isStorageInstance() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestCollectorClose_NilRdb(t *testing.T) {
	c := &collector{}
	c.close() // should not panic
}
