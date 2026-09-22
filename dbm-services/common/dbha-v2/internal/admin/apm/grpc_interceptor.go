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
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	goproto "google.golang.org/protobuf/proto"
)

var allowedGRPCMethods = map[string]struct{}{
	"Heartbeat":      {},
	"GetProbeConfig": {},
}

var allowedGRPCCodes = map[codes.Code]struct{}{
	codes.OK: {}, codes.Canceled: {}, codes.Unknown: {}, codes.InvalidArgument: {},
	codes.DeadlineExceeded: {}, codes.NotFound: {}, codes.AlreadyExists: {}, codes.PermissionDenied: {},
	codes.ResourceExhausted: {}, codes.FailedPrecondition: {}, codes.Aborted: {}, codes.OutOfRange: {},
	codes.Unimplemented: {}, codes.Internal: {}, codes.Unavailable: {}, codes.DataLoss: {},
	codes.Unauthenticated: {},
}

// UnaryServerInterceptor records bounded admin gRPC metrics around unary handlers.
func UnaryServerInterceptor() grpc.UnaryServerInterceptor {
	return func(
		ctx context.Context,
		req any,
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (any, error) {
		start := time.Now()
		fullMethod := ""
		if info != nil {
			fullMethod = info.FullMethod
		}
		reply, err := handler(ctx, req)
		recordGRPCMetrics(grpcMethodName(fullMethod), req, reply, err, time.Since(start))
		return reply, err
	}
}

func recordGRPCMetrics(method string, req, reply any, err error, elapsed time.Duration) {
	grpcCode := grpcCodeLabel(err)
	methodLabels := map[string]string{MetricLabelMethod: method}
	requestLabels := map[string]string{
		MetricLabelMethod: method, MetricLabelGRPCCode: grpcCode,
	}

	if recErr := GRPCRequestsTotal.IncWithLabels(requestLabels); recErr != nil {
		logger.Warn("failed to record grpc_requests_total, errmsg: %s", recErr)
	}

	if recErr := GRPCRequestDurationMs.ObserveWithLabels(
		methodLabels, float64(elapsed.Milliseconds()),
	); recErr != nil {
		logger.Warn("failed to record grpc_request_duration_ms, errmsg: %s", recErr)
	}

	if recErr := GRPCRequestSizeBytes.ObserveWithLabels(
		methodLabels, protoMessageSize(req),
	); recErr != nil {
		logger.Warn("failed to record grpc_request_size_bytes, errmsg: %s", recErr)
	}

	if recErr := GRPCResponseSizeBytes.ObserveWithLabels(
		methodLabels, protoMessageSize(reply),
	); recErr != nil {
		logger.Warn("failed to record grpc_response_size_bytes, errmsg: %s", recErr)
	}

	if grpcCode != codes.OK.String() {
		if recErr := GRPCRequestErrorsTotal.IncWithLabels(methodLabels); recErr != nil {
			logger.Warn("failed to record grpc_request_errors_total, errmsg: %s", recErr)
		}
	}

	recordProbeConfigResult(err, reply)
}

func recordProbeConfigResult(err error, reply any) {
	if err != nil {
		return
	}
	resp, ok := reply.(*proto.ProbeConfigResponse)
	if !ok {
		return
	}
	if recErr := GRPCProbeConfigResultTotal.IncWithLabels(map[string]string{
		MetricLabelCode: probeConfigResultLabel(resp.GetCode()),
	}); recErr != nil {
		logger.Warn("failed to record grpc_probe_config_result_total, errmsg: %s", recErr)
	}
}

func grpcMethodName(fullMethod string) string {
	name := fullMethod
	if idx := strings.LastIndex(fullMethod, "/"); idx >= 0 && idx+1 < len(fullMethod) {
		name = fullMethod[idx+1:]
	}
	if _, ok := allowedGRPCMethods[name]; ok {
		return name
	}
	return metricLabelUnknown
}

func grpcCodeLabel(err error) string {
	code := status.Code(err)
	if _, ok := allowedGRPCCodes[code]; ok {
		return code.String()
	}
	return metricLabelUnknown
}

func probeConfigResultLabel(code proto.ProbeConfigCode) string {
	switch code {
	case proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS:
		return "SUCCESS"
	case proto.ProbeConfigCode_PROBE_CONFIG_FAIL:
		return "FAIL"
	case proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA:
		return "NO_DATA"
	default:
		return metricLabelUnknown
	}
}

func protoMessageSize(msg any) float64 {
	encoded, ok := msg.(goproto.Message)
	if !ok || encoded == nil {
		return 0
	}
	return float64(goproto.Size(encoded))
}
