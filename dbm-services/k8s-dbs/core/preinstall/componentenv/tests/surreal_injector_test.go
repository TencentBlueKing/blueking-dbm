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

func buildSurrealRequest(initEnv map[string]any) *coreentity.Request {
	return &coreentity.Request{
		Metadata: coreentity.Metadata{
			StorageAddonType: string(coreconst.Surreal),
		},
		Spec: coreentity.Spec{
			ComponentList: []coreentity.ComponentResource{
				{ComponentName: coreconst.SurrealDB, Env: initEnv},
				{ComponentName: coreconst.SurrealPd},
				{ComponentName: coreconst.SurrealTikv},
			},
		},
	}
}

func assertValidSurrealPass(t *testing.T, env map[string]any) string {
	t.Helper()
	v, ok := env[coreconst.SurrealEnvPass]
	assert.True(t, ok)
	s, ok := v.(string)
	assert.True(t, ok)
	assert.NotEmpty(t, s)
	decoded, err := base64.StdEncoding.DecodeString(s)
	assert.NoError(t, err)
	assert.Equal(t, coreconst.SurrealPassRandBytes, len(decoded))
	return s
}

func TestSurrealInjector_DefaultsWhenNoneProvided(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	req := buildSurrealRequest(nil)

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.NotNil(t, env)
	assert.Equal(t, coreconst.SurrealDefaultUser, env[coreconst.SurrealEnvUser])
	assertValidSurrealPass(t, env)
}

func TestSurrealInjector_PreserveUserProvidedUser(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	userName := "custom-user"
	req := buildSurrealRequest(map[string]any{
		coreconst.SurrealEnvUser: userName,
	})

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, userName, env[coreconst.SurrealEnvUser])
	assertValidSurrealPass(t, env)
}

func TestSurrealInjector_PreserveUserProvidedPass(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	userPass := "user-provided-pass"
	req := buildSurrealRequest(map[string]any{
		coreconst.SurrealEnvPass: userPass,
	})

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, coreconst.SurrealDefaultUser, env[coreconst.SurrealEnvUser])
	assert.Equal(t, userPass, env[coreconst.SurrealEnvPass])
}

func TestSurrealInjector_ReuseFromExistingEnv(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	existingUser := "existing-user"
	existingPass := "existing-pass"
	existingEnvByComp := map[string]map[string]any{
		coreconst.SurrealDB: {
			coreconst.SurrealEnvUser: existingUser,
			coreconst.SurrealEnvPass: existingPass,
		},
	}
	req := buildSurrealRequest(nil)

	err := injector.Inject(req, existingEnvByComp)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, existingUser, env[coreconst.SurrealEnvUser])
	assert.Equal(t, existingPass, env[coreconst.SurrealEnvPass])
}

func TestSurrealInjector_PriorityUserGtExistingGtDefault(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	userName := "user-wins-name"
	existingPass := "existing-wins-pass"

	req := buildSurrealRequest(map[string]any{
		coreconst.SurrealEnvUser: userName,
	})
	existingEnvByComp := map[string]map[string]any{
		coreconst.SurrealDB: {
			coreconst.SurrealEnvUser: "existing-should-be-ignored",
			coreconst.SurrealEnvPass: existingPass,
		},
	}

	err := injector.Inject(req, existingEnvByComp)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, userName, env[coreconst.SurrealEnvUser])
	assert.Equal(t, existingPass, env[coreconst.SurrealEnvPass])
}

func TestSurrealInjector_OnlyInjectSurrealComponent(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	req := buildSurrealRequest(nil)

	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	// surreal 组件被注入
	assert.NotNil(t, req.Spec.ComponentList[0].Env)
	assert.Contains(t, req.Spec.ComponentList[0].Env, coreconst.SurrealEnvUser)
	assert.Contains(t, req.Spec.ComponentList[0].Env, coreconst.SurrealEnvPass)
	// pd / tikv 组件不被注入
	assert.Empty(t, req.Spec.ComponentList[1].Env)
	assert.Empty(t, req.Spec.ComponentList[2].Env)
}

func TestSurrealInjector_EmptyStringTreatedAsAbsent(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	req := buildSurrealRequest(map[string]any{
		coreconst.SurrealEnvUser: "",
		coreconst.SurrealEnvPass: "",
	})
	err := injector.Inject(req, nil)
	assert.NoError(t, err)

	env := req.Spec.ComponentList[0].Env
	assert.Equal(t, coreconst.SurrealDefaultUser, env[coreconst.SurrealEnvUser])
	assertValidSurrealPass(t, env)
}

func TestSurrealInjector_NilRequest(t *testing.T) {
	injector := &envinj.SurrealEnvInjector{}
	err := injector.Inject(nil, nil)
	assert.NoError(t, err)
}
