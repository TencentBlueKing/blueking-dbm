/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package informers

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/pkg/errors"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/client-go/dynamic/dynamicinformer"
	"k8s.io/client-go/tools/cache"
)

// DoStart 启动 Informer 具体实现
func DoStart(
	ctx context.Context,
	resourceGVR schema.GroupVersionResource,
	factory dynamicinformer.DynamicSharedInformerFactory,
	handler cache.ResourceEventHandler,
	informerName string,
) error {
	slog.Info(fmt.Sprintf("Starting %s Informer...", informerName), "resource", resourceGVR.String())
	genericInformer := factory.ForResource(resourceGVR)
	informer := genericInformer.Informer()
	_, err := informer.AddEventHandler(handler)
	// 添加事件处理器
	if err != nil {
		return errors.Wrap(err, fmt.Sprintf("%s: failed to add event handler", informerName))
	}

	// 启动 informer（异步）
	go informer.Run(ctx.Done())

	// 设计缓存同步超时
	syncCtx, syncCancel := context.WithTimeout(ctx, 60*time.Second)
	defer syncCancel()

	// 等待缓存同步
	if !cache.WaitForCacheSync(syncCtx.Done(), informer.HasSynced) {
		if errors.Is(syncCtx.Err(), context.DeadlineExceeded) {
			slog.Error(fmt.Sprintf("%s cache sync timed out", informerName),
				"timeout", "60s",
				"resource", resourceGVR.String(),
			)
			return fmt.Errorf("%s: cache sync timed out after 60 seconds", informerName)
		}
		return errors.Wrap(ctx.Err(), "ClusterInformer context cancelled while waiting for cache sync")
	}

	slog.Info(fmt.Sprintf("%s Informer started and cache synced successfully", informerName),
		"resource", resourceGVR.String())

	// 健康检查 goroutine
	go func() {
		ticker := time.NewTicker(5 * time.Minute)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				if !informer.HasSynced() {
					slog.Warn(fmt.Sprintf("%s cache lost sync", informerName),
						"resource", resourceGVR.String(),
					)
				}
			case <-ctx.Done():
				return
			}
		}
	}()

	// 等待终止信号
	<-ctx.Done()
	slog.Info(fmt.Sprintf("Shutting down %s Informer...", informerName), "resource", resourceGVR.String())
	return nil
}
