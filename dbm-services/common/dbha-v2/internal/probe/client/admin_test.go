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
	"bk-dbconfig/pkg/core/logger"
	"dbm-services/common/dbha-v2/internal/admin/service"
	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/pkg/proto"
	"testing"
	"time"

	"golang.org/x/net/context"
)

func runAdminServer(ctx context.Context) error {
	svr, err := service.NewAdminServer(adminAddress)
	if err != nil {
		logger.Fatal("make admin server failed. errmsg(%v)", err)
	}

	wg.Add(1)
	go func() {
		defer wg.Done()
		if err := svr.Run(); err != nil {
			logger.Fatal("admin exited. errmsg(%v)", err)
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

func connectAdminServer(ctx context.Context) error {
	for i := 0; i < maxConnection; i++ {
		wg.Add(1)
		go func(ctx context.Context) {
			defer wg.Done()

			cli, err := client.NewAdminClient(ctx, adminAddress, adminClientID)
			if err != nil {
				logger.Fatal("make admin client failed, errmsg(%v)", err)
			}

			adminClients = append(adminClients, cli)

			select {
			case <-ctx.Done():
				cli.Close()
				break
			}
		}(ctx)
	}

	return nil
}

func TestHeartbeat(t *testing.T) {
	for {
		if len(adminClients) == 0 {
			time.Sleep(1 * time.Second)
			continue
		}
		break
	}

	idx := rng.Intn(len(adminClients))
	cli := adminClients[idx]

	req := &proto.HeartbeatRequest{
		ClientID:      adminClientID,
		ConfigVersion: "v1.0.0",
	}

	resp, err := cli.HeartbeatRequest(req)
	if err != nil {
		t.Errorf("admin client post heartbeat request failed, errmsg(%v)", err)
		return
	}

	t.Logf("admin client heartheat response(%v)", resp)
}

func TestWatchConfig(t *testing.T) {
	for {
		if len(adminClients) == 0 {
			time.Sleep(1 * time.Second)
			continue
		}
		break
	}

	idx := rng.Intn(len(adminClients))
	cli := adminClients[idx]

	req := &proto.ProbeConfigRequest{
		ClientID: adminClientID,
	}

	respC, err := cli.WatchConfigRequest(req)
	if err != nil {
		t.Errorf("request config failed, errmsg(%v)", err)
	}

	select {
	case rsp, ok := <-respC:
		if !ok {
			t.Error("respond is failure")
			return
		}
		t.Logf("config request respond(%v)", rsp)
	}
}
