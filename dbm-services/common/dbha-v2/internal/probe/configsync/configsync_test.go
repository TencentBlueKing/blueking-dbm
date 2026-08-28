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

package configsync_test

import (
	"context"
	"errors"
	"net"
	"sync/atomic"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/configsync"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
)

// stubAdmin is a minimal admin service that answers GetProbeConfig with a canned response and
// records how many calls it received, so tests can tell a skipped endpoint from a tried one.
type stubAdmin struct {
	proto.UnimplementedAdminServiceServer

	resp  *proto.ProbeConfigResponse
	calls atomic.Int32
}

func (s *stubAdmin) GetProbeConfig(
	_ context.Context, _ *proto.ProbeConfigRequest,
) (*proto.ProbeConfigResponse, error) {
	s.calls.Add(1)
	return s.resp, nil
}

// startStubAdmin serves stub on a loopback port for the duration of the test.
func startStubAdmin(t *testing.T, stub *stubAdmin) string {
	t.Helper()

	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	srv := grpc.NewServer()
	proto.RegisterAdminServiceServer(srv, stub)
	go func() { _ = srv.Serve(lis) }()
	t.Cleanup(srv.Stop)

	return lis.Addr().String()
}

func fetchFrom(t *testing.T, endpoints []string) error {
	t.Helper()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_, err := configsync.Fetch(ctx, endpoints, &proto.ProbeConfigRequest{Ip: "127.0.0.1"})

	return err
}

// TestFetch_NoDataIsDistinctFromFailure is what lets periodic sync tell "admin has nothing for
// this machine" apart from "admin is unreachable". The two need opposite handling: the first is
// a stable answer to report once, the second is worth retrying.
func TestFetch_NoDataIsDistinctFromFailure(t *testing.T) {
	stub := &stubAdmin{resp: &proto.ProbeConfigResponse{
		Code:   proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA,
		Errmsg: "no data",
	}}
	endpoint := startStubAdmin(t, stub)

	err := fetchFrom(t, []string{endpoint})
	if !errors.Is(err, configsync.ErrNoData) {
		t.Fatalf("expected ErrNoData, errmsg: %s", err)
	}
}

// TestFetch_NoDataSkipsRemainingEndpoints keeps the walk from asking every admin the same
// question: they share one metadata source, so the answer would not change.
func TestFetch_NoDataSkipsRemainingEndpoints(t *testing.T) {
	first := &stubAdmin{resp: &proto.ProbeConfigResponse{Code: proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA}}
	second := &stubAdmin{resp: &proto.ProbeConfigResponse{
		Code:    proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS,
		Payload: `{"metadata":[]}`,
	}}

	err := fetchFrom(t, []string{startStubAdmin(t, first), startStubAdmin(t, second)})
	if !errors.Is(err, configsync.ErrNoData) {
		t.Fatalf("expected ErrNoData, errmsg: %s", err)
	}
	if got := second.calls.Load(); got != 0 {
		t.Errorf("second endpoint should not have been queried, calls: %d", got)
	}
}

// TestFetch_FailoverToNextEndpoint is the counterpart: a real failure must move on to the next
// admin instead of giving up.
func TestFetch_FailoverToNextEndpoint(t *testing.T) {
	failing := &stubAdmin{resp: &proto.ProbeConfigResponse{
		Code:   proto.ProbeConfigCode_PROBE_CONFIG_FAIL,
		Errmsg: "internal",
	}}
	healthy := &stubAdmin{resp: &proto.ProbeConfigResponse{
		Code:    proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS,
		Payload: `{"metadata":[{"ip":"127.0.0.1","port":3306}]}`,
	}}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	payload, err := configsync.Fetch(
		ctx,
		[]string{startStubAdmin(t, failing), startStubAdmin(t, healthy)},
		&proto.ProbeConfigRequest{Ip: "127.0.0.1"},
	)
	if err != nil {
		t.Fatalf("fetch failed, errmsg: %s", err)
	}
	if len(payload.Metadata) != 1 {
		t.Fatalf("unexpected metadata, got: %+v", payload.Metadata)
	}
	if got := healthy.calls.Load(); got != 1 {
		t.Errorf("healthy endpoint calls: %d, want 1", got)
	}
}

// TestFetch_LegacyAdminPayloadIsReported keeps the version-mismatch hint that already existed:
// an older admin answers with a bare metadata array and the operator needs to be told why.
func TestFetch_LegacyAdminPayloadIsReported(t *testing.T) {
	stub := &stubAdmin{resp: &proto.ProbeConfigResponse{
		Code:    proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS,
		Payload: `[{"ip":"127.0.0.1","port":3306}]`,
	}}

	err := fetchFrom(t, []string{startStubAdmin(t, stub)})
	if err == nil {
		t.Fatal("expected legacy payload to be rejected")
	}
	if errors.Is(err, configsync.ErrNoData) {
		t.Fatal("a legacy payload is a version mismatch, not missing data")
	}
}
