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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"

	agentreport "github.com/TencentBlueKing/bk-gse-sdk/go/service/agent-report"
	"github.com/TencentBlueKing/bk-gse-sdk/go/types"
)

// Reporter structure
type Reporter struct {
	ClientId   string
	quit       chan struct{}
	recvCli    agentreport.Client
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

// NewReporter created new reporter instance
func NewReporter(clientID string) *Reporter {
	return &Reporter{
		ClientId:   clientID,
		recvConfig: &config.Cfg.GSE,
	}
}

// CreateClients create gse client
func (r *Reporter) CreateClients(ctx context.Context) error {

	// get a new client with options
	receiver, err := agentreport.New(
		agentreport.WithDomainSocketPath(r.recvConfig.DomainSocketPath),
		agentreport.WithLogger(types.NewDefaultLogger(1)),
	)
	if err != nil {
		panic(err)
	}

	// launch client, it will try to connect to agent and keep the connection.
	if err = receiver.Launch(ctx); err != nil {
		panic(err)
	}
	// wait for a while to receive keepalive response which provides the agent info.
	time.Sleep(3 * time.Second) // nolint:mnd

	// get agent info.
	agentInfo, err := receiver.GetAgentInfo()
	if err != nil {
		panic(err)
	}

	fmt.Println("agent-id", agentInfo.AgentID)
	fmt.Println("agent cloud-id: ", agentInfo.CloudID)

	r.recvCli = receiver
	//r.adminCli = admin
	r.quit = make(chan struct{}, 1)

	r.wg.Add(1)
	go func() {
		r.keepalive()
		r.wg.Done()
	}()

	return nil
}

// PostToReceiver post data to receiver
func (r *Reporter) PostToReceiver(data []byte) error {
	if r.recvCli == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "receiver client is invalid(nil)")
	}

	err := r.recvCli.ReportData(
		context.Background(),
		r.recvConfig.DataID,
		data,
	)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidParameter, " failed to send metric")
	}
	return nil
}

// Close report function
func (r *Reporter) Close() {
	if r.quit != nil {
		close(r.quit)
	}

	// if r.recvCli != nil {
	// 	r.recvCli.Close()
	// 	r.recvCli = nil
	// }

	// if r.adminCli != nil {
	// 	r.adminCli.Close()
	// 	r.adminCli = nil
	// }

	r.wg.Wait()
	r.quit = nil
}
