/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spiderctl

import (
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"regexp"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// CheckTdbctlWithSpideSchemaComp 检查spider和中控Schema是否一致
type CheckTdbctlWithSpideSchemaComp struct {
	GeneralParam *components.GeneralParam       `json:"general"`
	Params       CheckTdbctlWithSpideSchemParam `json:"extend"`
	checkTdbctlWithSpideSchemaRt
}

// CheckTdbctlWithSpideSchemParam 检查参数
type CheckTdbctlWithSpideSchemParam struct {
	Host       string `json:"host"  validate:"required,ip"`                       // 当前实例的主机地址
	Port       int    `json:"port"  validate:"required,lt=65536,gte=3306"`        // 当前实例的端口
	SpiderPort int    `json:"spider_port"  validate:"required,lt=65536,gte=3306"` // spider节点端口
}

// CheckTdbctlWithSpideSchemRt runtime
type checkTdbctlWithSpideSchemaRt struct {
	checkDbs      []string
	spiderBaseDir string
	tdbctlBaseDir string
}

// Example subcommand example input
func (c CheckTdbctlWithSpideSchemaComp) Example() interface{} {
	return CheckTdbctlWithSpideSchemaComp{
		Params: CheckTdbctlWithSpideSchemParam{
			Host:       "127.0.0.1",
			Port:       3306,
			SpiderPort: 3307,
		},
	}
}

// FrmReg table frm
var FrmReg *regexp.Regexp

// Init init runtime
func (c *CheckTdbctlWithSpideSchemaComp) Init() (err error) {
	user := c.GeneralParam.RuntimeAccountParam.MonitorUser
	pwd := c.GeneralParam.RuntimeAccountParam.MonitorPwd
	FrmReg = regexp.MustCompile(`.*frm$`)
	tdbctlConn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.Port,
		User: user,
		Pwd:  pwd,
	}.Conn()
	if err != nil {
		logger.Error("connect to tdbctl failed, err: %s", err.Error())
		return err
	}
	spiderConn, err := native.InsObject{
		Host: c.Params.Host,
		Port: c.Params.SpiderPort,
		User: user,
		Pwd:  pwd,
	}.Conn()
	if err != nil {
		logger.Error("connect to spider failed, err: %s", err.Error())
		return err
	}
	defer tdbctlConn.Close()
	defer spiderConn.Close()

	c.tdbctlBaseDir, err = tdbctlConn.GetSingleGlobalVar("datadir")
	if err != nil {
		logger.Error("get tdbctl datadir failed, err: %s", err.Error())
		return err
	}
	c.spiderBaseDir, err = spiderConn.GetSingleGlobalVar("datadir")
	if err != nil {
		logger.Error("get spider datadir failed, err: %s", err.Error())
		return err
	}
	version, err := spiderConn.SelectVersion()
	if err != nil {
		logger.Error("获取version failed %s", err.Error())
		return err
	}
	alldbs, err := spiderConn.ShowDatabases()
	if err != nil {
		logger.Error("show databases failed, err: %s", err.Error())
		return err
	}
	c.checkDbs = util.FilterOutStringSlice(alldbs, computil.GetGcsSystemDatabases(version))
	c.checkDbs = util.FilterOutStringSlice(c.checkDbs, []string{"db_infobase"})
	return nil
}

// RunCheck 检查
func (c *CheckTdbctlWithSpideSchemaComp) RunCheck() (err error) {
	spiderDbSchemaCountMap := make(map[string]int)
	tdbctlDbSchemaCountMap := make(map[string]int)
	var globalErrs []error
	for _, db := range c.checkDbs {
		dbdirSpider := path.Join(c.spiderBaseDir, db)
		dbdirTdbctl := path.Join(c.tdbctlBaseDir, db)
		logger.Info("scan path %s,%s", dbdirSpider, dbdirTdbctl)

		map1, dbdirSpiderCount, err := countFilesInDir(dbdirSpider)
		if err != nil {
			logger.Error("count files in dir %s failed, err: %s", dbdirSpider, err.Error())
		}
		map2, dbdirTdbctlCount, err := countFilesInDir(dbdirTdbctl)
		if err != nil {
			logger.Error("count files in dir %s failed, err: %s", dbdirTdbctl, err.Error())
		}
		for tb := range map1 {
			if _, exist := map2[tb]; !exist {
				msg := fmt.Sprintf("%s frm文件在 tdbctl 中不存在,请确认\n", tb)
				globalErrs = append(globalErrs, fmt.Errorf("%s", msg))
				logger.Error(msg)
			}
		}
		if dbdirSpiderCount != dbdirTdbctlCount {
			msg := fmt.Sprintf("【%s】库上的表数量不一致,【tdbctl】节点上表总数量:%d, 【spider】节点上表的总数量 count:%d\n", db, dbdirTdbctlCount,
				dbdirSpiderCount)
			globalErrs = append(globalErrs, fmt.Errorf("%s", msg))
			logger.Error(msg)
		}
		spiderDbSchemaCountMap[db] = dbdirSpiderCount
		tdbctlDbSchemaCountMap[db] = dbdirTdbctlCount
	}
	// 输出结果
	for _, db := range c.checkDbs {
		logger.Info("db:【%s】, 【tdbctl】节点上表总数量:%d, 【spider】节点上表的总数量 count:%d", db, tdbctlDbSchemaCountMap[db],
			spiderDbSchemaCountMap[db])
	}
	return errors.Join(globalErrs...)
}

// countFilesInDir 获取文件数量
func countFilesInDir(dirPath string) (map[string]struct{}, int, error) {
	count := 0
	fileMap := make(map[string]struct{})

	err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if !info.IsDir() {
			if FrmReg.MatchString(path) && info.Size() > 0 {
				fileMap[filepath.Base(path)] = struct{}{}
				count++
			}
		}

		return nil
	})

	if err != nil {
		return nil, 0, err
	}
	return fileMap, count, nil
}
