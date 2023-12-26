package datastructure

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// TendisInsRecoverTask 节点数据构造任务
type TendisInsRecoverTask struct {
	SourceIP          string                 `json:"source_ip"`
	SourcePort        int                    `json:"source_ports" `
	NeWTempIP         string                 `json:"new_temp_ip" `
	NewTmpPort        int                    `json:"new_temp_ports"`
	NewTmpPassword    string                 `json:"new_tmp_password"`
	RecoveryTimePoint string                 `json:"recovery_time_point"`
	BackupFileDir     string                 `json:"backup_file_dir"` // 解压后文件
	RecoverDir        string                 `json:"recoverDir"`      // 备份目录
	BackupFile        string                 `json:"backup_file"`     // 备份文件名
	FullBackup        *TendisFullBackPull    `json:"fullBackup"`      // cache、ssd、plus 全备
	IncrBackup        *TplusIncrBackPull     `json:"incrBackup"`      // tendisplus binlog
	SSDIncrBackup     *TredisRocksDBIncrBack `json:"ssdIncrBackup"`   // ssd binlog

	TendisType     string `json:"tendis_type"`
	IsIncludeSlave bool   `json:"is_include_slave"`
	KvstoreNums    int    `json:"kvstore_nums"`
	MasterVersion  string `json:"master_version"` // 确定ssd 加载全备工具版本
	RestoreTool    string `json:"restore_tool"`   // ssd  加载全备工具
	SsdDataDir     string `json:"ssd_data_dir"`   //  ssd 数据目录
	DepsDir        string `json:"deps_dir"`       // /usr/local/redis/bin/deps
	redisCli       *myredis.RedisClient
	runtime        *jobruntime.JobGenericRuntime
	Err            error        `json:"-"`
	FullFileList   []FileDetail `json:"full_file_list"`    // 全备文件列表
	BinlogFileList []FileDetail `json:"binlog_file_list" ` // 增备文件列表

}

// FileDetail 备份文件结果记录详情
type FileDetail struct {
	TaskID        string `json:"task_id"`         // 任务ID，用于拉取备份文件
	Uptime        string `json:"uptime"`          // 备份任务上报时间
	FileLastMtime string `json:"file_last_mtime"` // 文件最后修改时间
	SourceIP      string `json:"source_ip"`       // 备份源IP
	Size          int    `json:"size" validate:"required"`
	FileTag       string `json:"file_tag"` // 文件类型 REDIS_FULL、REDIS_BINLOG
	Status        string `json:"status"`
	FileName      string `json:"file_name" validate:"required"`
}

// NewTendisInsRecoverTask 新建数据构建任务
func NewTendisInsRecoverTask(sourceIP string, sourcePort int, neWTempIP string, newTmpPort int,
	newTmpPasswordsword, recoveryTimePoint, recoverDir, tendisType string, isIncludeSlave bool,
	runtime *jobruntime.JobGenericRuntime, fullFileList []FileDetail,
	binlogFileList []FileDetail) (task *TendisInsRecoverTask, err error) {
	return &TendisInsRecoverTask{
		SourceIP:          sourceIP,
		SourcePort:        sourcePort,
		NeWTempIP:         neWTempIP,
		NewTmpPort:        newTmpPort,
		NewTmpPassword:    newTmpPasswordsword,
		RecoveryTimePoint: recoveryTimePoint,
		RecoverDir:        recoverDir,
		TendisType:        tendisType,
		IsIncludeSlave:    isIncludeSlave,
		runtime:           runtime,
		FullFileList:      fullFileList,
		BinlogFileList:    binlogFileList,
	}, nil
}

// GetRedisCli 获取redis连接
func (task *TendisInsRecoverTask) GetRedisCli() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始获取master:%s的连接...", redisAddr)
	task.runtime.Logger.Info(msg)
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		err = fmt.Errorf("获取连接失败:%v", err)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	task.runtime.Logger.Info("获取master:%s的连接成功", redisAddr)
	task.redisCli = redisCli
	return nil
}

// GetRocksdbNum 获取tendisplus kvstore 个数
func (task *TendisInsRecoverTask) GetRocksdbNum() (kvstorecounts int, err error) {
	task.runtime.Logger.Info("GetRocksdbNum start ...")

	// 获取kvstore个数
	var kvstorecount string
	kvstorecount, err = task.redisCli.GetKvstoreCount()
	if err != nil {
		err = fmt.Errorf("GetRocksdbNum GetKvstoreCount Err:%v", err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	task.runtime.Logger.Info("kvstorecount:%s", kvstorecount)
	kvstorecounts, err = strconv.Atoi(kvstorecount)
	if err != nil {
		errMsg := fmt.Sprintf(" kvstorecount  string to int failed err:%v", err)
		task.runtime.Logger.Error(errMsg)
	}
	task.KvstoreNums = kvstorecounts
	return
}

// PrecheckTendis tendis 前置检查
func (task *TendisInsRecoverTask) PrecheckTendis() error {

	task.runtime.Logger.Info("Precheck:检查链接是否可用")
	// 检查tendis 是否可连接，是否在使用中
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	replInfo, err := task.redisCli.Info("replication")
	if err != nil {
		return err
	}
	role, _ := replInfo["role"]

	// 校验角色是否是master
	if role != consts.RedisMasterRole {
		err = fmt.Errorf("Precheck failed: target tendis:%s role:%s !=master", redisAddr, role)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	task.runtime.Logger.Info("%s: role:%s", redisAddr, role)

	// 校验集群是否有业务在使用
	isUsing, cmds, err := task.redisCli.IsRedisUsing("redis-cli ", 10*time.Second)
	if err != nil {
		err = fmt.Errorf("Precheck failed: target tendis:%s isUsing:%v", redisAddr, err)
		return err
	}
	if isUsing == true {
		err = fmt.Errorf("Precheck failed: target tendis:%s is in use<br>cmds:%s", redisAddr, strings.Join(cmds, "<br>"))
		return err
	}
	task.runtime.Logger.Info("target tendis:%s no using", redisAddr)

	return nil

}

// ClearAllData 清理目标集群数据
func (task *TendisInsRecoverTask) ClearAllData() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始清理master:%s数据(fluashall)", redisAddr)
	task.runtime.Logger.Info(msg)

	cmd := []string{consts.TendisPlusFlushAllRename}
	result, err := task.redisCli.DoCommand(cmd, 0)
	if err != nil {
		return err
	}

	if !strings.Contains(result.(string), "OK") {
		err = fmt.Errorf("flush all master[%s]", redisAddr)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	msg = fmt.Sprintf("清理master:%s数据(fluashall)完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// ClusterResetMaster 断开目的回档节点和集群的联系(cluster reset)
func (task *TendisInsRecoverTask) ClusterResetMaster() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始断开master:%s与集群的联系(cluster reset)...", redisAddr)
	task.runtime.Logger.Info(msg)

	err := task.redisCli.ClusterReset()
	if err != nil {
		return err
	}
	time.Sleep(5 * time.Second) // sleep 2 seconds
	// 检查确实与集群断开联系
	runningMasters, err := task.redisCli.GetRunningMasters()
	if err != nil {
		return err
	}
	if len(runningMasters) != 1 {
		err = fmt.Errorf("master:%s cluster reset fail,running master count:%d > 1",
			redisAddr, len(runningMasters))
		str, _ := task.redisCli.GetClusterNodesStr()
		task.runtime.Logger.Error("cluster nodes%v,err:%v", str, err)

	}
	msg = fmt.Sprintf("断开master:%s与集群的联系(cluster reset)成功", redisAddr)
	task.runtime.Logger.Info(msg)

	return nil

}

// StopSlave 断开slave到master的同步关系
func (task *TendisInsRecoverTask) StopSlave() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始断开slave到master:%s的同步关系...", redisAddr)
	task.runtime.Logger.Info(msg)

	// 找到目标tendisplus 的slave
	slaveNodeList, err := task.redisCli.GetAllSlaveNodesByMasterAddr(redisAddr)
	if err != nil && util.IsNotFoundErr(err) == false {
		return err
	}
	if err != nil && util.IsNotFoundErr(err) == true {
		msg = fmt.Sprintf("master:%s 没有发现连接的slave,无需断开slave连接", redisAddr)
		task.runtime.Logger.Error(msg)
		return err
	}
	for _, slaveNodeTmp := range slaveNodeList {
		slaveNode01 := slaveNodeTmp

		msg = fmt.Sprintf("master:%s开始断开slave:%s同步关系", redisAddr, slaveNode01.Addr)
		task.runtime.Logger.Info(msg)

		// 断开同步关系
		newCli01, err := myredis.NewRedisClient(slaveNode01.Addr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
		if err != nil {
			return err
		}
		err = newCli01.ClusterReset()
		if err != nil {
			newCli01.Close()
			return err
		}
		time.Sleep(5 * time.Second)

		// 检查同步关系确实已断开
		infoData, err := newCli01.Info("replication")
		if err != nil {
			newCli01.Close()
			return err
		}
		newCli01.Close()
		role, _ := infoData["role"]
		if role != "master" {
			err = fmt.Errorf("%s 执行'cluster reset'失败,info replication结果role:%s,而不是master", slaveNode01.Addr, role)
			task.runtime.Logger.Error(err.Error())
			return err
		}
		msg = fmt.Sprintf("master:%s 断开slave:%s同步成功,slave Role:%s", redisAddr, slaveNode01.Addr, role)
		task.runtime.Logger.Info(msg)
	}

	msg = fmt.Sprintf("master:%s 共断开%d个slave同步关系", redisAddr, len(slaveNodeList))
	task.runtime.Logger.Info(msg)
	return nil
}

// GetBackupFileExt 获取全备文件后缀
func (task *TendisInsRecoverTask) GetBackupFileExt(backupFilePath string) (fileExt string, err error) {
	fileExt = filepath.Ext(backupFilePath)
	if fileExt == ".tar" || fileExt == ".tgz" {
		return fileExt, nil
	} else if strings.HasSuffix(backupFilePath, ".tar.gz") {
		fileExt = ".tar.gz"
	} else {
		err = fmt.Errorf("无法解压全备文件:%s", backupFilePath)
		task.runtime.Logger.Error(err.Error())
		return "", err
	}
	return fileExt, nil
}

// GetDecompressedDir 获取 recoverDir 的值,全备解压目录
// 如全备名是 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140.tar
// 则值为 3-TENDISPLUS-FULL-slave-127.0.0.x-30002-20230810-050140
func (task *TendisInsRecoverTask) GetDecompressedDir() (decpDir string, err error) {
	if task.BackupFileDir != "" {
		return task.BackupFileDir, nil
	}
	err = fmt.Errorf("BackupFileDir:%s 没有复赋值", task.BackupFileDir)
	task.runtime.Logger.Error(err.Error())
	return decpDir, err

}

// FindDstFileInDir 在指定文件夹下找到目标文件
func (task *TendisInsRecoverTask) FindDstFileInDir(dir string, dstFile string) (dstFilePos string, err error) {
	err = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.Name() == dstFile {
			dstFilePos = path
			return nil
		}
		return nil
	})
	if err != nil {
		err = fmt.Errorf("findDstFileInDir filepath.Walk fail,err:%v,dir:%s dstFile:%s", err, dir, dstFile)
		task.runtime.Logger.Error(err.Error())
		return "", err
	}
	if dstFilePos == "" {
		info := fmt.Sprintf("the destination file was not found in dir,dstFile:%s,dir:%s", dstFile, dir)
		task.runtime.Logger.Info(info)
		return "", util.NewNotFoundErr()
	}
	return
}

// CheckDecompressedDirIsOK 检查全备解压文件夹 是否存在,数据是否完整
// 数据是否完整:通过判断是否有clustermeta.txt、${rocksdbIdx}/backup_meta文件来确认
func (task *TendisInsRecoverTask) CheckDecompressedDirIsOK() (isExists, isCompelete bool, msg string) {

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg = fmt.Sprintf("开始检查全备(已解压)目录是否存在,是否完整")
	task.runtime.Logger.Info(msg)
	// 测试tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		return false, false, msg
	}
	defer redisCli.Close()

	isExists = false
	isCompelete = false

	decpDir, err := task.GetDecompressedDir()
	if err != nil {
		return
	}

	if _, err := os.Stat(decpDir); os.IsNotExist(err) {
		msg = fmt.Sprintf("全备解压目录:%s 不存在", decpDir)
		task.runtime.Logger.Info(msg)
		return
	}
	isExists = true // 解压目录存在
	var metaFile string
	metaFile, err = task.FindDstFileInDir(decpDir, "clustermeta.txt")
	if err != nil {
		return
	}
	if _, err := os.Stat(metaFile); os.IsNotExist(err) {
		// clustermeta.txt 不存在
		msg = fmt.Sprintf("全备解压目录:%s 中找不到 clustermeta.txt 文件", decpDir)
		task.runtime.Logger.Info(msg)
		isCompelete = false
		return
	}
	ClusterMeataDir := filepath.Dir(metaFile)

	// 获取kvstore个数
	var kvstorecount string
	kvstorecount, err = redisCli.GetKvstoreCount()
	if err != nil {
		err = fmt.Errorf("CheckDecompressedDirIsOK GetKvstoreCount Err:%v", err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	task.runtime.Logger.Info("kvstorecount:%s", kvstorecount)
	kvstorecounts, err := strconv.Atoi(kvstorecount)
	if err != nil {
		errMsg := fmt.Sprintf("%s kvstorecount  string to int failed err:%v", redisAddr, task.Err)
		task.runtime.Logger.Error(errMsg)
	}

	for i := 0; i < kvstorecounts; i++ {
		rocksdbBackupMeta := filepath.Join(ClusterMeataDir, fmt.Sprintf("%d/backup_meta", i))
		if _, err := os.Stat(rocksdbBackupMeta); os.IsNotExist(err) {
			msg = fmt.Sprintf("全备解压目录:%s/%d/backup_meta 找不到", decpDir, i)
			task.runtime.Logger.Info(msg)
			isCompelete = false
			return
		}
	}
	msg = fmt.Sprintf("解压目录存在且完整:%s", decpDir)
	task.runtime.Logger.Info(msg)
	// 解压文件存在且是完整的
	return true, true, msg
}

// Decompress 解压文件
func (task *TendisInsRecoverTask) Decompress(fileName string) error {

	// 解压 .lzo 类型文件
	if strings.HasSuffix(fileName, ".lzo") {
		// 检查 lzop 是否存在
		lzopBin := consts.LzopBin
		_, err := os.Stat(lzopBin)
		if err != nil && os.IsNotExist(err) {
			task.runtime.Logger.Error("Decompress: 解压工具 lzop 不存在,"+
				"请检查 %s  是否存在 err:%v", consts.LzopBin, err)
			task.runtime.Logger.Error(err.Error())
			return err

		}
		// 解压
		DecompressCmd := fmt.Sprintf("%s -d %s", lzopBin, fileName)
		task.runtime.Logger.Info("DecompressCmd:%s", DecompressCmd)
		_, err = util.RunLocalCmd("bash", []string{"-c", DecompressCmd}, "", nil, 10*time.Minute)
		if err != nil {
			task.runtime.Logger.Error("Decompress: 解压失败,请检查 %s 是否异常 err:%v", fileName, err)
			return err
		}
		return nil
	}

	var DecompressCmd string
	bkFileExt, err := task.GetBackupFileExt(fileName)
	if err != nil {
		return err
	}
	if bkFileExt == ".tar" {
		DecompressCmd = fmt.Sprintf("tar -xf %s", fileName)
	} else if bkFileExt == ".tar.gz" || bkFileExt == ".tgz" {
		DecompressCmd = fmt.Sprintf("tar -zxf %s", fileName)
	}

	if DecompressCmd != "" {

		// 将全备文件解压到指定目录下
		DecompressCmd = fmt.Sprintf("cd %s  && %s -C %s", task.RecoverDir, DecompressCmd, task.RecoverDir)
		msg := fmt.Sprintf("解压命令:%s", DecompressCmd)
		task.runtime.Logger.Info(msg)
		_, err = util.RunLocalCmd("bash", []string{"-c", DecompressCmd}, "", nil, 10*time.Minute)
		if err != nil {
			return err
		}
		if task.TendisType == consts.TendisTypeTendisplusInsance {
			isExists, isCompelete, msg := task.CheckDecompressedDirIsOK()
			if err != nil {
				return err
			}
			if isExists == false || isCompelete == false {
				// 如果不存在或不完整
				err = errors.New(msg)
				task.runtime.Logger.Error(err.Error())
				return err
			}

		} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
			// todo
			task.runtime.Logger.Info("检查tendis ssd 的全备解压文件是否有效")
			decpDir, err := task.GetDecompressedDir()
			if err != nil {
				return err
			}
			task.FullBackup.tendisSSDBackupVerify(decpDir)
		}

		// 	（测试先不删）删除 源文件
		err = task.RmLocalBakcupFile()
		if err != nil {
			return err
		}
	}

	return nil
}

// RmLocalBakcupFile 删除本地全备(未解压)文件
func (task *TendisInsRecoverTask) RmLocalBakcupFile() error {
	bkFileFullPath := filepath.Join(task.RecoverDir, task.BackupFile)
	if _, err := os.Stat(bkFileFullPath); os.IsNotExist(err) {
		return err
	}
	rmCmd := fmt.Sprintf("cd %s && rm -rf %s 2>/dev/null", task.RecoverDir, task.BackupFile)
	_, err := util.RunLocalCmd("bash", []string{"-c", rmCmd}, "", nil, 30*time.Minute)
	if err != nil {
		return err
	}
	msg := fmt.Sprintf("本地全备(未解压):%s 删除成功", task.BackupFile)
	task.runtime.Logger.Info(msg)
	return nil
}

// RecoverClusterSlots 恢复tendisplus slots信息
// 依据全备clustermeta.txt文件中slot:xxx-xxxx信息,cluster addslot
func (task *TendisInsRecoverTask) RecoverClusterSlots() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始恢复master:%s slots信息", redisAddr)
	task.runtime.Logger.Info(msg)

	fullClusterMeta, err := task.GetClusterMeata()
	if err != nil {
		return err
	}
	msg = fmt.Sprintf("redisAddr:%s全备中slots:%s", redisAddr, fullClusterMeta.Slot)
	task.runtime.Logger.Info(msg)

	slotList, _, _, _, err := myredis.DecodeSlotsFromStr(fullClusterMeta.Slot, "")
	if err != nil {
		return err
	}
	_, err = task.redisCli.ClusterAddSlots(slotList)
	if err != nil {
		return err
	}
	msg = fmt.Sprintf("恢复master:%s slots信息:%s 完成", redisAddr, fullClusterMeta.Slot)
	task.runtime.Logger.Info(msg)
	return nil
}

// RecoverSlave 恢复slave同步关系
// NOCC:golint/fnsize(设计如此)
func (task *TendisInsRecoverTask) RecoverSlave() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始恢复slave到master:%s的同步关系...", redisAddr)
	task.runtime.Logger.Info(msg)

	// 获取master的nodeiD
	var rbTenplusNodeData *myredis.ClusterNodeData = nil
	_, err := task.redisCli.GetClusterNodes()
	if err != nil {
		return err
	}
	clusterNodes, err := task.redisCli.GetAddrMapToNodes()
	if err != nil {
		return err
	}
	rbTenplusNodeData, ok := clusterNodes[redisAddr]
	if ok == false {
		err = fmt.Errorf("获取%s cluster nodes信息失败,结果为空", redisAddr)
		str01, _ := task.redisCli.GetClusterNodesStr()
		task.runtime.Logger.Info("cluster nodes:%v", str01)
		task.runtime.Logger.Error(err.Error())
		return err
	}
	msg = fmt.Sprintf("master:%s 对应NodeID:%s", redisAddr, rbTenplusNodeData.NodeID)
	task.runtime.Logger.Info(msg)

	// 从恢复目录的cluster_nodes.txt获取slave信息，cluster_nodes.txt是任务开始时生成的
	slaveNodes, err := task.GetTendisSlaveNodes(redisAddr)
	if err != nil {
		err = fmt.Errorf("master:%s 从cluster_nodes.txt中没有找到任何slave", redisAddr)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	msg = fmt.Sprintf("master:%s 从cluster nodes中共找到%d个slave", redisAddr, len(slaveNodes))
	task.runtime.Logger.Info(msg)
	maxRetryTimes := 10 // 最多重试10次
	isOK := false
	for _, slaveNode01 := range slaveNodes {
		slaveNodeItem := slaveNode01
		slaveAddr := slaveNodeItem.Addr
		slaveCli02, err := myredis.NewRedisClient(slaveAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
		if err != nil {
			return err
		}
		msg = fmt.Sprintf("master:%s 'cluster meet' slave:%s", redisAddr, slaveAddr)
		task.runtime.Logger.Info(msg)

		list01 := strings.Split(slaveAddr, ":")
		// cluster meet slave
		_, err = task.redisCli.ClusterMeet(list01[0], list01[1])
		if err != nil {
			slaveCli02.Close()
			return err
		}
		// 确保slave 和 master已connected
		idx := 0
		for ; idx < maxRetryTimes; idx++ {
			time.Sleep(5 * time.Second)
			_, err = slaveCli02.GetClusterNodes()
			if err != nil {
				return err
			}
			clusterNodes, err = slaveCli02.GetAddrMapToNodes()
			if err != nil {
				return err
			}
			_, isOK = clusterNodes[redisAddr]
			if isOK == true {
				msg = fmt.Sprintf("get master info success in slave after 'cluster meet',master:%s,slave:%s",
					redisAddr, slaveAddr)
				task.runtime.Logger.Info(msg)
				break
			}
			msg = fmt.Sprintf("slave:%s still not connected master:%s", slaveAddr, redisAddr)
			task.runtime.Logger.Info(msg)
			str01, _ := slaveCli02.GetClusterNodesStr()
			task.runtime.Logger.Info("print slave cluster nodes:%v", str01)
		}
		if isOK == false {
			err = fmt.Errorf("slave cannot connect master after 'cluster meet',slave:%s,master:%s",
				slaveAddr, redisAddr)
			task.runtime.Logger.Error(err.Error())
			return err
		}
		msg = fmt.Sprintf("slave:%s 'cluster replicate' master nodeID:%s", slaveAddr, rbTenplusNodeData.NodeID)
		task.runtime.Logger.Info(msg)
		// cluster replicate
		_, err = slaveCli02.ClusterReplicate(rbTenplusNodeData.NodeID)
		if err != nil {
			slaveCli02.Close()
			return err
		}
		time.Sleep(5 * time.Second)
		// 检查同步确实恢复
		infoData, err := slaveCli02.Info("replication")
		if err != nil {
			slaveCli02.Close()
			return err
		}
		slaveCli02.Close()
		role, _ := infoData["role"]
		if role != consts.RedisSlaveRole {
			err = fmt.Errorf("%s 执行'cluster replicate %s'失败,info replication结果role:%s,而不是slave",
				slaveAddr, rbTenplusNodeData.NodeID, role)
			task.runtime.Logger.Error(err.Error())
			return err
		}
		msg = fmt.Sprintf("slave:%s 'info replication'=>role:%s", slaveAddr, role)
		task.runtime.Logger.Info(msg)
	}
	msg = fmt.Sprintf("master:%s成功恢复%d个slave同步关系", redisAddr, len(slaveNodes))
	task.runtime.Logger.Info(msg)
	return nil
}

// GetClusterNodes 从备份文件目录获取clusternode信息，从而获取master的slaves信息
func (task *TendisInsRecoverTask) GetClusterNodes() (fileData []byte, err error) {
	if task.RecoverDir == "" {
		err = fmt.Errorf("task.RecoverDir:%s 为空,请检查RestoreBackup功能处的解压和赋值情况", task.RecoverDir)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	metaFile := filepath.Join(task.RecoverDir, "cluster_nodes.txt")
	_, err = os.Stat(metaFile)
	if err != nil {
		err = fmt.Errorf("%s os.Stat fail,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	fileData, err = os.ReadFile(metaFile)
	if err != nil {
		err = fmt.Errorf("读取cluster_nodes文件:%s失败,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	task.runtime.Logger.Info("cluster_nodes:%s,fileData:%s", metaFile, fileData)

	return fileData, nil
}

// GetTendisSlaveNodes 从本地记录的cluster nodes中获得master的slave
func (task *TendisInsRecoverTask) GetTendisSlaveNodes(masterAddr string) (

	slaveNodes []*myredis.ClusterNodeData, err error) {
	fileData, err := task.GetClusterNodes()
	if err != nil {
		return nil, err
	}

	nodesData, err := myredis.DecodeClusterNodes(string(fileData))
	if err != nil {
		return nil, err
	}
	task.runtime.Logger.Info("get nodesData from cluster_nodes.txt success:%v", nodesData)
	m01 := make(map[string]*myredis.ClusterNodeData)
	for _, tmpItem := range nodesData {
		infoItem := tmpItem
		m01[infoItem.Addr] = infoItem
	}
	masterNode, ok := m01[masterAddr]
	if ok == false {
		err = fmt.Errorf("not found master node:%s", masterAddr)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	if masterNode.Role != consts.RedisMasterRole {
		err = fmt.Errorf("node:%s not a master(role:%s)", masterAddr, masterNode.Role)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	for _, info01 := range m01 {
		infoItem := info01
		// NOCC:tosa/linelength(其他)
		if infoItem.Role == consts.RedisSlaveRole && infoItem.LinkState == consts.RedisLinkStateConnected &&
			infoItem.MasterID == masterNode.NodeID {
			msg := fmt.Sprintf("master:%s 找到一个slave:%s ", masterAddr, infoItem.Addr)
			task.runtime.Logger.Info(msg)
			slaveNodes = append(slaveNodes, infoItem)
		}
	}
	if len(slaveNodes) == 0 {
		msg := fmt.Sprintf("master:%s 没有找到任何slave信息", masterAddr)
		task.runtime.Logger.Info(msg)
		err = util.NewNotFoundErr()
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	task.runtime.Logger.Info("master:%s, get slaveNodes from cluster_nodes.txt success,slaveNodes:%v",
		masterAddr, slaveNodes)

	return slaveNodes, nil

}

// PullFullbackup 校验全备
func (task *TendisInsRecoverTask) PullFullbackup() error {
	fullBack := &TendisFullBackPull{}
	if task.TendisType == consts.TendisTypeTendisplusInsance {
		// 节点维度的
		// 查询时过滤正则
		filename := fmt.Sprintf("TENDISPLUS-FULL-slave-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("filename:%s", filename)
		kvstoreNums, err := task.GetRocksdbNum()
		if err != nil {
			return err
		}
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, kvstoreNums, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}
		//
		task.runtime.Logger.Info("Fullbackup fullBack.FileHead :%s", fullBack.FileHead)
		task.runtime.Logger.Info("PullFullbackup task.RecoveryTimePoint :%s", task.RecoveryTimePoint)

	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		filename := fmt.Sprintf("TENDISSSD-FULL-slave-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("filename:%s", filename)
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, 0, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}

	} else if task.TendisType == consts.TendisTypeRedisInstance {

		filename := fmt.Sprintf("%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("需要匹配 filename:%s", filename)
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, 0, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}
		task.FullBackup = fullBack
	}

	task.FullBackup = fullBack
	// 对传入的全备份文件进行校验
	task.runtime.Logger.Info("Fullbackup task.FullBackup.FileHead :%s", task.FullBackup.FileHead)

	// 校验节点维度的所有文件信息
	task.FullBackup.GetTendisFullbackNearestRkTime(task.FullFileList)
	if task.FullBackup.Err != nil {
		return task.FullBackup.Err
	}
	// 备份文件解压
	task.FullBackup.PullFullbackDecompressed()
	if task.FullBackup.Err != nil {
		return task.FullBackup.Err
	}
	return nil
}

// RestoreFullbackup 导入全备
func (task *TendisInsRecoverTask) RestoreFullbackup() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s开始导入全备", redisAddr)
	task.runtime.Logger.Info(msg)
	// 再次探测tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		return err
	}
	defer redisCli.Close()

	task.FullBackup.RestoreBackup(task.NeWTempIP, task.NewTmpPort, task.NewTmpPassword)
	if task.FullBackup.Err != nil {
		task.Err = task.FullBackup.Err
		return err
	}
	msg = fmt.Sprintf("master:%s导入全备完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// PullIncrbackup 拉取增备
func (task *TendisInsRecoverTask) PullIncrbackup() {
	task.runtime.Logger.Info("PullIncrbackup start...")

	// 节点维度的
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	fileName := fmt.Sprintf("binlog-%s-%d", task.SourceIP, task.SourcePort)
	task.runtime.Logger.Info("fileName:%s", fileName)
	// 节点维度增备信息：fileName 过滤，task.SourceIP 备份的源IP
	incrBack := NewTplusIncrBackPull(fileName, task.SourceIP)
	if incrBack.Err != nil {
		task.Err = incrBack.Err
		return
	}
	rbDstTime, _ := time.ParseInLocation(consts.UnixtimeLayoutZone, task.RecoveryTimePoint, time.Local)
	// 回档目标时间 比 用户填写的时间多1秒
	// (因为binlog_tool的--end-datetime参数,--end-datetime这个时间点的binlog是不会被应用的)
	rbDstTime = rbDstTime.Add(1 * time.Second)
	task.runtime.Logger.Info("回档目标时间 rbDstTime:%v", rbDstTime)
	// 获取kvstore个数
	var kvstorecount string
	kvstorecount, err := task.redisCli.GetKvstoreCount()
	if err != nil {
		err = fmt.Errorf("PullIncrbackup GetKvstoreCount Err:%v", err)
		task.runtime.Logger.Error(err.Error())
		return
	}
	task.runtime.Logger.Info("kvstorecount:%s", kvstorecount)
	kvstorecounts, err := strconv.Atoi(kvstorecount)
	if err != nil {
		errMsg := fmt.Sprintf("%s kvstorecount  string to int failed err:%v", redisAddr, task.Err)
		task.runtime.Logger.Error(errMsg)
	}
	for i := 0; i < kvstorecounts; i++ {
		// 每个rocksdb全备的startTimeSec是不一样的(所以其拉取的增备范围也是不一样的)
		// 其对应的startTimeSec可以从全备文件中获取到
		// 其对应的startPos也是不同的,从全备中获取
		backupMeta, err := task.GetRocksdbBackupMeta(i)
		if err != nil {
			task.Err = err
			return
		}
		// task.runtime.Logger.Info("kvstore:%d ,backupMeta:%v", i, backupMeta)
		// kvstore 维度的 的拉取备份文件任务，每个kvstore都是一个任务，因为kvstore的开始时间不一样
		incrBack.NewRocksDBIncrBack(i, backupMeta.BinlogPos+1, backupMeta.StartTime.Local().Format(consts.UnixtimeLayoutZone),
			rbDstTime.Local().Format(consts.UnixtimeLayoutZone), task.NeWTempIP, task.RecoverDir, task.RecoverDir)
		if incrBack.Err != nil {
			task.Err = incrBack.Err
			return
		}
	}
	task.IncrBackup = incrBack
	task.runtime.Logger.Info("IncrBackup,特定节点的增备信息:%v", task.IncrBackup)
	// 获取节点维度的备份信息
	task.IncrBackup.GetAllIncrBacksInfo(task.BinlogFileList)
	if task.IncrBackup.Err != nil {
		task.Err = incrBack.Err
		return
	}
	// 检查节点维度的所有binlog文件是否在存在
	task.IncrBackup.CheckAllBinlogFiles()
	if task.IncrBackup.Err != nil {
		task.Err = task.IncrBackup.Err
		return
	}
	// 解压所有备份文件
	task.IncrBackup.Decompressed()
	if task.IncrBackup.Err != nil {
		task.Err = task.IncrBackup.Err
		return
	}
	return
}

// ImportIncrBackup 导入binlog
func (task *TendisInsRecoverTask) ImportIncrBackup() error {

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s开始导入增备(binlog)", redisAddr)
	task.runtime.Logger.Info(msg)
	// 再次探测tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		task.Err = err
		return task.Err
	}
	defer redisCli.Close()

	task.IncrBackup.ImportBinlogsToTplus(task.NeWTempIP, task.NewTmpPort, task.NewTmpPassword)
	if task.Err != nil {
		task.Err = task.IncrBackup.Err
		return task.Err
	}
	msg = fmt.Sprintf("master:%s导入增备(binlog)完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// GetTendisplusHearbeatKey 根据tendisplus 节点信息获取心跳key
func (task *TendisInsRecoverTask) GetTendisplusHearbeatKey(masterIP string, masterPort int) string {
	Heartbeat := fmt.Sprintf("%s_%s:heartbeat", masterIP, strconv.Itoa(masterPort))
	return Heartbeat
}

// CheckRollbackResult check rollback result is ok
func (task *TendisInsRecoverTask) CheckRollbackResult() error {

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("CheckRollbackResult: master:%s开始检查回档结果是否正确", redisAddr)
	task.runtime.Logger.Info(msg)
	// 获取redis连接
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		task.Err = err
		return task.Err
	}
	defer redisCli.Close()
	// 检查目的集群是否有源集群的心跳数据
	srcHearbeatKey := task.GetTendisplusHearbeatKey(task.SourceIP, task.SourcePort)
	mylog.Logger.Info("srcHearbeatKey:%s", srcHearbeatKey)
	srcNodeHearbeat, err := redisCli.GetTendisplusHeartbeat(srcHearbeatKey)
	msg = fmt.Sprintf("检查目的集群是否有源集群的心跳数据:%v", srcNodeHearbeat)
	mylog.Logger.Info(msg)
	if err != nil {
		task.Err = err
		return task.Err
	}

	srcRedisAddr := fmt.Sprintf("%s:%s", task.SourceIP, strconv.Itoa(task.SourcePort))
	if len(srcNodeHearbeat) == 0 {
		msg = fmt.Sprintf("源tendisplus:%s 没有心跳写入,跳过回档结果校验", srcRedisAddr)
		mylog.Logger.Info(msg)
		return task.Err
	}
	kvstoreNums, err := task.GetRocksdbNum()
	if err != nil {
		task.Err = err
		return task.Err
	}

	rollbackDstTime, _ := time.ParseInLocation(consts.UnixtimeLayoutZone, task.RecoveryTimePoint, time.Local)
	var hearbeatVal time.Time
	var ok bool
	var errList []string

	for i := 0; i < kvstoreNums; i++ {
		if hearbeatVal, ok = srcNodeHearbeat[i]; ok == false {
			msg = fmt.Sprintf("源tendisplus:%s rocksdbid:%d 没有心跳写入", srcRedisAddr, i)
			mylog.Logger.Warn(msg)
			return task.Err
		}
		symbol := ""
		if rollbackDstTime.Sub(hearbeatVal).Minutes() > 10 {
			symbol = "<"
		} else if rollbackDstTime.Sub(hearbeatVal).Minutes() < -10 {
			symbol = ">"
		}
		if symbol != "" {
<<<<<<< HEAD
			msg = fmt.Sprintf("目的tendisplus:%s 源tendisplus:%s rocksdbid:%d 回档到时间:%s %s 目的时间:%s",
				redisAddr, srcRedisAddr, i, symbol,
				hearbeatVal.Local().Format(consts.UnixtimeLayoutZone),
=======
			msg = fmt.Sprintf("目的tendisplus:%s 源tendisplus:%s rocksdbid:%d 回档心跳时间:%s %s 回档目的时间:%s",
				redisAddr, srcRedisAddr, i,
				hearbeatVal.Local().Format(consts.UnixtimeLayoutZone),
				symbol,
>>>>>>> d5ec126a220b4c3ef375c443e1dfd1dcc75977cd
				rollbackDstTime.Local().Format(consts.UnixtimeLayoutZone))
			errList = append(errList)
			mylog.Logger.Error(msg)
			continue
		}
		msg = fmt.Sprintf("目的tendisplus:%s 源tendisplus:%s rocksdbid:%d 回档心跳时间:%s =~ 回档目的时间:%s",
			redisAddr, srcRedisAddr, i,
			hearbeatVal.Local().Format(consts.UnixtimeLayoutZone),
			rollbackDstTime.Local().Format(consts.UnixtimeLayoutZone))
		mylog.Logger.Info(msg)
	}
	if len(errList) > 0 {
		task.Err = fmt.Errorf("回档失败")
		return task.Err
	}
	return nil
}

// SSDPullIncrbackup ssd拉取增备
func (task *TendisInsRecoverTask) SSDPullIncrbackup() {
	task.runtime.Logger.Info("SSDPullIncrbackup start...")

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	fileName := fmt.Sprintf("binlog-%s-%d", task.SourceIP, task.SourcePort)
	task.runtime.Logger.Info("Source fileName:%s,DstAddr:%s", fileName, redisAddr)
	// 节点维度增备信息：fileName 过滤，task.SourceIP 备份的源IP

	rbDstTime, _ := time.ParseInLocation(consts.UnixtimeLayoutZone, task.RecoveryTimePoint, time.Local)
	// 回档目标时间 比 用户填写的时间多1秒
	// (因为binlog_tool的--end-datetime参数,--end-datetime这个时间点的binlog是不会被应用的)
	rbDstTime = rbDstTime.Add(1 * time.Second)
	task.runtime.Logger.Info("回档目标时间 rbDstTime:%v", rbDstTime)

	// 传入全备份开始时间和回档时间
	// startTime 拉取增备的开始时间 -> 全备份的开始时间
	// endTime 拉取增备份的结束时间 -> 回档时间
	ssdIncrBackup := NewTredisRocksDBIncrBack(fileName, task.SourceIP, task.FullBackup.ResultFullbackup[0].StartPos,
		task.FullBackup.ResultFullbackup[0].BackupStart.Local().Format(consts.UnixtimeLayoutZone),
		rbDstTime.Local().Format(consts.UnixtimeLayoutZone), task.NeWTempIP,
		task.RecoverDir, task.RecoverDir, task.RecoveryTimePoint)
	if ssdIncrBackup.Err != nil {
		task.Err = ssdIncrBackup.Err
		return
	}

	task.SSDIncrBackup = ssdIncrBackup
	task.runtime.Logger.Info("ssdIncrBackup,特定节点的增备信息:%v", task.SSDIncrBackup)
	// 获取节点维度的备份信息
	task.SSDIncrBackup.GetTredisIncrbacksSpecRocks(task.BinlogFileList)
	if task.SSDIncrBackup.Err != nil {
		task.Err = ssdIncrBackup.Err
		return
	}
	// 检验节点维度的所有binlog文件是否存在：解压和未解压的情况：
	// 但是当缺失一个解压的时候，会把未解压的也删除了？
	task.SSDIncrBackup.CheckAllBinlogFiles()
	if task.SSDIncrBackup.Err != nil {
		task.Err = task.SSDIncrBackup.Err
		return
	}
	// 解压所有备份文件
	task.SSDIncrBackup.Decompressed()
	if task.SSDIncrBackup.Err != nil {
		task.Err = task.SSDIncrBackup.Err
		return
	}
	return
}

// SSDRestoreFullbackup 导入全备
func (task *TendisInsRecoverTask) SSDRestoreFullbackup() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s start recover_tredis_from_rocksdb ...", redisAddr)
	task.runtime.Logger.Info(msg)
	// 获取tendis ssd连接
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisSSDInsance)
	if err != nil {
		return err
	}

	defer redisCli.Close()

	task.FullBackup.RecoverTredisFromRocksdb(task.NeWTempIP, task.NewTmpPort, task.NewTmpPassword)
	if task.FullBackup.Err != nil {
		task.Err = task.FullBackup.Err
		return err
	}
	msg = fmt.Sprintf("master:%s导入全备完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// SSDImportIncrBackup 导入binlog
func (task *TendisInsRecoverTask) SSDImportIncrBackup() error {

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s开始导入增备(binlog)", redisAddr)
	task.runtime.Logger.Info(msg)
	// 再次探测tendisplus连接性
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeTendisSSDInsance)
	if err != nil {
		task.Err = err
		return task.Err
	}
	defer redisCli.Close()

	task.SSDIncrBackup.ImportAllBinlogToTredis(task.NeWTempIP, task.NewTmpPort, task.NewTmpPassword)
	if task.Err != nil {
		task.Err = task.IncrBackup.Err
		return task.Err
	}
	msg = fmt.Sprintf("master:%s导入增备(binlog)完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// CacheRestoreFullbackup 导入全备
func (task *TendisInsRecoverTask) CacheRestoreFullbackup() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s start recover redis from aof/rdb ...", redisAddr)
	task.runtime.Logger.Info(msg)
	// 获取tendis 连接
	redisCli, err := myredis.NewRedisClient(redisAddr, task.NewTmpPassword, 0, consts.TendisTypeRedisInstance)
	if err != nil {
		return err
	}

	defer redisCli.Close()
	// NOCC:tosa/linelength(其他)
	task.FullBackup.RecoverCacheRedisFromBackupFile(task.SourceIP, task.SourcePort, task.NeWTempIP, task.NewTmpPort,
		task.NewTmpPassword)
	if task.FullBackup.Err != nil {
		task.Err = task.FullBackup.Err
		return task.Err
	}
	msg = fmt.Sprintf("master:%s导入全备完成", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// getNeWTempIPClusterNodes 生成 cluster_nodes.txt 信息
func (task *TendisInsRecoverTask) getNeWTempIPClusterNodes() error {

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("开始获取master:%s的连接...", redisAddr)
	task.runtime.Logger.Info(msg)
	password, err := myredis.GetRedisPasswdFromConfFile(task.NewTmpPort)
	if err != nil {
		return err
	}
	// 验证节点是否可连接
	redisCli, err := myredis.NewRedisClient(redisAddr, password, 0, consts.TendisTypeTendisplusInsance)
	if err != nil {
		return err
	}
	defer redisCli.Close()
	if task.RecoverDir == "" {
		err := fmt.Errorf("task.RecoverDir为空,请赋值")
		task.runtime.Logger.Error(err.Error())
		return err
	}
	// 获取前先检查是否存在
	clusterNodeInfoFile := filepath.Join(task.RecoverDir, "cluster_nodes.txt")
	_, err = os.Stat(clusterNodeInfoFile)
	// 如存在先删除
	if err == nil {
		mvCmd := fmt.Sprintf("cd %s && mv cluster_nodes.txt cluster_nodes_bak.txt", task.RecoverDir)
		task.runtime.Logger.Info("mv cluster_nodes.txt文件:%s", mvCmd)
		_, err = util.RunLocalCmd("bash", []string{"-c", mvCmd}, "", nil, 600*time.Second)
		if err != nil {
			task.runtime.Logger.Error(fmt.Sprintf("mv cluster_nodes.txt文件失败,详情:%v", err))
			return err
		}
	}

	cmd := fmt.Sprintf("cd %s && %s -h %s -p %d -a %s --no-auth-warning cluster nodes > cluster_nodes.txt",
		task.RecoverDir, consts.TendisplusRediscli, task.NeWTempIP, task.NewTmpPort, password)
	logCmd := fmt.Sprintf("cd %s && %s -h %s -p %d -a xxxx --no-auth-warning cluster nodes > cluster_nodes.txt",
		task.RecoverDir, consts.TendisplusRediscli, task.NeWTempIP, task.NewTmpPort)
	task.runtime.Logger.Info("获取cluster nodes信息:%s", logCmd)
	ret01, err := util.RunLocalCmd("bash", []string{"-c", cmd}, "", nil, 600*time.Second)
	if err != nil {
		task.runtime.Logger.Error(fmt.Sprintf("获取cluster nodes信息失败,详情:%v", err))
		return err
	}
	ret01 = strings.TrimSpace(ret01)
	if strings.Contains(ret01, "ERR:") == true {
		task.runtime.Logger.Error(fmt.Sprintf("获取cluster nodes信息失败,err:%v,cmd:%s", err, logCmd))

		return err
	}
	msg = fmt.Sprintf("redisAddr:%s获取cluster nodes信息成功", redisAddr)
	task.runtime.Logger.Info(msg)
	return nil
}

// Run 回档逻辑
// NOCC:golint/fnsize(设计如此)
func (task *TendisInsRecoverTask) Run() {

	// tendis 前置检查:连接，是否在使用
	err := task.PrecheckTendis()
	if err != nil {
		task.Err = err
		return
	}

	if task.TendisType == consts.TendisTypeTendisplusInsance {
		task.runtime.Logger.Info("开始Tendisplus 回档流程")
		// 如果是集群包含slave得情况，获取临时集群的cluster nodes 信息
		if task.IsIncludeSlave {
			err := task.getNeWTempIPClusterNodes()
			if err != nil {
				task.Err = err
				return
			}
		}

		// 全备文件校验
		err := task.PullFullbackup()
		if err != nil {
			task.Err = err
			return
		}
		// 增备文件校验
		task.PullIncrbackup()
		if task.Err != nil {
			task.Err = err
			return
		}
		// 清理数据，如果已经有部分数据，则会加载失败
		err = task.ClearAllData()
		if err != nil {
			task.Err = err
			return
		}
		// 停slave 断开同步,restorebackup的时候，用于恢复的目标实例不能是从属实例，同时用于恢复的目标实例不能有从属实例，否则会报错
		if task.IsIncludeSlave {
			err = task.StopSlave()
			if err != nil {
				task.Err = err
				return
			}

		}
		// 重置集群，去掉集群和slots信息
		err = task.ClusterResetMaster()
		if err != nil {
			task.Err = err
			return
		}
		// 加载全备
		err = task.RestoreFullbackup()
		if err != nil {
			task.Err = err
			return
		}
		// 加载binlog
		err = task.ImportIncrBackup()
		if err != nil {
			task.Err = err
			return
		}
		// 回档结果校验
		err = task.CheckRollbackResult()
		if err != nil {
			task.Err = err
			return
		}
		// 恢复master节点 slots信息（add slot）
		err = task.RecoverClusterSlots()
		if err != nil {
			task.Err = err
			return
		}
		// 恢复slave关系
		if task.IsIncludeSlave {
			err = task.RecoverSlave()
			if err != nil {
				task.Err = err
				return
			}
		}
		// 恢复集群关系，因为不知道哪些节点回档成功，所以在下发一个actuator 做：由flow传入所以参数

	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		task.runtime.Logger.Info("开始Tendis SSD 回档流程")
		// 全备文件校验
		err := task.PullFullbackup()
		if err != nil {
			task.Err = err
			return
		}

		// 增备文件校验
		task.SSDPullIncrbackup()
		if task.Err != nil {
			task.Err = err
			return
		}
		// 加载全备
		err = task.SSDRestoreFullbackup()
		if err != nil {
			task.Err = err
			return
		}
		// 加载binlog
		err = task.SSDImportIncrBackup()
		if err != nil {
			task.Err = err
			return
		}

	} else if task.TendisType == consts.TendisTypeRedisInstance {
		task.runtime.Logger.Info("开始Tendis Cache 回档流程")

		// 备份文件校验
		err := task.PullFullbackup()
		if err != nil {
			task.Err = err
			return
		}

		// 加载备份文件
		err = task.CacheRestoreFullbackup()
		if err != nil {
			task.Err = err
			return
		}

	}

	return
}
