/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package spider

import (
	"fmt"
	"reflect"

	"github.com/jmoiron/sqlx"
	"github.com/mohae/deepcopy"
	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// TdbctlQueryOnRemote 在中控指定server 执行命令
// 注意执行的 sql 不能尽量不要包含 双引号，或者提前转义
// need ADMIN privileges
func TdbctlQueryOnRemote(serverName string, query string, db *sqlx.DB) (*sqlx.Rows, error) {
	sqlStr := fmt.Sprintf("TDBCTL CONNECT NODE '%s' EXECUTE \"%s\"", serverName, query)
	rows, err := db.Queryx(sqlStr)
	if err != nil {
		logger.Log.Errorf("TdbctlQueryOnRemote sql:%s", sqlStr)
	}
	return rows, err
}

func TdbctlQueryByRole(dest interface{}, wrapper string, query string, db *sqlx.DB) (map[string]interface{}, error) {
	queryServers := fmt.Sprintf("select Server_name,Host,Port,Wrapper "+
		"from mysql.servers where Wrapper='%s'", wrapper)
	var servers []*MysqlServer
	if err := db.Select(&servers, queryServers); err != nil {
		return nil, err
	}
	destRes := make(map[string]interface{}) // {spt0: result, spt1: result}
	for _, s := range servers {
		rows, err := TdbctlQueryOnRemote(s.ServerName, query, db)
		if err != nil {
			return nil, errors.Wrapf(err, "query on %s", s.ServerName)
		}
		destTmp := deepcopy.Copy(dest)
		for rows.Next() {
			if err = rows.Scan(destTmp); err != nil {
				return nil, errors.Wrapf(err, "scan result on %s", s.ServerName)
			}
		}
		destRes[s.ServerName] = destTmp
	}
	if len(destRes) != len(servers) {
		return nil, errors.Errorf("TdbctlQueryByRole result error: %v", destRes)
	}
	return destRes, nil
}

// TdbctlQueryByRoleWithMerge 中控上对某个 serverRole(Wrapper) 遍历执行一个查询语句，并合并结果返回
// dest must be a ptr
func TdbctlQueryByRoleWithMerge(dest interface{}, serverRole string, query string, db *sqlx.DB) error {
	if reflect.TypeOf(dest).Kind() != reflect.Ptr {
		return errors.New("merge result need type ptr")
	}
	destValue := reflect.ValueOf(dest)
	destDirect := reflect.Indirect(destValue)

	destResult, err := TdbctlQueryByRoleNative(dest, serverRole, query, db)
	if err != nil {
		return err
	}
	var dests []interface{} // not used currently
	for _, res := range destResult {
		resType := reflect.TypeOf(res)
		switch resType.Kind() {
		case reflect.Ptr:
			resValue := reflect.ValueOf(res)
			direct := reflect.Indirect(resValue)
			for i := 0; i < direct.Len(); i++ {
				// 将子分片的结果集，追加到 dest 中
				destDirect.Set(reflect.Append(destDirect, direct.Index(i)))
				dests = append(dests, direct.Index(i).Interface())
			}
		default:
			// unreachable code
			dests = append(dests, res)
		}
	}
	return nil
}

// TdbctlQueryByRoleNative dest is a ptr ref interface{}
// 但 dest 只用于 deepcopy 模板，生成新的 ptr->interface{}，作为 map[string]interface{} 的 value
func TdbctlQueryByRoleNative(dest interface{}, serverRole string, query string,
	db *sqlx.DB) (map[string]interface{}, error) {
	queryServers := fmt.Sprintf("select Server_name,Host,Port,Wrapper,Username,Password "+
		"from mysql.servers where Wrapper='%s'", serverRole)
	var servers []*MysqlServer
	if err := db.Select(&servers, queryServers); err != nil {
		return nil, err
	}
	destRes := make(map[string]interface{}) // {spt0: result, spt1: result}
	for _, s := range servers {
		instObj := mysqlconn.InsObject{
			Host: s.Host,
			Port: s.Port,
			User: s.Username,
			Pwd:  s.Password,
		}
		dbw, err := instObj.Conn()
		if err != nil {
			return nil, errors.Wrapf(err, "connect %s", s.ServerName)
		}
		//defer dbw.Close()
		// 因为 dest 是从最外层传进来的，主要用于scan to struct，但不能直接覆盖 dest ptr，所以使用 deepcopy
		destTmp := deepcopy.Copy(dest)
		err = dbw.Db.Select(destTmp, query)
		if err != nil {
			dbw.Close()
			return nil, errors.Wrapf(err, "query %s", s.ServerName)
		}
		dbw.Close()
		destRes[s.ServerName] = destTmp
	}
	if len(destRes) != len(servers) {
		return nil, errors.Errorf("TdbctlQueryByRole result error: %v", destRes)
	}
	return destRes, nil
}
