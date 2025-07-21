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

package probe

import (
	"dbm-services/common/dbha-v2/internal/receiver/output"
	"dbm-services/common/dbha-v2/internal/receiver/output/storage"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/proto"
	"sync"
)

type requestEventC chan *proto.ReceiverRequest

// connectionHandler service connection handler
type connectionHandler struct {
	savers []output.Outputter
	eventC requestEventC
	quit   chan struct{}
	wg     sync.WaitGroup
}

func (c *connectionHandler) readEvent() {
	for {
		select {
		case <-c.quit:
			return

		case msg := <-c.eventC:
			if len(c.savers) == 0 {
				logger.Debug("no connection handler, drop the data(%v)", msg)
				continue
			}

			for _, saver := range c.savers {
				saver.Save(&storage.Message{
					Topic: "",
					Data:  string(msg.Payload),
				})
			}
		}
	}
}

func (c *connectionHandler) postEvent(event *proto.ReceiverRequest) error {
	select {
	case c.eventC <- event:
		return nil

	default:
		return gerrors.Newf(gerrors.QueueFull, "connection queue is full")
	}
}

func (c *connectionHandler) run() {
	if c.eventC == nil {
		c.eventC = make(chan *proto.ReceiverRequest, constant.DefaultReceiverBufferSize)
	}

	if c.quit == nil {
		c.quit = make(chan struct{}, 1)
	}

	c.wg.Add(1)
	go func() {
		c.readEvent()
		c.wg.Done()
	}()
}

func (c *connectionHandler) close() {
	if c.quit != nil {
		close(c.quit)
	}

	if c.eventC != nil {
		close(c.eventC)
	}

	c.wg.Wait()
	c.quit = nil
	c.eventC = nil
}
