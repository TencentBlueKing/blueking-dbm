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
	"testing"
	"time"

	"golang.org/x/net/context"
)

func runReceiverServer(ctx context.Context) error {

	svr, err := service.NewReceiverServer(receiverAddress)
	if err != nil {
		logger.Fatal("make receiver server failed. errmsg(%v)", err)
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := svr.Run(); err != nil {
			logger.Fatal("receiver exited. errmsg(%v)", err)
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

	return nil
}

func connectReceiverServer(ctx context.Context) error {
	for i := 0; i < maxConnection; i++ {
		wg.Add(1)
		go func(ctx context.Context) {
			defer wg.Done()

			cli, err := client.NewReceiverClient(ctx, receiverAddress, receiverClientID)
			if err != nil {
				logger.Fatal("make receiver client failed. errmsg(%v)", err)
			}

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

	return nil
}

func TestPushData(t *testing.T) {
	for {
		if len(receiverClients) == 0 {
			time.Sleep(1 * time.Second)
			continue
		}
		break
	}

	idx := rng.Intn(len(receiverClients))
	cli := receiverClients[idx]
	err := cli.SendMessage([]byte("hello world"))

	if err != nil {
		t.Errorf("receiver client send message failed. errmsg(%v)", err)
	}
}

func BenchmarkPushDataConnection(b *testing.B) {
	for i := 0; i < b.N; i++ {
		idx := rng.Intn(len(receiverClients))
		cli := receiverClients[idx]
		err := cli.SendMessage([]byte("random send a message(hello world)"))
		if err != nil {
			b.Errorf("send a message failed by random client, errmsg(%v)", err)
		}
	}
}
