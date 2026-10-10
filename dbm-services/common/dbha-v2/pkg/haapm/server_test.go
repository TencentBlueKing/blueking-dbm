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

package haapm

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/stretchr/testify/require"
)

func freeLoopbackAddr(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	addr := ln.Addr().String()
	require.NoError(t, ln.Close())
	return addr
}

func TestBindPrometheusIdempotentAndRestart(t *testing.T) {
	name := fmt.Sprintf("haapm_restart_%d", time.Now().UnixNano())
	counter := NewHaCounter(name, "test counter for restart")

	addr1 := freeLoopbackAddr(t)
	svr := NewServer(ServerConfig{Addr: addr1, Subsystem: "dbha_v2_test"})
	svr.Register(counter)
	require.NoError(t, svr.Start())
	require.NotNil(t, counter.ToMetric().Collector)

	require.NoError(t, svr.Stop())
	// Reuse a fresh loopback port to avoid TIME_WAIT flakiness after Shutdown.
	require.NoError(t, svr.ApplyListenConfig(ServerConfig{Addr: freeLoopbackAddr(t)}),
		"restart after Stop must skip already-bound collectors")

	addr2 := freeLoopbackAddr(t)
	require.NoError(t, svr.ApplyListenConfig(ServerConfig{
		Addr:      addr2,
		Subsystem: "should_be_ignored",
	}))

	resp, err := http.Get("http://" + addr2 + "/metrics")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Contains(t, string(body), name)

	require.NoError(t, svr.Stop())
	prometheus.Unregister(counter.ToMetric().Collector)
}

func TestBindPrometheusSameNameDifferentObjectStillFails(t *testing.T) {
	name := fmt.Sprintf("haapm_dup_%d", time.Now().UnixNano())
	c1 := NewHaCounter(name, "first")
	c2 := NewHaCounter(name, "second")

	addr := freeLoopbackAddr(t)
	svr := NewServer(ServerConfig{Addr: addr, Subsystem: "dbha_v2_test_dup"})
	svr.Register(c1)
	require.NoError(t, svr.Start())
	require.NoError(t, svr.Stop())

	svr2 := NewServer(ServerConfig{Addr: freeLoopbackAddr(t), Subsystem: "dbha_v2_test_dup"})
	svr2.Register(c2)
	err := svr2.Start()
	require.Error(t, err, "different Metric objects with same name must still fail")

	prometheus.Unregister(c1.ToMetric().Collector)
}
