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

package apm

import (
	"context"
	"testing"

	"dbm-services/common/dbha-v2/pkg/proto"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/testutil"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

func TestGRPCMethodNameAllowlist(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{in: "/dbha.v2.AdminService/Heartbeat", want: "Heartbeat"},
		{in: "/dbha.v2.AdminService/GetProbeConfig", want: "GetProbeConfig"},
		{in: "Heartbeat", want: "Heartbeat"},
		{in: "/dbha.v2.AdminService/Hack", want: metricLabelUnknown},
		{in: "", want: metricLabelUnknown},
	}
	for _, tc := range cases {
		if got := grpcMethodName(tc.in); got != tc.want {
			t.Fatalf("grpcMethodName(%s)=%s, want: %s", tc.in, got, tc.want)
		}
	}
}

func TestGRPCCodeLabelAllowlist(t *testing.T) {
	if got := grpcCodeLabel(nil); got != codes.OK.String() {
		t.Fatalf("nil error grpc_code: %s, want: OK", got)
	}
	if got := grpcCodeLabel(status.Error(codes.Unavailable, "storage is reloading")); got != codes.Unavailable.String() {
		t.Fatalf("unavailable grpc_code: %s", got)
	}
	if got := grpcCodeLabel(status.Error(codes.Code(99), "x")); got != metricLabelUnknown {
		t.Fatalf("unknown grpc_code: %s, want: %s", got, metricLabelUnknown)
	}
}

func TestProbeConfigResultLabelAllowlist(t *testing.T) {
	cases := []struct {
		in   proto.ProbeConfigCode
		want string
	}{
		{in: proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS, want: "SUCCESS"},
		{in: proto.ProbeConfigCode_PROBE_CONFIG_FAIL, want: "FAIL"},
		{in: proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA, want: "NO_DATA"},
		{in: proto.ProbeConfigCode(99), want: metricLabelUnknown},
	}
	for _, tc := range cases {
		if got := probeConfigResultLabel(tc.in); got != tc.want {
			t.Fatalf("probeConfigResultLabel(%d)=%s, want: %s", tc.in, got, tc.want)
		}
	}
}

func TestUnaryInterceptorOKDoesNotCountErrors(t *testing.T) {
	requests, errors, results := bindGRPCTestCollectors(t)
	_, err := UnaryServerInterceptor()(
		context.Background(),
		&proto.HeartbeatRequest{},
		&grpc.UnaryServerInfo{FullMethod: "/dbha.v2.AdminService/Heartbeat"},
		func(context.Context, any) (any, error) {
			return &proto.HeartbeatResponse{Errmsg: "success"}, nil
		},
	)
	if err != nil {
		t.Fatalf("heartbeat handler failed, errmsg: %s", err)
	}
	if got := testutil.ToFloat64(requests.WithLabelValues("Heartbeat", codes.OK.String())); got != 1 {
		t.Fatalf("grpc_requests_total: %v, want: 1", got)
	}
	if got := testutil.ToFloat64(errors.WithLabelValues("Heartbeat")); got != 0 {
		t.Fatalf("grpc_request_errors_total: %v, want: 0", got)
	}
	if got := testutil.ToFloat64(results.WithLabelValues("FAIL")); got != 0 {
		t.Fatalf("probe result FAIL: %v, want: 0", got)
	}
}

func TestUnaryInterceptorUnavailableCountsErrors(t *testing.T) {
	requests, errors, _ := bindGRPCTestCollectors(t)
	_, err := UnaryServerInterceptor()(
		context.Background(),
		&proto.HeartbeatRequest{},
		&grpc.UnaryServerInfo{FullMethod: "/dbha.v2.AdminService/Heartbeat"},
		func(context.Context, any) (any, error) {
			return nil, status.Error(codes.Unavailable, "storage is reloading")
		},
	)
	if status.Code(err) != codes.Unavailable {
		t.Fatalf("want Unavailable, errmsg: %s", err)
	}
	if got := testutil.ToFloat64(requests.WithLabelValues("Heartbeat", codes.Unavailable.String())); got != 1 {
		t.Fatalf("grpc_requests_total unavailable: %v, want: 1", got)
	}
	if got := testutil.ToFloat64(errors.WithLabelValues("Heartbeat")); got != 1 {
		t.Fatalf("grpc_request_errors_total: %v, want: 1", got)
	}
}

func TestUnaryInterceptorProbeConfigFailIsNotGRPCError(t *testing.T) {
	_, errors, results := bindGRPCTestCollectors(t)
	_, err := UnaryServerInterceptor()(
		context.Background(),
		&proto.ProbeConfigRequest{Ip: "127.0.0.1"},
		&grpc.UnaryServerInfo{FullMethod: "/dbha.v2.AdminService/GetProbeConfig"},
		func(context.Context, any) (any, error) {
			return &proto.ProbeConfigResponse{Code: proto.ProbeConfigCode_PROBE_CONFIG_FAIL}, nil
		},
	)
	if err != nil {
		t.Fatalf("GetProbeConfig FAIL should be grpc OK, errmsg: %s", err)
	}
	if got := testutil.ToFloat64(errors.WithLabelValues("GetProbeConfig")); got != 0 {
		t.Fatalf("grpc_request_errors_total: %v, want: 0", got)
	}
	if got := testutil.ToFloat64(results.WithLabelValues("FAIL")); got != 1 {
		t.Fatalf("grpc_probe_config_result_total FAIL: %v, want: 1", got)
	}
}

func TestUnaryInterceptorUnknownMethodLabel(t *testing.T) {
	requests, _, _ := bindGRPCTestCollectors(t)
	_, err := UnaryServerInterceptor()(
		context.Background(),
		&proto.HeartbeatRequest{},
		&grpc.UnaryServerInfo{FullMethod: "/dbha.v2.AdminService/Hack"},
		func(context.Context, any) (any, error) {
			return &proto.HeartbeatResponse{}, nil
		},
	)
	if err != nil {
		t.Fatalf("handler failed, errmsg: %s", err)
	}
	if got := testutil.ToFloat64(requests.WithLabelValues(metricLabelUnknown, codes.OK.String())); got != 1 {
		t.Fatalf("unknown method requests: %v, want: 1", got)
	}
}

func bindGRPCTestCollectors(t *testing.T) (*prometheus.CounterVec, *prometheus.CounterVec, *prometheus.CounterVec) {
	t.Helper()
	requests := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "test_grpc_requests_total", Help: "test",
	}, []string{MetricLabelMethod, MetricLabelGRPCCode})
	errors := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "test_grpc_request_errors_total", Help: "test",
	}, []string{MetricLabelMethod})
	results := prometheus.NewCounterVec(prometheus.CounterOpts{
		Name: "test_grpc_probe_config_result_total", Help: "test",
	}, []string{MetricLabelCode})
	prevReq := GRPCRequestsTotal.ToMetric().Collector
	prevErr := GRPCRequestErrorsTotal.ToMetric().Collector
	prevRes := GRPCProbeConfigResultTotal.ToMetric().Collector
	GRPCRequestsTotal.ToMetric().Collector = requests
	GRPCRequestErrorsTotal.ToMetric().Collector = errors
	GRPCProbeConfigResultTotal.ToMetric().Collector = results
	t.Cleanup(func() {
		GRPCRequestsTotal.ToMetric().Collector = prevReq
		GRPCRequestErrorsTotal.ToMetric().Collector = prevErr
		GRPCProbeConfigResultTotal.ToMetric().Collector = prevRes
	})
	return requests, errors, results
}
