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

package discovery

import (
	"fmt"
	"sync"
	"testing"

	"go.uber.org/zap"

	"dbm-services/common/dbha-v2/pkg/logger"
)

type capturedLog struct {
	level   string
	message string
}

type captureLogger struct {
	mu      sync.Mutex
	entries []capturedLog
}

// installCaptureLogger replaces the process-wide logger until the test ends.
func installCaptureLogger(t *testing.T) *captureLogger {
	t.Helper()
	prev := logger.Log()
	capture := &captureLogger{}
	logger.SetLogger(capture)
	t.Cleanup(func() { logger.SetLogger(prev) })

	return capture
}

func (l *captureLogger) OriginLogger() *zap.Logger { return zap.NewNop() }

func (l *captureLogger) Debug(format string, args ...any) { l.add("debug", format, args...) }
func (l *captureLogger) Info(format string, args ...any)  { l.add("info", format, args...) }
func (l *captureLogger) Warn(format string, args ...any)  { l.add("warn", format, args...) }
func (l *captureLogger) Error(format string, args ...any) { l.add("error", format, args...) }
func (l *captureLogger) Fatal(format string, args ...any) { l.add("fatal", format, args...) }

func (l *captureLogger) add(level, format string, args ...any) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.entries = append(l.entries, capturedLog{level: level, message: fmt.Sprintf(format, args...)})
}

func (l *captureLogger) logs() []capturedLog {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := make([]capturedLog, len(l.entries))
	copy(out, l.entries)

	return out
}
