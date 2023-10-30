/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package components

import (
	"encoding/json"
	"fmt"
)

// WrapperOutputString TODO
func WrapperOutputString(output string) string {
	return fmt.Sprintf(`<ctx>%s</ctx>`, output)
}

// WrapperOutput TODO
func WrapperOutput(v interface{}) (string, error) {
	if b, e := json.Marshal(v); e != nil {
		return "<ctx></ctx>", e
	} else {
		return fmt.Sprintf(`<ctx>%s</ctx>`, string(b)), nil
	}
}

// PrintOutputCtx TODO
func PrintOutputCtx(v interface{}) error {
	if ss, err := WrapperOutput(v); err != nil {
		return err
	} else {
		fmt.Println(ss)
	}
	return nil
}
