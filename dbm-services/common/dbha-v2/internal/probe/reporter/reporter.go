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

package reporter

import (
	"context"
	"dbm-services/common/dbha-v2/internal/probe/client"
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"sync"
	"time"

	agentreport "github.com/TencentBlueKing/bk-gse-sdk/go/service/agent-report"
	"github.com/TencentBlueKing/bk-gse-sdk/go/types"
)

type Reporter struct {
	ClientId   string
	quit       chan struct{}
	recvCli    *client.ReceiverClient
	adminCli   *client.AdminClient
	wg         sync.WaitGroup
	recvConfig *config.GSEConfig
}

func (r *Reporter) keepalive() {
	ticker := time.NewTicker(5 * time.Second)

	for {
		select {
		case <-ticker.C:
			if err := r.PostToReceiver([]byte("keepalive")); err != nil {
				logger.Warn("post keepalive request to receiver failed, errmsg(%v)", err)
			}

		case <-r.quit:
			return
		}
	}
}

func (r *Reporter) CreateClients(ctx context.Context) error {
	receiver, err := client.NewReceiverClient(ctx, config.Cfg.Receiver.Endpoints, r.ClientId)
	if err != nil {
		return err
	}

	admin, err := client.NewAdminClient(ctx, config.Cfg.Admin.Endpoints, r.ClientId)
	if err != nil {
		return err
	}

	r.recvCli = receiver
	r.adminCli = admin
	r.quit = make(chan struct{}, 1)

	r.wg.Add(1)
	go func() {
		r.keepalive()
		r.wg.Done()
	}()

	return nil
}

func (r *Reporter) PostToReceiver(data []byte) error {

	// Use GSE to generate a new client receiver
	gseClient, err := agentreport.New(
		agentreport.WithDomainSocketPath(r.recvConfig.DomainSocketPath),
		agentreport.WithLogger(types.NewDefaultLogger(1)),
	)
	if err != nil {
		return err
	}

	// launch client, it will try to connect to agent and keep the connection.
	if err = gseClient.Launch(context.Background()); err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "GSE client failed to launch.")
	}
	// wait for a while to receive keepalive response which provides the agent info.
	time.Sleep(3 * time.Second) // nolint:mnd

	// after launch successfully, you can report data to agent.
	// the message will be report to the data-id(channel-id) which you set.
	if err = gseClient.ReportData(
		context.Background(),
		r.recvConfig.DataID,
		data,
	); err != nil {
		return gerrors.Newf(gerrors.Failure, "GSE client failed to report dataS")
	}
	return nil
}

func (r *Reporter) Close() {
	if r.quit != nil {
		close(r.quit)
	}

	if r.recvCli != nil {
		r.recvCli.Close()
		r.recvCli = nil
	}

	if r.adminCli != nil {
		r.adminCli.Close()
		r.adminCli = nil
	}

	r.wg.Wait()
	r.quit = nil
}
