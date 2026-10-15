// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"sync"
)

// RunBounded calls fn(0..n-1) in order with at most limit calls in flight and returns the first
// error. No call starts after an error; calls already started still run to completion.
func RunBounded(n, limit int, fn func(i int) error) error {
	if limit < 1 {
		limit = 1
	}
	var (
		wg       sync.WaitGroup
		mu       sync.Mutex
		firstErr error
	)
	sem := make(chan struct{}, limit)
	for i := 0; i < n; i++ {
		sem <- struct{}{}
		mu.Lock()
		failed := firstErr != nil
		mu.Unlock()
		if failed {
			<-sem
			break
		}
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			defer func() { <-sem }()
			if err := fn(i); err != nil {
				mu.Lock()
				if firstErr == nil {
					firstErr = err
				}
				mu.Unlock()
			}
		}(i)
	}
	wg.Wait()
	return firstErr
}

// runPipeline parses items ahead on pool, a slot pool shared by every port of the host, and
// applies them strictly in index order. At most lookahead items are parsed but not yet applied.
// The first parse or apply error stops it: nothing after the failed item is applied.
func runPipeline(n, lookahead int, pool chan struct{}, parse, apply func(i int) error) error {
	if n == 0 {
		return nil
	}
	if lookahead < 1 {
		lookahead = 1
	}
	results := make([]chan error, n)
	for i := range results {
		results[i] = make(chan error, 1)
	}
	tokens := make(chan struct{}, lookahead)
	stop := make(chan struct{})
	producerDone := make(chan struct{})
	var parsing sync.WaitGroup

	go func() {
		defer close(producerDone)
		for i := 0; i < n; i++ {
			select {
			case tokens <- struct{}{}:
			case <-stop:
				return
			}
			select {
			case pool <- struct{}{}:
			case <-stop:
				return
			}
			parsing.Add(1)
			go func(i int) {
				defer parsing.Done()
				defer func() { <-pool }()
				results[i] <- parse(i)
			}(i)
		}
	}()

	var err error
	for i := 0; i < n; i++ {
		if err = <-results[i]; err != nil {
			break
		}
		if err = apply(i); err != nil {
			break
		}
		<-tokens
	}
	close(stop)
	<-producerDone
	parsing.Wait()
	return err
}
