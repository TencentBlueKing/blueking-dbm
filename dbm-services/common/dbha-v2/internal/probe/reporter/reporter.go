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
)

type Reporter struct {
	ClientId string
	recvCli  *client.ReceiverClient
	adminCli *client.AdminClient
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

	return nil
}

func (r *Reporter) PostToReceiver(data []byte) error {
	if r.recvCli == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "receiver client is invalid(nil)")
	}

	return r.recvCli.SendMessage(data)
}

func (r *Reporter) PostToAdmin() error {
	if r.adminCli == nil {
		return gerrors.Newf(gerrors.InvalidParameter, "admin client is invalid(nil)")
	}

	return nil
}

func (r *Reporter) Close() {
	if r.recvCli != nil {
		r.recvCli.Close()
		r.recvCli = nil
	}

	if r.adminCli != nil {
		r.adminCli.Close()
		r.adminCli = nil
	}
}
