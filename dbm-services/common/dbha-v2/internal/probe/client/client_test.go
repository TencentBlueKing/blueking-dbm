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

package client_test

import (
	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/pkg/logger"
	"math/rand"
	"os"
	"sync"
	"testing"
	"time"

	"golang.org/x/net/context"
)

var wg sync.WaitGroup
var receiverClients []*client.ReceiverClient
var rng *rand.Rand
var maxConnection int = 3000
var adminClients []*client.AdminClient

const (
	adminAddress     = "127.0.0.1:28860"
	adminClientID    = "admin-cli-client"
	receiverAddress  = "127.0.0.1:28859"
	receiverClientID = "receiver-cli-cleint"
)

func setup(ctx context.Context) {
	logCfg := logger.Config{
		FileName:   "/var/log/dbha/probe.log",
		LogLevel:   "debug",
		MaxSizeMB:  100,
		MaxBackups: 10,
	}

	log := logger.NewZapLogger(logCfg)
	logger.SetLogger(log)
	src := rand.NewSource(time.Now().UnixNano())
	rng = rand.New(src)

	if err := runReceiverServer(ctx); err != nil {
		logger.Fatal("run receiver server failed. errmsg(%v)", err)
	}

	if err := runAdminServer(ctx); err != nil {
		logger.Fatal("run admin server failed. errmsg(%v)", err)
	}

	if err := connectReceiverServer(ctx); err != nil {
		logger.Fatal("create connection with receiver server, errmsg(%v)", err)
	}

	if err := connectAdminServer(ctx); err != nil {
		logger.Fatal("create connection with admin server, errmsg(%v)", err)
	}
}

func teardonw() {
	wg.Wait()
}

func TestMain(m *testing.M) {
	ctx, cancelFunc := context.WithCancel(context.Background())

	setup(ctx)

	code := m.Run()

	cancelFunc()

	teardonw()
	os.Exit(code)
}
