package backupsys

import (
	"errors"
	"fmt"
	"io/ioutil"
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

// RedisInsRecoverTask 节点数据构造任务
type RedisInsRecoverTask struct {
	SourceIP          string                 `json:"source_ip"`
	SourcePort        int                    `json:"source_ports" `
	NeWTempIP         string                 `json:"new_temp_ip" `
	NewTmpPort        int                    `json:"new_temp_ports"`
	NewTmpPassword    string                 `json:"new_tmp_password"`
	RecoveryTimePoint string                 `json:"recovery_time_point"`
	BackupFileDir     string                 `json:"backup_file_dir"` // 解压后文件
	RecoverDir        string                 `json:"recoverDir"`      // 备份目录
	BackupFile        string                 `json:"backup_file"`     // 备份文件名
	FullBackup        *TplusFullBackPull     `json:"fullBackup"`
	IncrBackup        *TplusIncrBackPull     `json:"incrBackup"`
	SSDIncrBackup     *TredisRocksDBIncrBack `json:"ssdIncrBackup"`
	MyRollbackDir     string                 `json:"myRollbackDir"`   // 从'我'的视角,回档目录
	NodeRollbackDir   string                 `json:"NodeRollbackDir"` // 从'Node'的视角,回档目录
	TendisType        string                 `json:"tendis_type"`
	IsIncludeSlave    bool                   `json:"is_include_slave"`
	IsPrecheck        bool                   `json:"in_precheck"`
	KvstoreNums       int                    `json:"kvstore_nums"`
	MasterVersion     string                 `json:"master_version"` // 确定ssd 加载全备工具版本
	RestoreTool       string                 `json:"restore_tool"`   // ssd  加载全备工具
	SsdDataDir        string                 `json:"ssd_data_dir"`   //  ssd 数据目录
	DepsDir           string                 `json:"deps_dir"`       // /usr/local/redis/bin/deps
	redisCli          *myredis.RedisClient
	runtime           *jobruntime.JobGenericRuntime
	Err               error `json:"-"`
}

// NewRedisInsRecoverTask 新建数据构建任务
func NewRedisInsRecoverTask(sourceIP string, sourcePort int, neWTempIP string, newTmpPort int,
	newTmpPasswordsword, recoveryTimePoint, recoverDir, tendisType string, isIncludeSlave bool, isPrecheck bool,
	runtime *jobruntime.JobGenericRuntime) (task *RedisInsRecoverTask, err error) {
	return &RedisInsRecoverTask{
		SourceIP:          sourceIP,
		SourcePort:        sourcePort,
		NeWTempIP:         neWTempIP,
		NewTmpPort:        newTmpPort,
		NewTmpPassword:    newTmpPasswordsword,
		RecoveryTimePoint: recoveryTimePoint,
		RecoverDir:        recoverDir,
		TendisType:        tendisType,
		IsIncludeSlave:    isIncludeSlave,
		IsPrecheck:        isPrecheck,
		runtime:           runtime,
	}, nil
}

// GetRedisCli 获取redis连接
func (task *RedisInsRecoverTask) GetRedisCli() error {
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
func (task *RedisInsRecoverTask) GetRocksdbNum() (kvstorecounts int, err error) {
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
func (task *RedisInsRecoverTask) PrecheckTendis() error {

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

// Precheck tendisplus && tendis ssd && tendis cache 前置检查
// - 检查源tendis全备+binlog信息是否能获取;
// - 检查目的tendis磁盘空间是否足够;
// NOCC:golint/fnsize(设计如此)
func (task *RedisInsRecoverTask) Precheck() error {

	task.runtime.Logger.Info("Precheck:检查全备和binlog信息是否能获取,磁盘空间是否够")
	task.runtime.Logger.Info("task.TendisType is:%s", task.TendisType)
	// 节点维度的
	// 尝试获取源tendis全备信息
	// 备份系统查询时过滤正则
	fullBack := &TplusFullBackPull{}
	var binlogSize int64
	if task.TendisType == consts.TendisTypeTendisplusInsance {
		incrBack := &TplusIncrBackPull{}
		filename := fmt.Sprintf("TENDISPLUS-FULL-slave-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("需要匹配 filename:%s", filename)

		// 前置检查的时候还没部署节点，拿不到kvstoreNums信息，检查的是给固定值 10
		kvstoreNums := 10
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, kvstoreNums, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}
		task.FullBackup = fullBack
		// 后加
		task.FullBackup.GetTplusFullbackNearestRkTime()
		if task.FullBackup.Err != nil {
			return task.FullBackup.Err
		}
		task.runtime.Logger.Info("查询全备份信息结束")
		// 后加

		// 尝试获取源tendis binlog全备信息
		fileName := fmt.Sprintf("binlog-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("fileName:%s", fileName)
		// 节点维度增备信息：fileName 过滤，task.SourceIP 备份的源IP
		incrBack = NewTplusIncrBackPull(fileName, task.SourceIP)
		if incrBack.Err != nil {
			return incrBack.Err
		}
		layout := "2006-01-02 15:04:05"
		rbDstTime, _ := time.ParseInLocation(layout, task.RecoveryTimePoint, time.Local)
		// 回档目标时间 比 用户填写的时间多1秒
		// (因为binlog_tool的--end-datetime参数,--end-datetime这个时间点的binlog是不会被应用的)
		rbDstTime = rbDstTime.Add(1 * time.Second)
		task.runtime.Logger.Info("回档目标时间 rbDstTime:%v", rbDstTime)

		for i := 0; i < kvstoreNums; i++ {
			// 每个rocksdb全备的startTimeSec是不一样的(所以其拉取的增备范围也是不一样的)
			// 其对应的startTimeSec可以从全备文件中获取到
			// 其对应的startPos也是不同的,从全备中获取这里只是查询，所以startPos传入100也是可以的

			// 这里粗略地 以全备的创建时间 作为 binlog拉取的startTime
			// 后面真实的 binlog拉取startTime 需要从全备文件中获取
			// task.runtime.Logger.Info("kvstore:%d ,backupMeta:%v", i, backupMeta)
			// kvstore 维度的 的拉取备份文件任务，每个kvstore都是一个任务，因为kvstore的开始时间不一样

			incrBack.NewRocksDBIncrBack(i, 100, task.FullBackup.ResultFullbackup[0].BackupStart.Local().Format(layout),
				rbDstTime.Local().Format(layout), task.NeWTempIP, task.RecoverDir, task.RecoverDir)
			if incrBack.Err != nil {
				return incrBack.Err
			}
		}
		task.IncrBackup = incrBack
		task.runtime.Logger.Info("IncrBackup,特定节点的增备信息:%v", task.IncrBackup)
		// 获取节点维度的备份信息
		task.IncrBackup.GetAllIncrBacksInfo()
		if task.IncrBackup.Err != nil {
			return task.IncrBackup.Err
		}
		// binlog 文件大小
		binlogSize = incrBack.TotalSize()

	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {

		filename := fmt.Sprintf("TENDISSSD-FULL-slave-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("需要匹配 filename:%s", filename)
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, 0, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}
		task.FullBackup = fullBack

		task.FullBackup.GetTplusFullbackNearestRkTime()
		if task.FullBackup.Err != nil {
			return task.FullBackup.Err
		}
		task.runtime.Logger.Info("查询全备份信息结束")

		// 新加 binlog 维度
		// 尝试获取源tendis ssd  binlog全备信息
		// 节点维度增备信息：fileName 过滤，task.SourceIP 备份的源IP
		fileName := fmt.Sprintf("binlog-%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("fileName:%s", fileName)

		layout := "2006-01-02 15:04:05"
		rbDstTime, _ := time.ParseInLocation(layout, task.RecoveryTimePoint, time.Local)
		// 回档目标时间 比 用户填写的时间多1秒
		// (因为binlog_tool的--end-datetime参数,--end-datetime这个时间点的binlog是不会被应用的)
		rbDstTime = rbDstTime.Add(1 * time.Second)
		task.runtime.Logger.Info("回档目标时间 rbDstTime:%v", rbDstTime)

		// 传入全备份开始时间和回档时间
		// startTime 拉取增备的开始时间 -> 全备份的开始时间
		// endTime 拉取增备份的结束时间 -> 回档时间
		ssdIncrBackup := NewTredisRocksDBIncrBack(fileName, task.SourceIP, 100,
			task.FullBackup.ResultFullbackup[0].BackupStart.Local().Format(layout),
			rbDstTime.Local().Format(layout), task.NeWTempIP, task.RecoverDir, task.RecoverDir, task.RecoveryTimePoint)
		if ssdIncrBackup.Err != nil {
			task.Err = ssdIncrBackup.Err
			return task.Err
		}

		task.SSDIncrBackup = ssdIncrBackup
		task.runtime.Logger.Info("ssdIncrBackup,特定节点的增备信息:%v", task.SSDIncrBackup)
		// 获取节点维度的备份信息
		task.SSDIncrBackup.GetTredisIncrbacksSpecRocks()
		if task.SSDIncrBackup.Err != nil {
			task.Err = ssdIncrBackup.Err
			return task.Err
		}
		// binlog 文件大小
		binlogSize = task.SSDIncrBackup.TotalSize()

	} else if task.TendisType == consts.TendisTypeRedisInstance {

		filename := fmt.Sprintf("%s-%d", task.SourceIP, task.SourcePort)
		task.runtime.Logger.Info("需要匹配 filename:%s", filename)
		fullBack = NewFullbackPull(task.SourceIP, filename, task.RecoveryTimePoint,
			task.NeWTempIP, task.RecoverDir, 0, task.TendisType)
		if fullBack.Err != nil {
			return fullBack.Err
		}
		task.FullBackup = fullBack
		task.FullBackup.GetTplusFullbackNearestRkTime()
		if task.FullBackup.Err != nil {
			return task.FullBackup.Err
		}
	}

	task.runtime.Logger.Info("binlogSize:%d", binlogSize)

	// 确认磁盘空间足够
	// - 可用空间必须大于 全备大小+binlog大小
	// - 总空间必须大于  全备大小+binlog大小 的两倍
	backupSize := fullBack.TotalSize() + binlogSize
	needSize := 1.2 * float64(backupSize)
	// 检查下载磁盘空间是否足够
	// 备份盘
	bakDiskUsg, err := util.GetLocalDirDiskUsg(task.RecoverDir)
	if err != nil {
		task.runtime.Logger.Error(err.Error())
		return err
	}
	// 数据盘
	dataDiskUsg, err := util.GetLocalDirDiskUsg(consts.GetRedisDataDir())
	if err != nil {
		task.runtime.Logger.Error(err.Error())
		return err
	}

	// 检查备份空间是否大于 全备大小+binlog大小
	if int64(bakDiskUsg.AvailSize) < backupSize {
		err = fmt.Errorf("Precheck failed: ip:%s 备份目录磁盘可用空间:%d MB 小于备份文件所需磁盘空间:%d MB",
			task.NeWTempIP, bakDiskUsg.AvailSize/1024/1024.0, backupSize/1024/1024.0)
		task.runtime.Logger.Error(err.Error())
		return err

	}
	task.runtime.Logger.Info("bakDiskUsg.AvailSize:%d MB backupSize:%d MB",
		bakDiskUsg.AvailSize/1024/1024.0, backupSize/1024/1024.0)

	// 检查数据盘是否大于 1.2*（全备大小+binlog）大小
	if float64(dataDiskUsg.AvailSize) < needSize {
		err = fmt.Errorf("Precheck failed: ip:%s 数据目录磁盘可用空间:%d MB 小于备份文件所需磁盘空间:%d MB",
			task.NeWTempIP, dataDiskUsg.AvailSize/1024/1024.0, backupSize/1024/1024.0)
		task.runtime.Logger.Error(err.Error())
		return err

	}

	task.runtime.Logger.Info("dataDiskUsg.AvailSize:%d MB(%d GB),backupSize:%d MB(%d GB)(%d KB)",
		dataDiskUsg.AvailSize/1024/1024.0, dataDiskUsg.AvailSize/1024/1024/1024.0,
		backupSize/1024/1024.0, backupSize/1024/1024/1024.0, backupSize/1024.0)

	// 磁盘空间使用已有85%,则报错
	if bakDiskUsg.UsageRatio > 85 || dataDiskUsg.UsageRatio > 85 {
		err = fmt.Errorf("Precheck failed: %s disk Used%d%% > 85%% or %s disk Used(%d%%) >85%%",
			task.RecoverDir, bakDiskUsg.UsageRatio,
			consts.GetRedisDataDir(), dataDiskUsg.UsageRatio)
		task.runtime.Logger.Error(err.Error())
		return err
	}

	return nil

}

// ClearAllData 清理目标集群数据
func (task *RedisInsRecoverTask) ClearAllData() error {
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
func (task *RedisInsRecoverTask) ClusterResetMaster() error {
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
func (task *RedisInsRecoverTask) StopSlave() error {
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
func (task *RedisInsRecoverTask) GetBackupFileExt(backupFilePath string) (fileExt string, err error) {
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
func (task *RedisInsRecoverTask) GetDecompressedDir() (decpDir string, err error) {
	if task.BackupFileDir != "" {
		return task.BackupFileDir, nil
	}
	err = fmt.Errorf("BackupFileDir:%s 没有复赋值", task.BackupFileDir)
	task.runtime.Logger.Error(err.Error())
	return decpDir, err

}

// FindDstFileInDir 在指定文件夹下找到目标文件
func (task *RedisInsRecoverTask) FindDstFileInDir(dir string, dstFile string) (dstFilePos string, err error) {
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
func (task *RedisInsRecoverTask) CheckDecompressedDirIsOK() (isExists, isCompelete bool, msg string) {

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
func (task *RedisInsRecoverTask) Decompress(fileName string) error {

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
func (task *RedisInsRecoverTask) RmLocalBakcupFile() error {
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
func (task *RedisInsRecoverTask) RecoverClusterSlots() error {
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
func (task *RedisInsRecoverTask) RecoverSlave() error {
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
	slaveNodes, err := task.GetTplusSlaveNodes(redisAddr)
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
func (task *RedisInsRecoverTask) GetClusterNodes() (fileData []byte, err error) {
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
	fileData, err = ioutil.ReadFile(metaFile)
	if err != nil {
		err = fmt.Errorf("读取cluster_nodes文件:%s失败,err:%v", metaFile, err)
		task.runtime.Logger.Error(err.Error())
		return nil, err
	}
	task.runtime.Logger.Info("cluster_nodes:%s,fileData:%s", metaFile, fileData)

	return fileData, nil
}

// GetTplusSlaveNodes 从本地记录的cluster nodes中获得master的slave
func (task *RedisInsRecoverTask) GetTplusSlaveNodes(masterAddr string) (

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

// PullFullbackup 拉取全备
func (task *RedisInsRecoverTask) PullFullbackup() error {
	fullBack := &TplusFullBackPull{}
	if task.TendisType == consts.TendisTypeTendisplusInsance {
		// 节点维度的
		// 备份系统查询时过滤正则
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
		task.runtime.Logger.Info("PullFullbackup fullBack.FileHead :%s", fullBack.FileHead)

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
	//
	task.runtime.Logger.Info("PullFullbackup task.FullBackup.FileHead :%s", task.FullBackup.FileHead)

	// 获取节点维度的所有文件信息
	task.FullBackup.GetTplusFullbackNearestRkTime()
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
func (task *RedisInsRecoverTask) RestoreFullbackup() error {
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
func (task *RedisInsRecoverTask) PullIncrbackup() {
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
	layout := "2006-01-02 15:04:05"
	rbDstTime, _ := time.ParseInLocation(layout, task.RecoveryTimePoint, time.Local)
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
		incrBack.NewRocksDBIncrBack(i, backupMeta.BinlogPos+1, backupMeta.StartTime.Local().Format(layout),
			rbDstTime.Local().Format(layout), task.NeWTempIP, task.RecoverDir, task.RecoverDir)
		if incrBack.Err != nil {
			task.Err = incrBack.Err
			return
		}
	}
	task.IncrBackup = incrBack
	task.runtime.Logger.Info("IncrBackup,特定节点的增备信息:%v", task.IncrBackup)
	// 获取节点维度的备份信息
	task.IncrBackup.GetAllIncrBacksInfo()
	if task.IncrBackup.Err != nil {
		task.Err = incrBack.Err
		return
	}
	// 拉取节点维度的所有文件
	task.IncrBackup.PullAllFiles()
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
func (task *RedisInsRecoverTask) ImportIncrBackup() error {

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
func (task *RedisInsRecoverTask) GetTendisplusHearbeatKey(masterIP string, masterPort int) string {
	Heartbeat := fmt.Sprintf("%s_%s:heartbeat", masterIP, strconv.Itoa(masterPort))
	return Heartbeat
}

// CheckRollbackResult check rollback result is ok
func (task *RedisInsRecoverTask) CheckRollbackResult() error {

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
	srcNodeHearbeat, err := redisCli.GetTendisplusHeartbeat(srcHearbeatKey)
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

	rollbackDstTime, _ := time.ParseInLocation(consts.UnixtimeLayout, task.RecoveryTimePoint, time.Local)
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
			msg = fmt.Sprintf("目的tendisplus:%s 源tendisplus:%s rocksdbid:%d 回档到时间:%s %s 目的时间:%s",
				redisAddr, srcRedisAddr, i, symbol,
				hearbeatVal.Local().Format(consts.UnixtimeLayout),
				rollbackDstTime.Local().Format(consts.UnixtimeLayout))
			errList = append(errList, msg)
			mylog.Logger.Error(msg)
			continue
		}
		msg = fmt.Sprintf("目的tendisplus:%s 源tendisplus:%s rocksdbid:%d 回档到时间:%s =~ 目的时间:%s",
			redisAddr, srcRedisAddr, i,
			hearbeatVal.Local().Format(consts.UnixtimeLayout),
			rollbackDstTime.Local().Format(consts.UnixtimeLayout))
		mylog.Logger.Info(msg)
	}
	if len(errList) > 0 {
		task.Err = fmt.Errorf("回档失败")
		return task.Err
	}
	return nil
}

// SSDPullIncrbackup ssd拉取增备
func (task *RedisInsRecoverTask) SSDPullIncrbackup() {
	task.runtime.Logger.Info("SSDPullIncrbackup start...")

	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	fileName := fmt.Sprintf("binlog-%s-%d", task.SourceIP, task.SourcePort)
	task.runtime.Logger.Info("Source fileName:%s,DstAddr:%s", fileName, redisAddr)
	// 节点维度增备信息：fileName 过滤，task.SourceIP 备份的源IP

	layout := "2006-01-02 15:04:05"
	rbDstTime, _ := time.ParseInLocation(layout, task.RecoveryTimePoint, time.Local)
	// 回档目标时间 比 用户填写的时间多1秒
	// (因为binlog_tool的--end-datetime参数,--end-datetime这个时间点的binlog是不会被应用的)
	rbDstTime = rbDstTime.Add(1 * time.Second)
	task.runtime.Logger.Info("回档目标时间 rbDstTime:%v", rbDstTime)

	// 传入全备份开始时间和回档时间
	// startTime 拉取增备的开始时间 -> 全备份的开始时间
	// endTime 拉取增备份的结束时间 -> 回档时间
	ssdIncrBackup := NewTredisRocksDBIncrBack(fileName, task.SourceIP, task.FullBackup.ResultFullbackup[0].StartPos,
		task.FullBackup.ResultFullbackup[0].BackupStart.Local().Format(layout),
		rbDstTime.Local().Format(layout), task.NeWTempIP, task.RecoverDir, task.RecoverDir, task.RecoveryTimePoint)
	if ssdIncrBackup.Err != nil {
		task.Err = ssdIncrBackup.Err
		return
	}

	task.SSDIncrBackup = ssdIncrBackup
	task.runtime.Logger.Info("ssdIncrBackup,特定节点的增备信息:%v", task.SSDIncrBackup)
	// 获取节点维度的备份信息
	task.SSDIncrBackup.GetTredisIncrbacksSpecRocks()
	if task.SSDIncrBackup.Err != nil {
		task.Err = ssdIncrBackup.Err
		return
	}
	// 拉取节点维度的所有文件
	task.SSDIncrBackup.PullAllFiles()
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
func (task *RedisInsRecoverTask) SSDRestoreFullbackup() error {
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
func (task *RedisInsRecoverTask) SSDImportIncrBackup() error {

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
func (task *RedisInsRecoverTask) CacheRestoreFullbackup() error {
	redisAddr := fmt.Sprintf("%s:%s", task.NeWTempIP, strconv.Itoa(task.NewTmpPort))
	msg := fmt.Sprintf("master:%s start recover redis from aof/rdb ...", redisAddr)
	task.runtime.Logger.Info(msg)
	// 获取tendis ssd连接
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
func (task *RedisInsRecoverTask) getNeWTempIPClusterNodes() error {

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

	cmd := fmt.Sprintf("cd %s && redis-cli -h %s -p %d -a %s cluster nodes > cluster_nodes.txt",
		task.RecoverDir, task.NeWTempIP, task.NewTmpPort, password)
	logCmd := fmt.Sprintf("cd %s && redis-cli -h %s -p %d -a xxxx cluster nodes > cluster_nodes.txt",
		task.RecoverDir, task.NeWTempIP, task.NewTmpPort)
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
func (task *RedisInsRecoverTask) Run() {

	// flow 先下发一个actuator 来检查备份文件是否存在，备份空间是够足够
	if task.IsPrecheck {
		// 前置检查:备份是否存在等信息、磁盘空间是否够
		err := task.Precheck()
		if err != nil {
			task.Err = err
			return
		}
		return
	}
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

		// 全备下载
		err := task.PullFullbackup()
		if err != nil {
			task.Err = err
			return
		}
		// 增备下载
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
		// 恢复集群关系，因为不知道哪些节点回档成功，所以在下一个actuator 做：由flow传入所以参数

	} else if task.TendisType == consts.TendisTypeTendisSSDInsance {
		task.runtime.Logger.Info("开始Tendis SSD 回档流程")
		// 全备下载
		err := task.PullFullbackup()
		if err != nil {
			task.Err = err
			return
		}

		// 增备下载
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

		// 备份文件下载
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
