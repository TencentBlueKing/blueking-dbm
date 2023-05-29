package myredis

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbmon/mylog"
	"dbm-services/redis/db-tools/dbmon/pkg/consts"
)

// CmdClusterInfo 命令:cluster info的结果
type CmdClusterInfo struct {
	ClusterState                       string `json:"cluster_state"`
	ClusterSlotsAssigned               int    `json:"cluster_slots_assigned"`
	ClusterSlotsOk                     int    `json:"cluster_slots_ok"`
	ClusterSlotsPfail                  int    `json:"cluster_slots_pfail"`
	ClusterSlotsFail                   int    `json:"cluster_slots_fail"`
	ClusterKnownNodes                  int    `json:"cluster_known_nodes"`
	ClusterSize                        int    `json:"cluster_size"`
	ClusterCurrentEpoch                int    `json:"cluster_current_epoch"`
	ClusterMyEpoch                     int    `json:"cluster_my_epoch"`
	ClusterStatsMessagesPingSent       uint64 `json:"cluster_stats_messages_ping_sent"`
	ClusterStatsMessagesPongSent       uint64 `json:"cluster_stats_messages_pong_sent"`
	ClusterStatsMessagesMeetSent       uint64 `json:"cluster_stats_messages_meet_sent"`
	ClusterStatsMessagesPublishSent    uint64 `json:"cluster_stats_messages_publish_sent"`
	ClusterStatsMessagesUpdateSent     uint64 `json:"cluster_stats_messages_update_sent"`
	ClusterStatsMessagesSent           uint64 `json:"cluster_stats_messages_sent"`
	ClusterStatsMessagesPingReceived   uint64 `json:"cluster_stats_messages_ping_received"`
	ClusterStatsMessagesPongReceived   uint64 `json:"cluster_stats_messages_pong_received"`
	ClusterStatsMessagesMeetReceived   uint64 `json:"cluster_stats_messages_meet_received"`
	ClusterStatsMessagesUpdateReceived uint64 `json:"cluster_stats_messages_update_received"`
	ClusterStatsMessagesReceived       uint64 `json:"cluster_stats_messages_received"`
}

// DecodeClusterInfo 解析cluster info命令结果
func DecodeClusterInfo(cmdRet string) (clusterInfo *CmdClusterInfo) {
	clusterInfo = &CmdClusterInfo{}
	list01 := strings.Split(cmdRet, "\n")
	for _, item01 := range list01 {
		item01 = strings.TrimSpace(item01)
		if len(item01) == 0 {
			continue
		}
		list02 := strings.SplitN(item01, ":", 2)
		if len(list02) < 2 {
			continue
		}
		if list02[0] == "cluster_state" {
			clusterInfo.ClusterState = list02[1]
		} else if list02[0] == "cluster_slots_assigend" {
			clusterInfo.ClusterSlotsAssigned, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_slots_ok" {
			clusterInfo.ClusterSlotsOk, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_slots_pfail" {
			clusterInfo.ClusterSlotsPfail, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_known_nodes" {
			clusterInfo.ClusterKnownNodes, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_size" {
			clusterInfo.ClusterSize, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_current_epoch" {
			clusterInfo.ClusterCurrentEpoch, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_my_epoch" {
			clusterInfo.ClusterMyEpoch, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "cluster_stats_messages_ping_sent" {
			clusterInfo.ClusterStatsMessagesPingSent, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_pong_sent" {
			clusterInfo.ClusterStatsMessagesPongSent, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_meet_sent" {
			clusterInfo.ClusterStatsMessagesMeetSent, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_sent" {
			clusterInfo.ClusterStatsMessagesSent, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_ping_received" {
			clusterInfo.ClusterStatsMessagesPingReceived, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_pong_received" {
			clusterInfo.ClusterStatsMessagesPongReceived, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_meet_received" {
			clusterInfo.ClusterStatsMessagesMeetReceived, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_update_received" {
			clusterInfo.ClusterStatsMessagesUpdateReceived, _ = strconv.ParseUint(list02[1], 10, 64)
		} else if list02[0] == "cluster_stats_messages_received" {
			clusterInfo.ClusterStatsMessagesReceived, _ = strconv.ParseUint(list02[1], 10, 64)
		}
	}
	return
}

// ClusterInfo 获取cluster info结果并解析
func (db *RedisClient) ClusterInfo() (clusterInfo *CmdClusterInfo, err error) {
	var ret01 string
	if db.DbType == consts.TendisTypeRedisCluster {
		ret01, err = db.ClusterClient.ClusterInfo(context.TODO()).Result()
	} else {
		ret01, err = db.InstanceClient.ClusterInfo(context.TODO()).Result()
	}
	if err != nil {
		err = fmt.Errorf("ClusterInfo execute cluster info fail,err:%v,clusterAddr:%s", err, db.Addr)
		mylog.Logger.Error(err.Error())
		return nil, err
	}
	clusterInfo = DecodeClusterInfo(ret01)
	return clusterInfo, nil
}
