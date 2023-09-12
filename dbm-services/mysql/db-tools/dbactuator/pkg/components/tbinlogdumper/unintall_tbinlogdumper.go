/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package tbinlogdumper

import (
	"fmt"
	"path"
	"strconv"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

// UnInstallTbinlogDumperComp TODO
// tbinlogdumper本质上是mysqld进程，可以继承一些方法
type UnInstallTbinlogDumperComp struct {
	mysql.UnInstallMySQLComp
}

// TbinlogDumperClearDir 删除特定的实例目录
func (u *UnInstallTbinlogDumperComp) TbinlogDumperClearDir() error {
	for _, port := range u.Params.Ports {
		var (
			dataBak  = cst.DumperDefaultBakDir
			dataPath = path.Join(
				cst.DumperDefaultDir,
				cst.DefaultMysqlDataBasePath,
				strconv.Itoa(port),
			) //  "/data/idip_cache/mysqldata/{port}"
			dataLog = path.Join(
				cst.DumperDefaultDir,
				cst.DefaultMysqlLogBasePath,
				strconv.Itoa(port),
			) //  "/data/idip_cache/mysqllog/{port}"
			//  "/data/idip_cache/dbbak/"
			suffix     = fmt.Sprintf("_bak_%s", time.Now().Format(cst.TIMELAYOUTSEQ))
			dataLogBak = path.Join(
				dataBak,
				fmt.Sprintf("%s_%d%s", cst.DefaultMysqlLogBasePath, port, suffix),
			)
		)
		if !cmutil.FileExists(dataBak) {
			cmd := fmt.Sprintf("mkdir %s;", dataBak)
			output, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", cmd, err, output)
				return err
			}
		}

		if cmutil.FileExists(dataLog) {
			cmd := fmt.Sprintf("mv %s %s;", dataLog, dataLogBak)
			logger.Info("backup command [%s]", cmd)
			output, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", cmd, err, output)
				return err
			}
		}

		if cmutil.FileExists(dataPath) {
			cmd := fmt.Sprintf(
				"mv %s %s_%d%s;",
				dataPath,
				path.Join(dataBak, cst.DefaultMysqlDataBasePath),
				port,
				suffix,
			)
			logger.Info("backup command [%s]", cmd)
			output, err := osutil.ExecShellCommand(false, cmd)
			if err != nil {
				err = fmt.Errorf("execute [%s] get an error:%w,output:%s", cmd, err, output)
				return err
			}
		}
	}
	return nil
}
