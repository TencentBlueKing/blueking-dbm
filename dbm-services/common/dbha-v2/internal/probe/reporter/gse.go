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
	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	agentreport "github.com/TencentBlueKing/bk-gse-sdk/go/service/agent-report"
	"github.com/TencentBlueKing/bk-gse-sdk/go/types"
)

var NameGSE = "GSE"

type gse struct {
	cfg      config.ReporterConfig
	agentCli agentreport.Client
}

// NewGSEClient new GSE client
func NewGSEClient(cfg config.ReporterConfig, logger types.Logger) (Reporter, error) {
	cli, err := agentreport.New(
		agentreport.WithDomainSocketPath(cfg.Endpoint),
		agentreport.WithLogger(logger),
	)

	if err != nil {
		logger.Error("do not create gse agent, endpoint(%s), %v", cfg.Endpoint, err)
		return nil, gerrors.Newf(gerrors.ComponentFailure, "create agent client failed, %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), cfg.ConnTimeout)
	defer cancel()

	if err = cli.Launch(ctx); err != nil {
		logger.Error("do not connect with agent, endpoint(%s), connection timeout(%v), %v", cfg.Endpoint,
			cfg.ConnTimeout, err)

		return nil, gerrors.Newf(gerrors.ComponentFailure, "do not connect with agent, %v", err)
	}
	g := &gse{
		cfg:      cfg,
		agentCli: cli,
	}

	return g, nil
}

// Name return reporter's name
func (g *gse) Name() string {
	return NameGSE
}

// Post post the content to server by GSE
func (g *gse) Post(ctx context.Context, content []byte) error {
	ctxTimeout, cancel := context.WithTimeout(ctx, g.cfg.ConnTimeout)
	defer cancel()

	if err := g.agentCli.ReportData(ctxTimeout, uint32(g.cfg.DataID), content); err != nil {
		return gerrors.Newf(gerrors.ComponentFailure, "report data to agent failed, dataID(%d), %v", g.cfg.DataID, err)
	}

	return nil
}

func (g *gse) Close() {
	if err := g.agentCli.Terminate(context.Background()); err != nil {
		logger.Error("terminate the connection with gse agent failed, %v", err)
	}
	logger.Info("Terminate the connection with GSE agent successfully")
}
