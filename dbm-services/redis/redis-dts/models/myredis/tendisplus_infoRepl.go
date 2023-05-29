package myredis

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// InfoReplSlave Tendisplus master中执行info replication结果中slave状态
// 如: slave0:ip=luketest03-redis-rdsplus4-1.luketest03-svc.dmc,port=30000,state=online,offset=930327677,lag=0
type InfoReplSlave struct {
	Name   string `json:"name"`
	IP     string `json:"ip"`
	Port   int    `json:"port"`
	State  string `json:"state"`
	Offset int64  `json:"offset"`
	Lag    int64  `json:"lag"`
}

func (slave *InfoReplSlave) decode(line string) error {
	line = strings.TrimSpace(line)
	list01 := strings.Split(line, ":")
	if len(list01) < 2 {
		return fmt.Errorf(`%s format not correct,
		the correct format is as follows:slave0:ip=xx,port=48000,state=online,offset=2510,lag=0`, line)
	}
	slave.Name = list01[0]
	list02 := strings.Split(list01[1], ",")
	for _, item01 := range list02 {
		list02 := strings.Split(item01, "=")
		if list02[0] == "ip" {
			slave.IP = list02[1]
		} else if list02[0] == "port" {
			slave.Port, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "state" {
			slave.State = list02[1]
		} else if list02[0] == "offset" {
			slave.Offset, _ = strconv.ParseInt(list02[1], 10, 64)
		} else if list02[0] == "lag" {
			slave.Lag, _ = strconv.ParseInt(list02[1], 10, 64)
		}
	}
	return nil
}

// InfoReplRocksdb ..
type InfoReplRocksdb struct {
	Name      string `json:"name"`
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	State     string `json:"state"`
	BinlogPos int64  `json:"binlog_pos"`
	Lag       int64  `json:"lag"`
}

// InfoReplRocksdbSlave 在tendisplus master上执行info replication结果中rocksdb<num>_slave0解析
// 如: rocksdb0_slave0:ip=127.0.0.1,port=48000,dest_store_id=0,state=online,binlog_pos=249,lag=0,binlog_lag=0
type InfoReplRocksdbSlave struct {
	InfoReplRocksdb
	DestStoreID int   `json:"dest_store_id"`
	BinlogLag   int64 `json:"binlog_lag"`
}

func (slave *InfoReplRocksdbSlave) decode(line string) error {
	line = strings.TrimSpace(line)
	var err error
	list01 := strings.Split(line, ":")
	if len(list01) < 2 {
		err = fmt.Errorf(`%s format not correct,
		the correct format is as follows:
		rocksdb0_slave0:ip=xx,port=xx,dest_store_id=0,state=online,binlog_pos=249,lag=0,binlog_lag=0`, line)
		return err
	}
	slave.Name = list01[0]

	list02 := strings.Split(list01[1], ",")
	for _, item01 := range list02 {
		list02 := strings.Split(item01, "=")
		if list02[0] == "ip" {
			slave.IP = list02[1]
		} else if list02[0] == "port" {
			slave.Port, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "dest_store_id" {
			slave.DestStoreID, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "state" {
			slave.State = list02[1]
		} else if list02[0] == "binlog_pos" {
			slave.BinlogPos, _ = strconv.ParseInt(list02[1], 10, 64)
		} else if list02[0] == "lag" {
			slave.Lag, _ = strconv.ParseInt(list02[1], 10, 64)
		} else if list02[0] == "binlog_lag" {
			slave.BinlogLag, _ = strconv.ParseInt(list02[1], 10, 64)
		}
	}
	return nil
}

// InfoReplRocksdbMaster 在tendisplus slave上执行info replication结果中rocksdb<num>_master解析
// 如: rocksdb0_master:ip=127.0.0.1,port=47000,src_store_id=0,state=online,binlog_pos=249,lag=0
type InfoReplRocksdbMaster struct {
	InfoReplRocksdb
	SrcStoreID int `json:"src_store_id"`
}

func (master *InfoReplRocksdbMaster) decode(line string) error {
	line = strings.TrimSpace(line)
	list01 := strings.Split(line, ":")
	var err error
	if len(list01) < 2 {
		err = fmt.Errorf(`%s format not correct,
		the correct format is as follows: 
		rocksdb0_master:ip=xxxx,port=47000,src_store_id=0,state=online,binlog_pos=249,lag=0`, line)
		return err
	}
	master.Name = list01[0]

	list02 := strings.Split(list01[1], ",")
	for _, item01 := range list02 {
		list02 := strings.Split(item01, "=")
		if list02[0] == "ip" {
			master.IP = list02[1]
		} else if list02[0] == "port" {
			master.Port, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "src_store_id" {
			master.SrcStoreID, _ = strconv.Atoi(list02[1])
		} else if list02[0] == "state" {
			master.State = list02[1]
		} else if list02[0] == "binlog_pos" {
			master.BinlogPos, _ = strconv.ParseInt(list02[1], 10, 64)
		} else if list02[0] == "lag" {
			master.Lag, _ = strconv.ParseInt(list02[1], 10, 64)
		}
	}
	return nil
}

// TendisplusInfoReplData tendisplus info replication命令结果解析
type TendisplusInfoReplData struct {
	Addr                   string                  `json:"addr"`
	Role                   string                  `json:"role"`
	MasterHost             string                  `json:"master_host"`
	MasterPort             int                     `json:"master_port"`
	MasterLinkStatus       string                  `json:"master_link_status"`
	MasterLastIoSecondsAgo int64                   `json:"master_last_io_seconds_ago"`
	MasterSyncInPogress    int64                   `json:"master_sync_in_progress"`
	SlaveReplOffset        int64                   `json:"slave_repl_offset"`
	SlavePriority          int64                   `json:"slave_priority"`
	SlaveReadOnly          int                     `json:"slave_read_only"`
	ConnectedSlaves        int                     `json:"connected_slaves"`
	MasterReplOffset       int64                   `json:"master_repl_offset"`
	SlaveList              []InfoReplSlave         `json:"slave_list"`
	RocksdbMasterList      []InfoReplRocksdbMaster `json:"rocksdb_master_list"`
	RocksdbSlaveList       []InfoReplRocksdbSlave  `json:"rocksdb_slave_list"`
}

// String 用于打印
func (rpl *TendisplusInfoReplData) String() string {
	tmp, _ := json.Marshal(rpl)
	return string(tmp)
}

// GetRole master/slave
func (rpl *TendisplusInfoReplData) GetRole() string {
	return rpl.Role
}

// GetMasterLinkStatus up/down
func (rpl *TendisplusInfoReplData) GetMasterLinkStatus() string {
	return rpl.MasterLinkStatus
}

// SlaveMaxLag ..
// - 如果我的角色是slave,则从 RocksdbMasterList 中获取maxLag;
// - 如果我的角色是master,则先根据slaveAddr找到slave,然后从 SlaveList 中获取获取maxLag;
// - 如果slaveAddr为空,则获取master第一个slave的lag作为 maxLag;
func (rpl *TendisplusInfoReplData) SlaveMaxLag(slaveAddr string) (int64, error) {
	var maxLag int64 = 0
	var err error = nil
	slaveAddr = strings.TrimSpace(slaveAddr)
	if rpl.GetRole() == "slave" {
		if rpl.GetMasterLinkStatus() == "down" {
			err = fmt.Errorf("slave:%s master_link_status is %s", rpl.Addr, rpl.GetMasterLinkStatus())
			return maxLag, err
		}
		for _, rdbMaster01 := range rpl.RocksdbMasterList {
			if rdbMaster01.Lag > 18000000000000000 {
				// 以前tendisplus的一个bug, 新版本已修复
				continue
			}
			if rdbMaster01.Lag > maxLag {
				maxLag = rdbMaster01.Lag
			}
		}
		return maxLag, nil
	}
	// role==master
	if len(rpl.SlaveList) == 0 {
		err = fmt.Errorf("master:%s have no slave", rpl.Addr)
		return maxLag, err
	}
	if slaveAddr == "" {
		// default first slave lag
		maxLag = rpl.SlaveList[0].Lag
		return maxLag, nil
	}
	var destSlave *InfoReplSlave = nil
	for _, slave01 := range rpl.SlaveList {
		slaveItem := slave01
		addr01 := fmt.Sprintf("%s:%d", slaveItem.IP, slaveItem.Port)
		if slaveAddr == addr01 {
			destSlave = &slaveItem
			break
		}
	}
	if destSlave == nil {
		err = fmt.Errorf("master:%s not find slave:%s", rpl.Addr, slaveAddr)
		return maxLag, err
	}
	maxLag = destSlave.Lag
	return maxLag, nil
}

// TendisplusInfoRepl tendisplus info replication结果解析
// 参考内容: http://tendis.cn/#/Tendisplus/%E5%91%BD%E4%BB%A4/info?id=replication
func (db *RedisWorker) TendisplusInfoRepl() (replData TendisplusInfoReplData, err error) {
	var replRet string
	replRet, err = db.Client.Info(context.TODO(), "replication").Result()
	if err != nil {
		err = fmt.Errorf("info replication fail,err:%v,aadr:%s", err, db.Addr)
		return
	}
	infoList := strings.Split(replRet, "\n")
	replData = TendisplusInfoReplData{}
	replData.Addr = db.Addr

	slaveReg := regexp.MustCompile(`^slave\d+$`)
	rocksdbSlaveReg := regexp.MustCompile(`^rocksdb\d+_slave\d+$`)
	rocksdbMasterReg := regexp.MustCompile(`^rocksdb\d+_master$`)
	for _, infoItem := range infoList {
		infoItem = strings.TrimSpace(infoItem)
		if strings.HasPrefix(infoItem, "#") {
			continue
		}
		if len(infoItem) == 0 {
			continue
		}
		list01 := strings.SplitN(infoItem, ":", 2)
		if len(list01) < 2 {
			continue
		}
		list01[0] = strings.TrimSpace(list01[0])
		list01[1] = strings.TrimSpace(list01[1])
		if list01[0] == "role" {
			replData.Role = list01[1]
		} else if list01[0] == "master_host" {
			replData.MasterHost = list01[1]
		} else if list01[0] == "master_port" {
			replData.MasterPort, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "master_link_status" {
			replData.MasterLinkStatus = list01[1]
		} else if list01[0] == "master_last_io_seconds_ago" {
			replData.MasterLastIoSecondsAgo, _ = strconv.ParseInt(list01[1], 10, 64)
		} else if list01[0] == "master_sync_in_progress" {
			replData.MasterSyncInPogress, _ = strconv.ParseInt(list01[1], 10, 64)
		} else if list01[0] == "slave_repl_offset" {
			replData.SlaveReplOffset, _ = strconv.ParseInt(list01[1], 10, 64)
		} else if list01[0] == "slave_priority" {
			replData.SlavePriority, _ = strconv.ParseInt(list01[1], 10, 64)
		} else if list01[0] == "slave_read_only" {
			replData.SlaveReadOnly, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "connected_slaves" {
			replData.ConnectedSlaves, _ = strconv.Atoi(list01[1])
		} else if list01[0] == "master_repl_offset" {
			replData.MasterReplOffset, _ = strconv.ParseInt(list01[1], 10, 64)
		} else if slaveReg.MatchString(list01[0]) == true {
			slave01 := InfoReplSlave{}
			err = slave01.decode(infoItem)
			if err != nil {
				return
			}
			replData.SlaveList = append(replData.SlaveList, slave01)
		} else if rocksdbSlaveReg.MatchString(list01[0]) == true {
			rdbSlave01 := InfoReplRocksdbSlave{}
			err = rdbSlave01.decode(infoItem)
			if err != nil {
				return
			}
			replData.RocksdbSlaveList = append(replData.RocksdbSlaveList, rdbSlave01)
		} else if rocksdbMasterReg.MatchString(list01[0]) == true {
			rdbMaster01 := InfoReplRocksdbMaster{}
			err = rdbMaster01.decode(infoItem)
			if err != nil {
				return
			}
			replData.RocksdbMasterList = append(replData.RocksdbMasterList, rdbMaster01)
		}
	}
	return
}
