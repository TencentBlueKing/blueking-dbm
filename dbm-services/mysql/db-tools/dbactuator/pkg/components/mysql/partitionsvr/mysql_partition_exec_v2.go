/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package partitionsvr

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"fmt"
)

// PartitionExecComp 分区执行组件
type PartitionExecComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *PartitionExecParam      `json:"extend"`
	PartitionRuntimeCtx
}

// PartitionExecParam 分区执行参数
type PartitionExecParam struct {
	Cluster      Cluster            `json:"cluster"`
	Configs      []*PartitionConfig `json:"configs"`
	Force        bool               `json:"force"`
	PartialForce bool               `json:"partial_force"`
	ErrorLogs    []error
}

// PartitionConfig 分区配置
type PartitionConfig struct {
	ConfigID              int64  `json:"config_id"`
	DbLike                string `json:"dblike"`
	TbLike                string `json:"tblike"`
	PartitionColumn       string `json:"partition_column"`
	PartitionColumnType   string `json:"partition_column_type"`
	ExpireTime            int    `json:"expire_time"`
	PartitionTimeInterval int    `json:"partition_time_interval"`
	PartitionType         int    `json:"partition_type"`
	TimeZone              string `json:"time_zone"`
	Phase                 string `json:"phase"`
	ExtraPartition        int    `json:"extra_partition"`
	ReservedPartition     int
}

type ForceInitInfo struct {
	Force bool
	User  string
	Pwd   string
	Host  string
	Port  int
}

type PartitionRuntimeCtx struct {
	Conn *native.DbWorker
}

// Example
func (c *PartitionExecComp) Example() (err error) {

	return
}

func (c *PartitionExecComp) TmpTest() (err error) {

	FakeReport()

	return nil
}

// Init 分区任务初始化参数 配置
func (c *PartitionExecComp) Init() (err error) {
	conn, err := native.InsObject{
		Host: c.Params.Cluster.IP,
		Port: c.Params.Cluster.Port,
		User: c.GeneralParam.RuntimeAccountParam.PartitionYwUser,
		Pwd:  c.GeneralParam.RuntimeAccountParam.PartitionYwPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", c.Params.Cluster.Port, err.Error())
		return err
	}
	c.Conn = conn

	// MysqlTest(conn)

	return nil
}

func (c *PartitionExecComp) ExecutePartition() (err error) {
	// 确保连接在使用完成后关闭
	defer func() {
		if c.Conn != nil {
			c.Conn.Close()
		}
	}()

	// 获取目标db基本信息 真实库表名，是否是分区表
	//c.GetAllDbTbRealName()
	// 此处开始区分集群类型
	switch c.Params.Cluster.ClusterType {
	case cst.TendbCluster:
		err = c.TendbClusterPartition()
	default:
		err = c.TendbPartition()
	}

	if err != nil {
		return err
	}
	return nil
}

func MysqlTest(conn *native.DbWorker) {
	sql := "select id as ID,name as Name from partition_v2_test_02.tb1_hasuniquekey"
	rows, err := conn.Query(sql)
	if err != nil {
		fmt.Printf("这是mysql测试函数，当前执行报错：%s \n", err.Error())
		return
	}
	fmt.Printf("%+v\n", rows)

	for _, row := range rows {
		v, ok := row["Name"]
		if !ok {
			fmt.Println("it's not ok!")
		}
		fmt.Println(v)
	}

}
