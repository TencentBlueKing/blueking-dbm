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

package detector

import (
	"context"
	"errors"
	"net"
	"testing"
	"time"
)

// testLoopbackIP keeps every probe target inside the loopback range.
const testLoopbackIP = "127.0.0.1"

// freeLoopbackPort returns a loopback port that nothing is listening on, so a
// dial to it is refused instead of timing out.
func freeLoopbackPort(t *testing.T) int {
	t.Helper()

	ln, err := net.Listen("tcp", testLoopbackIP+":0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}
	addr, ok := ln.Addr().(*net.TCPAddr)
	if !ok {
		_ = ln.Close()
		t.Fatalf("unexpected listener address type: %T", ln.Addr())
	}
	if err := ln.Close(); err != nil {
		t.Fatalf("close listener failed, errmsg: %s", err)
	}

	return addr.Port
}

// TestRunConnectionRefused verifies that a refused TCP connection is reported as
// a connect failure, never as a timeout.
func TestRunConnectionRefused(t *testing.T) {
	sshCli := &Ssh{ip: testLoopbackIP, port: freeLoopbackPort(t), user: "root", timeout: 2 * time.Second}

	start := time.Now()
	resp, err := sshCli.Run("echo ok")
	elapsed := time.Since(start)

	if !errors.Is(err, ErrDetectorCreateSshConnection) {
		t.Fatalf("want ErrDetectorCreateSshConnection, got: %v", err)
	}
	if errors.Is(err, ErrDetectorSshConnectTimeout) {
		t.Fatalf("a refused connection must not be classified as a timeout: %v", err)
	}
	if resp != nil {
		t.Fatalf("no response is expected when the connection is refused, got: %+v", resp)
	}
	if elapsed > time.Second {
		t.Fatalf("a refused connection must fail fast, elapsed: %v", elapsed)
	}
}

// TestClassifySshErr verifies how a stage error is mapped onto the sentinels.
func TestClassifySshErr(t *testing.T) {
	plainErr := errors.New("connection refused")

	cases := []struct {
		name     string
		err      error
		stageErr error
		want     error
	}{
		{name: "net timeout", err: timeoutNetError{}, stageErr: ErrDetectorCreateSshConnection,
			want: ErrDetectorSshConnectTimeout},
		{name: "context deadline", err: context.DeadlineExceeded, stageErr: ErrDetectorCreateSshSession,
			want: ErrDetectorSshConnectTimeout},
		{name: "plain error keeps the stage", err: plainErr, stageErr: ErrDetectorCreateSshConnection,
			want: ErrDetectorCreateSshConnection},
		{name: "nil error keeps the stage", err: nil, stageErr: ErrDetectorCreateSshSession,
			want: ErrDetectorCreateSshSession},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := classifySshErr(tc.err, tc.stageErr); !errors.Is(got, tc.want) {
				t.Fatalf("want %v, got: %v", tc.want, got)
			}
		})
	}
}

// timeoutNetError is a net.Error that reports itself as timed out.
type timeoutNetError struct{}

// Error implements the error interface.
func (timeoutNetError) Error() string { return "i/o timeout" }

// Timeout implements the net.Error interface.
func (timeoutNetError) Timeout() bool { return true }

// Temporary implements the net.Error interface.
func (timeoutNetError) Temporary() bool { return false }

// newStuckListener starts a TCP listener on 127.0.0.1 whose handler keeps the
// connection open without completing the SSH handshake.
func newStuckListener(t *testing.T, onAccept func(conn net.Conn)) (*Ssh, func()) {
	t.Helper()

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed, errmsg: %s", err)
	}

	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			go func() {
				defer func() { _ = conn.Close() }()
				onAccept(conn)
			}()
		}
	}()

	addr, ok := ln.Addr().(*net.TCPAddr)
	if !ok {
		_ = ln.Close()
		t.Fatalf("unexpected listener address type: %T", ln.Addr())
	}

	// A tiny budget keeps the test fast; the production default is much larger.
	sshCli := &Ssh{ip: "127.0.0.1", port: addr.Port, user: "root", timeout: 100 * time.Millisecond}

	return sshCli, func() { _ = ln.Close() }
}

// TestRunBannerBlackhole verifies that a server which accepts the connection but
// never sends its banner no longer blocks forever: the overall budget must bound
// the handshake stage.
func TestRunBannerBlackhole(t *testing.T) {
	sshCli, cleanup := newStuckListener(t, func(_ net.Conn) {
		time.Sleep(2 * time.Second) // stay silent: no banner at all
	})
	defer cleanup()

	start := time.Now()
	_, err := sshCli.Run("echo ok")
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("Run must fail when the handshake never completes")
	}
	if !errors.Is(err, ErrDetectorSshConnectTimeout) {
		t.Fatalf("want ErrDetectorSshConnectTimeout, got: %v", err)
	}
	if elapsed > time.Second {
		t.Fatalf("Run took too long: %v", elapsed)
	}
}

// TestRunKexStalled verifies that a server which sends its banner but never
// answers the key exchange is bounded by the same budget.
func TestRunKexStalled(t *testing.T) {
	sshCli, cleanup := newStuckListener(t, func(conn net.Conn) {
		_, _ = conn.Write([]byte("SSH-2.0-stalled\r\n"))
		time.Sleep(2 * time.Second) // banner sent, then stay silent
	})
	defer cleanup()

	start := time.Now()
	_, err := sshCli.Run("echo ok")
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("Run must fail when the key exchange never completes")
	}
	if !errors.Is(err, ErrDetectorSshConnectTimeout) {
		t.Fatalf("want ErrDetectorSshConnectTimeout, got: %v", err)
	}
	if elapsed > time.Second {
		t.Fatalf("Run took too long: %v", elapsed)
	}
}
