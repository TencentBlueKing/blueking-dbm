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

package tests

import (
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	envinj "k8s-dbs/core/preinstall/componentenv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestRegistry_GetInjector_Qdrant(t *testing.T) {
	injector := envinj.Registry.GetInjector(coreconst.Qdrant)
	assert.NotNil(t, injector)
	_, ok := injector.(*envinj.QdrantEnvInjector)
	assert.True(t, ok)
}

func TestRegistry_GetInjector_Unregistered(t *testing.T) {
	injector := envinj.Registry.GetInjector(coreconst.Surreal)
	assert.NotNil(t, injector)
	_, ok := injector.(*envinj.NoopEnvInjector)
	assert.True(t, ok)
}

func TestNoopEnvInjector_Inject(t *testing.T) {
	injector := &envinj.NoopEnvInjector{}
	req := &coreentity.Request{
		Spec: coreentity.Spec{
			ComponentList: []coreentity.ComponentResource{
				{ComponentName: "foo", Env: map[string]any{"KEEP": "me"}},
			},
		},
	}
	err := injector.Inject(req, nil)
	assert.NoError(t, err)
	assert.Equal(t, "me", req.Spec.ComponentList[0].Env["KEEP"])
	assert.Len(t, req.Spec.ComponentList[0].Env, 1)
}
