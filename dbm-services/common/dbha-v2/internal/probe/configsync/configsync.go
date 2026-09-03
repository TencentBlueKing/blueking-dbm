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

// Package configsync fetches probe configuration from admin and renders it to YAML.
//
// It holds the part of that flow shared by the gen-config command and the probe's periodic
// sync, and deliberately knows about neither. Locally owned fields, including persisted
// clearPorts, are injected through config.LocalFields. Scheduling, file locking and hot reload
// stay in the probe. Keeping the shared part here is what lets the running probe reuse it
// without importing the command package.
package configsync

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"

	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/proto"
)

// ErrNoData reports that admin has no metadata for this machine. It is a definite answer, not a
// failure: every admin would say the same, and the caller should treat it as "nothing to
// configure" rather than as an endpoint that needs retrying.
var ErrNoData = errors.New("admin has no metadata for this machine")

// Fetch asks the admin endpoints for this machine's configuration and returns the parsed
// payload. Endpoints are tried in order and the first successful answer wins; when all of them
// fail the last error is reported, since that is usually the informative one.
//
// The caller owns the context deadline: it bounds the whole walk over the endpoints, not each
// individual attempt.
//
// When admin knows nothing about this machine the error wraps ErrNoData; callers that sync
// periodically should recognise it and avoid rewriting a working config with an empty one.
func Fetch(
	ctx context.Context, endpoints []string, req *proto.ProbeConfigRequest,
) (probeconfig.ProbeConfigPayload, error) {
	raw, err := fetchPayload(ctx, endpoints, req)
	if err != nil {
		return probeconfig.ProbeConfigPayload{}, err
	}

	return unmarshalPayload(raw)
}

// Render turns a payload into the probe YAML document. Options carry the fields admin does not
// know about, such as the blocks the probe owns locally.
func Render(payload probeconfig.ProbeConfigPayload, opts ...config.GenOption) (string, error) {
	rendered, err := config.GenProbeYAML(payload, opts...)
	if err != nil {
		return "", fmt.Errorf("generate probe config: %w", err)
	}

	return rendered, nil
}

func fetchPayload(ctx context.Context, endpoints []string, req *proto.ProbeConfigRequest) (string, error) {
	var lastErr error
	for _, endpoint := range endpoints {
		adminClient, err := client.NewAdminClient(ctx, endpoint, "")
		if err != nil {
			lastErr = fmt.Errorf("create admin client for %s: %w", endpoint, err)
			continue
		}
		resp, err := adminClient.GetProbeConfig(ctx, req)
		adminClient.Close()
		if err != nil {
			lastErr = fmt.Errorf("get probe config from %s: %w", endpoint, err)
			continue
		}
		if resp.GetCode() == proto.ProbeConfigCode_PROBE_CONFIG_NO_DATA {
			// Answered, just with nothing: trying the remaining endpoints would only repeat
			// the same lookup, and reporting it as a failure would hide a real misconfiguration
			// behind a generic "all endpoints failed".
			return "", fmt.Errorf("%w, endpoint: %s, errmsg: %s", ErrNoData, endpoint, resp.GetErrmsg())
		}
		if resp.GetCode() != proto.ProbeConfigCode_PROBE_CONFIG_SUCCESS {
			lastErr = fmt.Errorf("admin %s returned code: %s, errmsg: %s",
				endpoint, resp.GetCode().String(), resp.GetErrmsg())

			continue
		}
		return resp.GetPayload(), nil
	}
	return "", fmt.Errorf("all admin endpoints failed, last error: %w", lastErr)
}

func unmarshalPayload(raw string) (probeconfig.ProbeConfigPayload, error) {
	var payload probeconfig.ProbeConfigPayload
	if err := json.Unmarshal([]byte(raw), &payload); err != nil {
		// Legacy admin returns a raw metadata list ([]ProbeMetadataItem) instead of ProbeConfigPayload;
		// detect this to provide a clear version-mismatch error rather than a generic unmarshal error.
		if len(raw) > 0 && raw[0] == '[' {
			return payload, fmt.Errorf(
				"admin returned legacy metadata array instead of ProbeConfigPayload, "+
					"please upgrade admin to match the probe version: %w", err)
		}
		return payload, fmt.Errorf("parse probe config payload from admin: %w", err)
	}
	return payload, nil
}
