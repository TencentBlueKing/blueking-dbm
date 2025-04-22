/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
// Package dbmysql
// SpiderProxyLayer file defined spider node's fail-over main logic.

package dbmysql

import (
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// SpiderProxyLayerSwitch spider node switch
type SpiderProxyLayerSwitch struct {
	SpiderCommonSwitch
	//proxy layer instance used(spider, proxy)
	AdminPort int
	//storage layer instance used
	Entry dbutil.BindEntry
	//temporary secondary node, after elect new primary, need to CHANGE MASTER TO
	SecondaryNodes []TdbctlNodes
}

// EnablePrimary connect candidate node and execute TDBCTL ENABLE PRIMARY FORCE
func (ins *SpiderProxyLayerSwitch) EnablePrimary(rawPrimaryNode *TdbctlInfo) error {
	log.Logger.Debugf("try to connect tdbctl:%s#%d", rawPrimaryNode.Host, rawPrimaryNode.Port)
	tdbctlConn, connErr := ins.ConnectInstance(rawPrimaryNode.Host, rawPrimaryNode.Port)
	if connErr != nil {
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("connect tdbctl[%s#%d] failed:%s, retry others",
			rawPrimaryNode.Host, rawPrimaryNode.Port, connErr.Error()))
		//connect failed, try another
		return connErr
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("connect tdbctl[%s#%d] success",
		rawPrimaryNode.Host, rawPrimaryNode.Port))

	if _, err := tdbctlConn.Exec(ForcePrimarySQL); err != nil {
		_ = tdbctlConn.Close()
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("tdbctl[%s#%d] do "+
			"[%s] failed:%s, try another", rawPrimaryNode.Host, rawPrimaryNode.Port, ForcePrimarySQL, err.Error()))
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "enable primary force success")
	_ = tdbctlConn.Close()

	return nil
}

func (ins *SpiderProxyLayerSwitch) ElectPrimaryCandidate() (*TdbctlInfo, error) {
	getLogFileIndex := func(logFile string) (int, error) {
		parts := strings.Split(logFile, ".")
		if len(parts) < 2 {
			return 0, fmt.Errorf("invalid log file format")
		}
		return strconv.Atoi(parts[1])
	}

	var electNode *TdbctlInfo
	var nodes map[string]TdbctlNodes
	maxRelayIndex := -1
	maxExecPos := uint64(0)
	oldPrimaryName := ""

	//found any node and get nodes info from TDBCTL_NODES
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to connect any alived tdbctl node and get nodes info"))
	for _, spider := range ins.SpiderNodes {
		//only spider-master had tdbctl node, and should connect use admin port
		if spider.Status == constvar.UNAVAILABLE ||
			spider.SpiderRole == constvar.TenDBClusterProxySlave {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("spider node[%s#%d]'s status is %s and role is %s,"+
				"skip this one", spider.IP, spider.Port, spider.Status, spider.SpiderRole))
			continue
		}

		//try to connect a tdbctl node
		log.Logger.Debugf("try to connect tdbctl:%s#%d", spider.IP, spider.AdminPort)
		currentConn, connErr := ins.ConnectInstance(spider.IP, spider.AdminPort)
		if connErr != nil {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("connect tdbctl[%s#%d] failed:%s, retry others",
				spider.IP, spider.AdminPort, connErr.Error()))
			//connect failed, try another
			continue
		}
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("connect tdbctl[%s#%d] success", spider.IP, spider.AdminPort))

		//try to get nodes info
		var err error
		nodes, err = ins.QueryNodesInfo(currentConn)
		_ = currentConn.Close()
		if err != nil {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf(" failed:%s, try others", err.Error()))
			continue
		}

		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get all nodes info from node[%s#%d] success, nodeInfo:%v",
			spider.IP, spider.AdminPort, nodes))
		break
	}

	if len(nodes) == 0 {
		return nil, fmt.Errorf("failed to retrieve any nodes information")
	}

	ins.ReportLogs(constvar.InfoResult, "try to elect an appropriate node as primary")
	for _, node := range nodes {
		//1. clusterRole must be Secondary
		//should not happen
		if strings.EqualFold(node.ClusterRole, PrimaryRole) {
			return nil, fmt.Errorf("[bug]node[%s#%d]'s clusterRole[%s] is primary, can not happen",
				node.Host, node.Port, node.ClusterRole)
		}
		if !strings.EqualFold(node.ClusterRole, SecondaryRole) {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("node[%s#%d]'s clusterRole[%s] is not secondary, skip",
				node.Host, node.Port, node.ClusterRole))
			continue
		}

		//2. ReplicationMaster couldn't be empty
		if node.ReplicationMaster == "" {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("node[%s#%d]'s replication master is empty, skip",
				node.Host, node.Port))
			continue
		}

		//3. all secondary node's REPLICATION_MASTER must be the same
		if oldPrimaryName == "" {
			oldPrimaryName = node.ReplicationMaster
		} else if node.ReplicationMaster != oldPrimaryName {
			ins.ReportLogs(constvar.FailResult, fmt.Sprintf("multi ReplicationMaster found[%s,%s]",
				node.ReplicationInfo, oldPrimaryName))
			return nil, fmt.Errorf("inconsistent ReplicationMaster among nodes")
		}

		//4. parse replication info and check whether SQL_Thread is running
		replInfo := ReplicationInfo{}
		if err := json.Unmarshal([]byte(node.ReplicationInfo), &replInfo); err != nil {
			ins.ReportLogs(constvar.WarnResult, fmt.Sprintf("get node[%s#%d]'s replication info abnormal:%s,"+
				"try other nodes", node.Host, node.Port, err.Error()))
			continue
		}
		log.Logger.Debugf("node[%s#%d]'s REPLICATION_INFO:%s",
			node.Host, node.Port, util.GraceStructString(replInfo))
		if !strings.EqualFold(replInfo.SlaveSqlRunning, "Yes") {
			ins.ReportLogs(constvar.WarnResult, fmt.Sprintf("node[%s#%d]'s sql_thread not Yes, try other nodes",
				node.Host, node.Port))
			continue
		}

		//5. check replication slow
		//compare binlog file's index first, if index the same, compare ExecMasterLogPos
		relayIndex, err := getLogFileIndex(replInfo.RelayMasterLogFile)
		if err != nil {
			ins.ReportLogs(constvar.WarnResult, fmt.Sprintf("check node[%s#%d]'s replication delay abnormal:%s",
				node.Host, node.Port, err.Error()))
			continue
		}

		//add node to array and repair new replication later
		ins.SecondaryNodes = append(ins.SecondaryNodes, node)
		execPos, _ := strconv.ParseUint(replInfo.ExecMasterLogPos, 10, 64)

		if relayIndex > maxRelayIndex ||
			(relayIndex == maxRelayIndex && execPos > maxExecPos) {
			maxRelayIndex = relayIndex
			maxExecPos, _ = strconv.ParseUint(replInfo.ExecMasterLogPos, 10, 64)
			electNode = &TdbctlInfo{
				ServerName:    node.ServerName,
				Host:          node.Host,
				Port:          node.Port,
				CurrentServer: 0,
			}
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("node[%s#%d]'s replication delay is samller,"+
				"temporary select it", node.Host, node.Port))
		}
	}

	if electNode != nil {
		return electNode, nil
	}

	return nil, fmt.Errorf("elect new tdbctl primary node failed, no satified node found")
}

// CheckSwitch check whether satisfy switch before do real switch
func (ins *SpiderProxyLayerSwitch) CheckSwitch() (bool, error) {
	return true, nil
}

// DoSwitch do spider(include tdbctl) switch
// 1. release broken-down node's name service if exist
// 2. found primary tdbctl, if primary broken-down, do elect first
// 3. remove broken-down node from primary-tdbctl route table
// 4. primary-tdbctl do flush routing
func (ins *SpiderProxyLayerSwitch) DoSwitch() error {
	var (
		primaryHost string
		primaryPort int
	)

	//1. delete name service
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("try to release ip[%s#%d] from all domain entry",
		ins.Ip, ins.Port))
	if err := ins.DeleteNameService(ins.Entry); err != nil {
		return err
	}

	//2. set all spider nodes
	if err := ins.SetSpiderNodes(); err != nil {
		return err
	}

	//2. try to get primary node
	if err := ins.GetPrimary(); err != nil {
		ins.ReportLogs(constvar.FailResult, "get primary node failed")
		return err
	}

	//3. primary node broken-down, try to elect one
	if ins.PrimaryTdbctl.CurrentServer == 1 {
		ins.ReportLogs(constvar.InfoResult, "primary node broken-down, try to elect one")

		newPrimaryNode, err := ins.ElectPrimaryCandidate()
		if err != nil {
			ins.ReportLogs(constvar.FailResult, "elect primary node failed")
			return err
		}
		if err = ins.EnablePrimary(newPrimaryNode); err != nil {
			ins.ReportLogs(constvar.FailResult, "enable primary node failed")
			return err
		}
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("enable primary node[%s#%d] success",
			newPrimaryNode.Host, newPrimaryNode.Port))

		//set new primary node
		ins.NewPrimaryTdbctl = newPrimaryNode
	}

	//4. get all route from primary node
	if ins.NewPrimaryTdbctl != nil {
		primaryHost = ins.NewPrimaryTdbctl.Host
		primaryPort = ins.NewPrimaryTdbctl.Port
	} else {
		primaryHost = ins.PrimaryTdbctl.Host
		primaryPort = ins.PrimaryTdbctl.Port
	}
	log.Logger.Debugf("try to connect to primary tdbctl")
	primaryConn, err := ins.ConnectInstance(primaryHost, primaryPort)
	if err != nil {
		return err
	}
	defer func() {
		_ = primaryConn.Close()
	}()
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get all route table from primary before switch"))
	if ins.RouteTable, err = ins.QueryRouteInfo(primaryConn); err != nil {
		_ = primaryConn.Close()
		return fmt.Errorf("get all route info failed:%s", err.Error())
	}
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("get all route table info success:%s",
		util.GraceStructString(ins.RouteTable)))

	//5. remove broken-down spider node from route table
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("remove spider node[%s#%d] from route table",
		ins.Ip, ins.Port))
	if err := ins.RemoveNodeFromRoute(primaryConn, ins.Ip, ins.Port); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("remove spider node failed:%s", err.Error()))
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "remove spider node success")

	//6. remove broken-down tdbctl node from route table
	ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("remove tdbctl node[%s#%d] from route table",
		ins.Ip, ins.AdminPort))
	if err := ins.RemoveNodeFromRoute(primaryConn, ins.Ip, ins.AdminPort); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("remove tdbctl node[%s#%d] from route-table failed:%s",
			ins.Ip, ins.AdminPort, err.Error()))
		return err
	}
	ins.ReportLogs(constvar.InfoResult, "remove tdbctl node success")

	//7. flush routing
	ins.ReportLogs(constvar.InfoResult, "flush route table")
	if _, err = primaryConn.Exec(FlushRouteForceSQL); err != nil {
		ins.ReportLogs(constvar.FailResult, fmt.Sprintf("flush route failed:%s", err.Error()))
		return fmt.Errorf("execute[%s] failed:%s", FlushRouteForceSQL, err.Error())
	}
	ins.ReportLogs(constvar.SuccessResult, "flush route success")

	return nil
}

// RollBack proxy do rollback
func (ins *SpiderProxyLayerSwitch) RollBack() error {
	return nil
}

func (ins *SpiderProxyLayerSwitch) DoFinal() error {
	if ins.PrimaryTdbctl.CurrentServer == 1 {
		//whether all lived tdbctl do change master to
		allNodeRepaired := true
		newMaster := ins.NewPrimaryTdbctl
		ins.ReportLogs(constvar.InfoResult,
			"primary broke-down and elect success, try to repair new replication")
		//1. reset slave on new primary
		ins.ReportLogs(constvar.InfoResult, "do reset slave first")
		if binlogFile, binlogPosition, err := ins.ResetSlaveExtend(newMaster.Host, newMaster.Port); err != nil {
			ins.ReportLogs(constvar.FailResult, "new primary node do reset slave failed")
			return err
		} else {
			ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("before reset slave, consistent binlog info:%s,%d",
				binlogFile, binlogPosition))
		}

		//2. do change master to on all alive tdbctl nodes
		changeSQL := fmt.Sprintf("change master to master_host='%s', master_port=%d, master_auto_position=1",
			newMaster.Host, newMaster.Port)
		ins.ReportLogs(constvar.InfoResult, fmt.Sprintf("do [%s] on all alive tdbctl nodes", changeSQL))
		for _, node := range ins.SecondaryNodes {
			if node.ServerName == ins.NewPrimaryTdbctl.ServerName {
				//skip itself, which is new elected
				continue
			}
			err := ins.ChangeMasterAuto(node.Host, node.Port, changeSQL)
			if err != nil {
				ins.ReportLogs(constvar.WarnResult, err.Error())
				allNodeRepaired = false
			}
		}
		if !allNodeRepaired {
			return fmt.Errorf("not all alived node change mastero to success")
		}
	}

	return nil
}

// ShowSwitchInstanceInfo show db-mysql instance's switch info
func (ins *SpiderProxyLayerSwitch) ShowSwitchInstanceInfo() string {
	return fmt.Sprintf("<%s#%d IDC:%d Role:%s Status:%s Bzid:%s ClusterType:%s MachineType:%s>",
		ins.Ip, ins.Port, ins.IdcID, ins.Role, ins.Status, ins.App, ins.ClusterType,
		ins.MetaType)
}
