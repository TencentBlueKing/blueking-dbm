/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package precheck SQLServer 文件前置检查（在进入语法解析之前进行）。
//
// 插件化设计：
//   - 每个具体检查器（如 encoding、keyword、syntax 等）实现 PreChecker 接口，
//     并在自身 init() 中调用 Register 注册到全局 registry。
//   - handler 层只调用 RunAll(filePath)，无需知晓具体有哪些检查器。
//   - 新增一种检查项 = 新建一个 .go 文件 + init() 里 Register()，主代码零改动。
package precheck

import (
	"sync"

	"dbm-services/mysql/db-simulation/app/sqlserver"
)

// PreChecker 前置检查器接口。
// 每个前置检查都实现该接口，通过 Register 自注册后由 RunAll 统一编排调用。
type PreChecker interface {
	// Name 检查器名称（用于日志与去重）
	Name() string
	// Check 对单个文件执行检查；filePath 为本地磁盘上的绝对/相对路径。
	// 返回 result 描述该文件的检查结论；err 仅用于表示"检查器自身异常"（如读文件失败），
	// 而"文件不符合规范"应通过 result.Status = FileCheckFail 表达，不返回 err。
	Check(filePath string) (result sqlserver.FileCheckResult, err error)
}

// 全局检查器注册表；仅在进程启动阶段的 init() 中写入，运行期只读，无需加锁读。
var (
	registryMu sync.Mutex
	registry   []PreChecker
	registered = map[string]struct{}{} // 防重复注册
)

// Register 将一个检查器注册到全局注册表。
// 约定在具体检查器所在文件的 init() 中调用，例如：
//
//	func init() { precheck.Register(NewEncodingChecker()) }
//
// 重复注册（同名）会被忽略，保证多次 init 或测试场景下安全。
func Register(c PreChecker) {
	if c == nil {
		return
	}
	registryMu.Lock()
	defer registryMu.Unlock()
	if _, ok := registered[c.Name()]; ok {
		return
	}
	registered[c.Name()] = struct{}{}
	registry = append(registry, c)
}

// Registered 返回当前已注册的检查器名称快照（主要用于日志/自检）。
func Registered() []string {
	registryMu.Lock()
	defer registryMu.Unlock()
	names := make([]string, 0, len(registry))
	for _, c := range registry {
		names = append(names, c.Name())
	}
	return names
}

// RunAll 依次运行所有已注册的检查器；一旦某个检查器返回 fail，即短路返回该结果。
// 调用方（handler）无需感知具体有哪些检查项。
func RunAll(filePath string) (sqlserver.FileCheckResult, error) {
	// 快照拷贝，避免在极端情况下 init 后仍被并发修改
	registryMu.Lock()
	checkers := make([]PreChecker, len(registry))
	copy(checkers, registry)
	registryMu.Unlock()

	for _, c := range checkers {
		res, err := c.Check(filePath)
		if err != nil {
			return res, err
		}
		if res.Status != sqlserver.FileCheckPass {
			return res, nil
		}
	}
	return sqlserver.FileCheckResult{
		Status: sqlserver.FileCheckPass,
	}, nil
}
