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

// Package sink stores receiver messages in configured backend databases.
package sink

import (
	"context"
	"strings"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Sinker Define the interface for storing data.
type Sinker interface {
	Save(msg *Message) error
	Close()
}

// BatchResult summarizes one SaveBatch call.
// Valid is the count of messages that passed validation (before dedup).
// Invalid is JSON-illegal or unknown harvest_type count.
// Failed is rows that ultimately were not written on any endpoint.
// Stats counts each input message once: written, or one drop reason.
type BatchResult struct {
	Valid   int
	Invalid int
	Failed  int
	Stats   WriteStats
}

// BatchSinker optionally writes many messages in one call.
// error is non-nil only when ctx is done or the sink is closed; other failures
// are reported via BatchResult.Failed.
// Implementations must fill Stats so Written plus the drop total equals len(msgs).
// A sinker that leaves Stats empty is omitted from the sink delay and drop metrics.
type BatchSinker interface {
	SaveBatch(ctx context.Context, msgs []*Message) (BatchResult, error)
}

// NewSinker create a new saver
func NewSinker(cfg config.SinkConfig) (Sinker, error) {
	switch strings.ToLower(cfg.Name) {
	case strings.ToLower(mySQLName):
		return newMySql(cfg)

	default:
		return nil, gerrors.Newf(gerrors.Unsupported, "unsupported storage(%s)", cfg.Name)
	}
}
