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

package main

func startServers(cfg mockConfig, st *appStats) ([]func(), error) {
	if err := st.openDump(); err != nil {
		return nil, err
	}
	stoppers := []func(){st.closeDump}

	payload, err := defaultPayloadJSON()
	if err != nil {
		stopAll(stoppers)
		return nil, err
	}
	ctl := newAdminControl(payload)

	stopAdmin, err := startAdmin(cfg.adminAddr, st, ctl)
	if err != nil {
		stopAll(stoppers)
		return nil, err
	}
	stoppers = append(stoppers, stopAdmin)

	stopReceiver, err := startReceiver(cfg.receiverAddr, st)
	if err != nil {
		stopAll(stoppers)
		return nil, err
	}
	stoppers = append(stoppers, stopReceiver)

	stopRedis, err := startRedis(cfg.redisAddr, st)
	if err != nil {
		stopAll(stoppers)
		return nil, err
	}
	stoppers = append(stoppers, stopRedis)

	stopHTTP, err := startHTTP(cfg.httpAddr, st, ctl)
	if err != nil {
		stopAll(stoppers)
		return nil, err
	}
	stoppers = append(stoppers, stopHTTP)
	return stoppers, nil
}

func stopAll(stoppers []func()) {
	for i := len(stoppers) - 1; i >= 0; i-- {
		stoppers[i]()
	}
}
