/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysql

import (
	"errors"
	"fmt"
	"path"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
)

var installTokudbSQL = `
set sql_log_bin=off;use mysql;
INSERT INTO plugin (name,dl) VALUES ('tokudb','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_trx','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_locks','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_lock_waits','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_file_map','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_fractal_tree_info','ha_tokudb.so');
INSERT INTO plugin (name,dl) VALUES ('tokudb_fractal_tree_block_map','ha_tokudb.so');`

// EnableTokudbEngineComp TODO
type EnableTokudbEngineComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       EnableTokudbParams
	enabledTokudbCtx
}

type enabledTokudbCtx struct {
	conns           map[Port]*native.DbWorker
	sockeMap        map[Port]string
	serializeCnfMap map[Port]*util.CnfFile
}

// EnableTokudbParams TODO
type EnableTokudbParams struct {
	Host  string `json:"host" validate:"required,ip" `
	Ports []int  `json:"ports" validate:"required,gt=0,dive"`
}

// CloseConn TODO
func (t *EnableTokudbEngineComp) CloseConn() (err error) {
	for _, v := range t.conns {
		v.Db.Close()
	}
	return nil
}

// Example subcommand example input
func (t *EnableTokudbEngineComp) Example() interface{} {
	return &EnableTokudbEngineComp{
		Params: EnableTokudbParams{
			Host:  "127.0.0.1",
			Ports: []int{3306, 3307},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.MySQLAdminReplExample,
			},
		},
	}
}

// Init prepare run env
func (t *EnableTokudbEngineComp) Init() (err error) {
	t.conns = make(map[Port]*native.DbWorker)
	t.sockeMap = make(map[Port]string)
	t.serializeCnfMap = make(map[Port]*util.CnfFile)
	for _, port := range t.Params.Ports {
		conn, err := native.InsObject{
			Host: t.Params.Host,
			Port: port,
			User: t.GeneralParam.RuntimeAccountParam.AdminUser,
			Pwd:  t.GeneralParam.RuntimeAccountParam.AdminPwd,
		}.Conn()
		if err != nil {
			logger.Error("conn err:%v", err)
			return err
		}
		ver, err := conn.SelectVersion()
		if err != nil {
			logger.Error("select version err:%v", err)
			return err
		}
		// version check
		if mysqlutil.GetMajorVersion(cmutil.MySQLVersionParse(ver)) != "5.6" {
			return errors.New("tokudb engine only support mysql 5.6  vesion")
		}
		// my.cnf  exist check
		mycnfFile := util.GetMyCnfFileName(port)
		if !cmutil.FileExists(mycnfFile) {
			logger.Error("mycnf file not exist:%v", mycnfFile)
			return errors.New("mycnf file not exist")
		}
		cnf, err := util.LoadMyCnfForFile(mycnfFile)
		if err != nil {
			logger.Error("load mycnf err:%v", err)
			return err
		}
		// get socket path
		socket, err := cnf.GetMySQLSocket()
		if err != nil {
			logger.Error("get mysql socket err:%v", err)
			return err
		}
		t.sockeMap[port] = socket
		t.conns[port] = conn
		t.serializeCnfMap[port] = cnf
	}
	return t.disableHugePage()
}

func (t *EnableTokudbEngineComp) disableHugePage() (err error) {
	logger.Info("doing disable huge page ...")
	output, err := osutil.StandardShellCommand(false, "echo never > /sys/kernel/mm/transparent_hugepage/enabled")
	if err != nil {
		logger.Error("Failed to set transparent hugepage to never: %v,output:%s", err, output)
		return err
	}
	logger.Info("set transparent hugepage to never success")
	return nil
}

// ReWriteMyCnf 重新定义tokudb配置
func (t *EnableTokudbEngineComp) ReWriteMyCnf() (err error) {
	for _, port := range t.Params.Ports {
		cfg := t.serializeCnfMap[port]
		bpSize, err := cfg.GetMysqldKeyVaule("innodb_buffer_pool_size")
		if err != nil {
			logger.Error("get mysql innodb_buffer_pool_size err:%v", err)
			return err
		}
		result := regexp.MustCompile(`(^\d+)(m|M|g|G)`).FindStringSubmatch(bpSize)
		if len(result) != 3 {
			return fmt.Errorf("can not find digit in %s", bpSize)
		}
		size, err := strconv.Atoi(result[1])
		if err != nil {
			logger.Error("convert string to int err:%v", err)
			return err
		}
		tokudb_cache_size := fmt.Sprintf("%d%s", size/2, result[2])
		datadir, err := cfg.GetMySQLDataDir()
		if err != nil {
			logger.Error("get mysql datadir from my.cnf err:%v", err)
			return err
		}
		tokuBasedir := path.Join(datadir, "tokudb")
		tokuDatadir := path.Join(tokuBasedir, "data")
		tokuLogdir := path.Join(tokuBasedir, "log")
		tokuTmpdir := path.Join(tokuBasedir, "tmp")
		// init tokudb dir
		logger.Info("init tokudb dir:%s", tokuBasedir)
		stderr, err := osutil.StandardShellCommand(false, fmt.Sprintf("mkdir -p %s &&  chown -R mysql %s ",
			strings.Join([]string{tokuDatadir,
				tokuLogdir, tokuTmpdir}, " "),
			tokuBasedir))
		if err != nil {
			logger.Error("create dir err:%v,std err:%s", err, stderr)
			return err
		}
		cfg.Cfg.Section("mysqld").Key("tokudb_cache_size").SetValue(tokudb_cache_size)
		cfg.Cfg.Section("mysqld").Key("tokudb_data_dir").SetValue(tokuDatadir)
		cfg.Cfg.Section("mysqld").Key("tokudb_log_dir").SetValue(tokuLogdir)
		cfg.Cfg.Section("mysqld").Key("tokudb_tmp_dir").SetValue(tokuTmpdir)
		cfg.Cfg.Section("mysqld").Key("tokudb_commit_sync").SetValue("0")
		cfg.Cfg.Section("mysqld").Key("tokudb_fsync_log_period").SetValue("1000")
		cfg.Cfg.Section("mysqld").Key("tokudb_lock_timeout").SetValue("50000")
		cfg.Cfg.Section("mysqld").Key("tokudb_fs_reserve_percent").SetValue("0")
		cfg.ReplaceValue("mysqld", "innodb_buffer_pool_size", false, "200M")
		cfg.ReplaceValue("mysqld", "default_storage_engine", false, "Tokudb")
		// save configuration file
		if err = cfg.SafeSaveFile(false); err != nil {
			logger.Error("save mysql config err:%v", err)
			return err
		}
	}
	return err
}

// Install :install
func (t *EnableTokudbEngineComp) Install() (err error) {
	wg := sync.WaitGroup{}
	mu := sync.Mutex{}
	var errs []error
	for _, port := range t.Params.Ports {
		conn, ok := t.conns[port]
		if !ok {
			return fmt.Errorf("port %d: conn is nil", port)
		}
		conn.Exec(installTokudbSQL)
		wg.Add(1)
		go func(port int) {
			defer wg.Done()
			err := computil.RestartMysqlInstanceNormal(native.InsObject{
				Host:   t.Params.Host,
				Port:   port,
				User:   t.GeneralParam.RuntimeAccountParam.AdminUser,
				Pwd:    t.GeneralParam.RuntimeAccountParam.AdminPwd,
				Socket: t.sockeMap[port],
			})
			if err != nil {
				logger.Error("restart mysql %d instance err:%v", port, err)
				mu.Lock()
				errs = append(errs, fmt.Errorf("retsart %d failde:%w", port, err))
				mu.Unlock()
			}
		}(port)
	}
	wg.Wait()
	return errors.Join(errs...)
}
