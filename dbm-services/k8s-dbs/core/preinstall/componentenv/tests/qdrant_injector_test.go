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
	"encoding/base64"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	envinj "k8s-dbs/core/preinstall/componentenv"
	"testing"

	"github.com/stretchr/testify/assert"
)

func buildQdrantRequest(initEnv map[string]any) *coreentity.Request {
	return &coreentity.Request{
		Metadata: coreentity.Metadata{
			StorageAddonType: string(coreconst.Qdrant),
		},
		Spec: coreentity.Spec{
			ComponentList: []coreentity.ComponentResource{
				{ComponentName: "qdrant", Env: initEnv},
			},
		},
	}
}

func assertValidQdrantKey(t *testing.T, env map[string]any, key string) string {
	t.Helper()
	v, ok := env[key]
	assert.True(t, ok)
	s, ok := v.(string)
	assert.True(t, ok)
	assert.NotEmpty(t, s)
	decoded, err := base64.StdEncoding.DecodeString(s)
	assert.NoError(t, err)
	assert.Equal(t, coreconst.QdrantAPIKeyRandBytes, len(decoded))
	return s
}

func TestQdrantInjector_InjectBothWhenNoneProvided(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	req := buildQdrantRequest(nil)

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.NotNil(t, env)
	k1 := assertValidQdrantKey(t, env, coreconst.QdrantEnvAPIKey)
	k2 := assertValidQdrantKey(t, env, coreconst.QdrantEnvReadOnlyAPIKey)
	assert.NotEqual(t, k1, k2)
}

func TestQdrantInjector_PreserveUserProvided(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	userKey := "user-provided-api-key"
	req := buildQdrantRequest(map[string]any{
		coreconst.QdrantEnvAPIKey: userKey,
	})

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, userKey, env[coreconst.QdrantEnvAPIKey])
	assertValidQdrantKey(t, env, coreconst.QdrantEnvReadOnlyAPIKey)
}

func TestQdrantInjector_ReuseFromExistingEnv(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	existingAPIKey := "existing-api-key-from-cluster-cr"
	existingReadOnlyKey := "existing-read-only-key"
	existingEnvByComp := map[string]map[string]any{
		"qdrant": {
			coreconst.QdrantEnvAPIKey:         existingAPIKey,
			coreconst.QdrantEnvReadOnlyAPIKey: existingReadOnlyKey,
		},
	}
	req := buildQdrantRequest(nil)

	err := injector.Inject(req, existingEnvByComp)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, existingAPIKey, env[coreconst.QdrantEnvAPIKey])
	assert.Equal(t, existingReadOnlyKey, env[coreconst.QdrantEnvReadOnlyAPIKey])
}

func TestQdrantInjector_PriorityUserGtExistingGtGenerated(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	userAPIKey := "user-wins"
	existingReadOnlyKey := "existing-ro-wins-over-generated"

	req := buildQdrantRequest(map[string]any{
		coreconst.QdrantEnvAPIKey: userAPIKey,
	})
	existingEnvByComp := map[string]map[string]any{
		"qdrant": {
			coreconst.QdrantEnvAPIKey:         "existing-should-be-ignored",
			coreconst.QdrantEnvReadOnlyAPIKey: existingReadOnlyKey,
		},
	}

	err := injector.Inject(req, existingEnvByComp)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, userAPIKey, env[coreconst.QdrantEnvAPIKey])
	assert.Equal(t, existingReadOnlyKey, env[coreconst.QdrantEnvReadOnlyAPIKey])
}

func TestQdrantInjector_NilEnvInitialized(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	req := &coreentity.Request{
		Spec: coreentity.Spec{
			ComponentList: []coreentity.ComponentResource{
				{ComponentName: "qdrant"},
			},
		},
	}
	err := injector.Inject(req, nil)
	assert.NoError(t, err)
	assert.NotNil(t, req.Spec.ComponentList[0].Env)
	assertValidQdrantKey(t, req.Spec.ComponentList[0].Env, coreconst.QdrantEnvAPIKey)
	assertValidQdrantKey(t, req.Spec.ComponentList[0].Env, coreconst.QdrantEnvReadOnlyAPIKey)
}

func TestQdrantInjector_EmptyStringTreatedAsAbsent(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	req := buildQdrantRequest(map[string]any{
		coreconst.QdrantEnvAPIKey: "",
	})
	err := injector.Inject(req, nil)
	assert.NoError(t, err)
	assertValidQdrantKey(t, req.Spec.ComponentList[0].Env, coreconst.QdrantEnvAPIKey)
}

func TestQdrantInjector_NilRequest(t *testing.T) {
	injector := &envinj.QdrantEnvInjector{}
	err := injector.Inject(nil, nil)
	assert.NoError(t, err)
}
