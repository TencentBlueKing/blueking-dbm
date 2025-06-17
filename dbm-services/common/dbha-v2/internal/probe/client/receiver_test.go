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
	"dbm-services/common/dbha-v2/internal/receiver/service"
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

const (
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

	svr, err := service.NewReceiverServer(receiverAddress)
	if err != nil {
		logger.Fatal("make receiver server failed. errmsg(%v)", err)
		return
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := svr.Run(); err != nil {
			logger.Fatal("receiver exited. errmsg(%v)", err)
			return
		}
	}()

	wg.Add(1)
	go func(ctx context.Context) {
		defer wg.Done()
		select {
		case <-ctx.Done():
			time.Sleep(1 * time.Second)
			svr.Close()
			break
		}
	}(ctx)

	for i := 0; i < maxConnection; i++ {
		wg.Add(1)
		go func(ctx context.Context) {
			defer wg.Done()

			cli, err := connectReceiverServer(ctx)
			if err != nil {
				logger.Fatal("create receiver client failed. errmsg(%v)", err)
			}

			receiverClients = append(receiverClients, cli)

			select {
			case <-ctx.Done():
				cli.Close()
				break
			}
		}(ctx)
	}
}

func connectReceiverServer(ctx context.Context) (*client.ReceiverClient, error) {

	cli, err := client.NewReceiverClient(ctx, receiverAddress, receiverClientID)
	if err != nil {
		logger.Fatal("make receiver client failed. errmsg(%v)", err)
		return nil, err
	}

	err = cli.Connect()
	if err != nil {
		logger.Fatal("receiver client run failed. errmsg(%v)", err)
		return nil, err
	}

	return cli, nil
}

func TestPushData(t *testing.T) {

	for {
		if len(receiverClients) == 0 {
			time.Sleep(1 * time.Second)
			continue
		}
		break
	}

	logger.Info("send a message to receiver server")

	idx := rng.Intn(len(receiverClients))
	cli := receiverClients[idx]
	err := cli.SendMessage([]byte("hello world"))

	if err != nil {
		logger.Error("receiver client send message failed. errmsg(%v)", err)
	}

	logger.Info("send a message to receiver server finished")
}

func BenchmarkPushDataConnection(b *testing.B) {
	for i := 0; i < b.N; i++ {
		idx := rng.Intn(len(receiverClients))
		cli := receiverClients[idx]
		err := cli.SendMessage([]byte("random send a message(hello world)"))
		if err != nil {
			logger.Error("send a message failed by random client, errmsg(%v)", err)
		}
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
