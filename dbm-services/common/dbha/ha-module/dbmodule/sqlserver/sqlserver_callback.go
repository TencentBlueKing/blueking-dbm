/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package sqlserver

import (
	"encoding/json"
	"fmt"
	"strconv"

	"dbm-services/common/dbha/ha-module/client"
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
)

// NewSqlserverInstanceByCmDB unmarshal cmdb instances to agent detect instance struct
func NewSqlserverInstanceByCmDB(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error) {
	var (
		err          error
		unmarshalIns []*SqlserverDetectInstanceInfoFromCmDB
		ret          []dbutil.DataBaseDetect
	)
	unmarshalIns, err = UnMarshalSqlserverInstanceByCmdb(instances, constvar.SqlserverHA)

	if err != nil {
		return nil, err
	}

	for _, uIns := range unmarshalIns {
		ret = append(ret, AgentNewSqlserverDetectInstance(uIns, conf))
	}

	return ret, err
}

// DeserializeSqlserver 反序列化从Agent上报上来的故障实例
func DeserializeSqlserver(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error) {
	response := SqlserverDetectResponse{}
	err := json.Unmarshal(jsonInfo, &response)
	if err != nil {
		log.Logger.Errorf("json unmarshal failed. jsoninfo:\n%s\n, err:%s", string(jsonInfo), err.Error())
		return nil, err
	}
	ret := GMNewSqlserverDetectInstance(&response, conf)
	return ret, nil
}

// NewSqlserverSwitchInstance unmarshal cmdb instances to switch instance struct
func NewSqlserverSwitchInstance(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error) {
	var ret []dbutil.DataBaseSwitch
	for _, v := range instances {
		ins := dbutil.DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}

		// 用于切换的实例信息
		log.Logger.Debugf("sqlserver instance detail info:%#v", ins)
		swIns := SqlserverSwitch{
			BaseSwitch: dbutil.BaseSwitch{
				Ip:          ins.IP,
				Port:        ins.Port,
				IdcID:       ins.BKIdcCityID,
				Status:      ins.Status,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
				Config:      conf,
				CmDBClient:  client.NewCmDBClient(&conf.DBConf.CMDB, conf.GetCloudId()),
				HaDBClient:  client.NewHaDBClient(&conf.DBConf.HADB, conf.GetCloudId()),
			},
			Role: ins.InstanceRole,
		}
		swIns.SetStandbySlave(ins.Receiver)
		swIns.Entry = ins.BindEntry
		ret = append(ret, &swIns)
	}
	return ret, nil
}

// UnMarshalSqlserverInstanceByCmdb convert cmdb instance info to SqlserverLDetectInstanceInfoFromCmDB
func UnMarshalSqlserverInstanceByCmdb(instances []interface{},
	clusterType string) ([]*SqlserverDetectInstanceInfoFromCmDB, error) {
	var (
		ret []*SqlserverDetectInstanceInfoFromCmDB
	)
	cache := map[string]*SqlserverDetectInstanceInfoFromCmDB{}

	for _, v := range instances {
		ins := dbutil.DBInstanceInfoDetail{}
		rawData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("marshal instance info failed:%s", err.Error())
		}
		if err = json.Unmarshal(rawData, &ins); err != nil {
			return nil, fmt.Errorf("unmarshal instance info failed:%s", err.Error())
		}
		if ins.ClusterType != clusterType || (ins.Status != constvar.RUNNING && ins.Status != constvar.AVAILABLE) {
			continue
		}
		cacheIns, ok := cache[ins.IP]
		//only need detect the minimum port instance
		if !ok || ok && ins.Port < cacheIns.Port {
			cache[ins.IP] = &SqlserverDetectInstanceInfoFromCmDB{
				Ip:          ins.IP,
				Port:        ins.Port,
				App:         strconv.Itoa(ins.BKBizID),
				ClusterType: ins.ClusterType,
				MetaType:    ins.MachineType,
				Cluster:     ins.Cluster,
			}
		}
	}

	for _, cacheIns := range cache {
		ret = append(ret, cacheIns)
	}

	return ret, nil
}
