/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package api

import (
	"encoding/json"

	"github.com/pkg/errors"
)

// ScheduleChange TODO
func (m *Manager) ScheduleChange(name, schedule string, permanent bool) (int, error) {
	body := struct {
		Name      string `json:"name"`
		Schedule  string `json:"schedule"`
		Permanent bool   `json:"permanent"`
	}{
		Name:      name,
		Schedule:  schedule,
		Permanent: permanent,
	}

	resp, err := m.do("/schedule/change", "POST", body)
	if err != nil {
		return 0, errors.Wrap(err, "manager call /schedule/change")
	}

	res := struct {
		EntryId int `json:"entry_id"`
	}{}
	err = json.Unmarshal(resp, &res)
	if err != nil {
		return 0, errors.Wrap(err, "manager unmarshal /schedule/change response")
	}

	return res.EntryId, nil
}
