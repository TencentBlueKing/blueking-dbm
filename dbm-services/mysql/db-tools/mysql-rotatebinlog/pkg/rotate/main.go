package rotate

import (
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	ma "dbm-services/mysql/db-tools/mysql-crond/api"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/backup"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/log"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/models"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/util"

	"github.com/ghodss/yaml"
	errs "github.com/pkg/errors"
	"github.com/spf13/cast"
	"github.com/spf13/viper"
)

// RotateBinlogComp TODO
type RotateBinlogComp struct {
	Config    string `json:"config"`
	configObj *Config
}

// Example TODO
func (c *RotateBinlogComp) Example() interface{} {
	return RotateBinlogComp{
		Config: "config.yaml",
	}
}

// Init TODO
func (c *RotateBinlogComp) Init() (err error) {

	envPATH := os.Getenv("PATH")
	if envPATH == "" {
		envPATH = "."
	}
	envPATHs := []string{envPATH}
	envPATHs = append(envPATHs, "/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin")
	_ = os.Setenv("PATH", strings.Join(envPATHs, ":"))
	return nil
}

// Start godoc
// 多个实例进行rotate，除了空间释放的计算有关联，其它互补影响
// 即一个实例rotate失败，不影响其它rotate执行。但会抛出失败的那个实例相应错误
func (c *RotateBinlogComp) Start() (err error) {
	if err = log.InitLogger(); err != nil {
		return err
	}
	if c.configObj, err = InitConfig(c.Config); err != nil {
		return err
	}
	if err = log.InitReporter(); err != nil {
		return err
	}
	if err = models.InitDB(); err != nil {
		return err
	}
	setupCloseHandler()
	defer models.DB.Conn.Close()
	if err = models.SetupTable(); err != nil {
		return err
	}

	var servers []*ServerObj
	if err = viper.UnmarshalKey("servers", &servers); err != nil {
		return errs.Wrap(err, "parse config servers")
	} else {
		logger.Info("config servers: %+v", servers)
	}
	var errRet error
	for _, inst := range servers {
		var backupClient backup.BackupClient
		if backupClient, err = backup.InitBackupClient(); err != nil {
			err = errs.WithMessagef(err, "init backup_client")
			logger.Error("%+v", err.Error())
			errRet = errors.Join(errRet, err)
			continue
		}
		inst.backupClient = backupClient // if nil, ignore backup
		inst.instance = &native.InsObject{
			Host:   inst.Host,
			Port:   inst.Port,
			User:   inst.Username,
			Pwd:    inst.Password,
			Socket: inst.Socket,
		}
		if err = validate.GoValidateStruct(inst, true, false); err != nil {
			err = errs.WithMessagef(err, "validate instance %s", inst)
			logger.Error("%+v", err.Error())
			errRet = errors.Join(errRet, err)
			continue
		}
		if err = inst.Rotate(); err != nil {
			err = errs.WithMessagef(err, "run rotatebinlog %d", inst.Port)
			logger.Error("%+v", err)
			errRet = errors.Join(errRet, err)
			continue
		}
	}
	if err = c.decideSizeToFree(servers); err != nil {
		return errors.Join(errRet, err)
	}
	for _, inst := range servers {
		if err = inst.FreeSpace(); err != nil {
			logger.Error("FreeSpace %+v", err)
			errRet = errors.Join(errRet, err)
		}
		if err = inst.rotate.Backup(); err != nil {
			logger.Error("Backup %+v", err)
			errRet = errors.Join(errRet, err)
		}
	}
	return errRet
}

// RemoveConfig 删除某个 binlog 实例的 rotate 配置
func (c *RotateBinlogComp) RemoveConfig(ports []string) (err error) {
	if c.configObj, err = InitConfig(c.Config); err != nil {
		return err
	}
	for _, binlogPort := range ports {
		port := cast.ToInt(binlogPort)
		newServers := make([]*ServerObj, 0)
		var portFound bool
		for _, binlogInst := range c.configObj.Servers {
			if binlogInst.Port == port {
				portFound = true
			} else {
				newServers = append(newServers, binlogInst)
			}
		}
		if !portFound {
			logger.Warn("port instance %d not found when running removeConfig", port)
		}
		c.configObj.Servers = newServers
	}
	yamlData, err := yaml.Marshal(c.configObj) // use json tag
	if err != nil {
		return err
	}
	cfgFile := c.Config // viper.ConfigFileUsed()
	if err = cmutil.FileExistsErr(cfgFile); err != nil {
		return err
	}
	if err := ioutil.WriteFile(cfgFile, yamlData, 0644); err != nil {
		return err
	}
	return nil
}

// HandleScheduler 处理调度选项，返回 handled=true 代表 add/del 选项工作中
func (c *RotateBinlogComp) HandleScheduler(addSchedule, delSchedule bool) (handled bool, err error) {
	if err = log.InitLogger(); err != nil {
		return false, err
	}
	if c.configObj, err = InitConfig(c.Config); err != nil {
		return handled, err
	}
	crondManager := ma.NewManager(viper.GetString("crond.api_url"))
	if delSchedule == true {
		handled = true
		_, err = crondManager.Delete(viper.GetString("crond.item_name"), true)
		if err != nil {
			return handled, err
		}
		return handled, nil
	}
	if addSchedule {
		handled = true
		executable, _ := os.Executable()
		executeDir := filepath.Dir(executable)
		jobItem := ma.JobDefine{
			Name: viper.GetString("crond.item_name"),
			// Command:  fmt.Sprintf(`cd %s && %s`, executeDir, executable),
			Command:  executable,
			WorkDir:  executeDir,
			Args:     []string{"-c", "config.yaml", "1>>logs/main.log 2>&1"},
			Schedule: viper.GetString("crond.schedule"),
			Creator:  "sys",
			Enable:   true,
		}
		logger.Info("adding job_item to crond: %+v", jobItem)
		_, err = crondManager.CreateOrReplace(jobItem, true)
		if err != nil {
			return handled, err
		}
		return handled, nil
	}
	return handled, nil
}

// decideSizeToFree 根据 binlog 所在分区剩余空间 与 binlog 大小，算出需要清理的 binlog size
// 再挑选出可以删除的 binlog 进行删除
// 计算的结果在 i.rotate.sizeToFreeMB 里，表示该实例需要释放的binlog空间
func (c *RotateBinlogComp) decideSizeToFree(servers []*ServerObj) error {
	keepPolicy := viper.GetString("public.keep_policy")
	if keepPolicy == KeepPolicyLeast {
		for _, inst := range servers {
			inst.rotate.sizeToFreeMB = PolicyLeastMaxSize
		}
		logger.Info("keep_policy=%s will try to delete binlog files as much as possible", keepPolicy)
		return nil
	} else if keepPolicy == "" || keepPolicy == KeepPolicyMost {
		logger.Info("keep_policy=%s will calculate size to delete for every binlog instance", keepPolicy)
	} else {
		return fmt.Errorf("unknown keep_policy %s", keepPolicy)
	}

	var diskPartInst = make(map[string][]*ServerObj)      // 每个挂载目录上，放了哪些binlog实例以及对应的binlog空间
	var diskParts = make(map[string]*cmutil.DiskPartInfo) // 目录对应的空间信息
	for _, inst := range servers {
		diskPart, err := util.GetDiskPartitionWithDir(inst.binlogDir)
		if err != nil {
			logger.Warn("fail to get binlog_dir %s disk partition info", inst.binlogDir)
			continue
		}
		mkey := diskPart.Mountpoint
		diskPartInst[mkey] = append(diskPartInst[mkey], inst)
		diskParts[mkey] = diskPart
	}
	logger.Info("binlogDir location: %v, binlogDir Info:%v", diskPartInst, diskParts)
	// 根据 binlog 目录大小来决定删除空间
	var maxBinlogSizeAllowedMB int64 = 1
	if maxBinlogSizeAllowed, err := cmutil.ViperGetSizeInBytesE("public.max_binlog_total_size"); err != nil {
		return err
	} else {
		maxBinlogSizeAllowedMB = maxBinlogSizeAllowed / 1024 / 1024
	}
	logger.Info("viper config:%s, parsed_mb:%d",
		viper.GetString("public.max_binlog_total_size"),
		maxBinlogSizeAllowedMB,
	)

	for diskPartName, diskPart := range diskParts {
		var instBinlogSizeMB = make(map[int]int64) // binlog 端口对应的 binlog大小信息
		for _, inst := range diskPartInst[diskPartName] {
			binlogSizeMB, err := util.GetDirectorySizeMB(inst.binlogDir)
			if err != nil {
				return err
			}
			inst.rotate.binlogSizeMB = binlogSizeMB
			instBinlogSizeMB[inst.Port] = binlogSizeMB
			logger.Info("%d binlogDirSize:%d MB, disk %+v", inst.Port, binlogSizeMB, diskPart)

			if binlogSizeMB > maxBinlogSizeAllowedMB {
				sizeToFree := binlogSizeMB - maxBinlogSizeAllowedMB
				inst.rotate.sizeToFreeMB = sizeToFree
				logger.Info("plan to free space: %+v", inst.rotate)
			}
		}

		// 根据磁盘使用率来决定删除空间
		maxDiskUsedPctAllowed := viper.GetFloat64("public.max_disk_used_pct") / float64(100)
		maxDiskUsedAllowedMB := cast.ToUint64(maxDiskUsedPctAllowed*float64(diskPart.Total)) / 1024 / 1024
		logger.Info("diskPart %s TotalMB:%d UsedPercent:%.2f, maxDiskUsedPctAllowed:%.2f",
			diskPartName, diskPart.Total/1024/1024, diskPart.UsedPercent, maxDiskUsedPctAllowed)
		if diskPart.UsedPercent < maxDiskUsedPctAllowed {
			continue
		}
		diskPartSizeToFreeMB := int64((diskPart.UsedTotal / 1024 / 1024) - maxDiskUsedAllowedMB)
		portSizeToFreeMB := util.DecideSizeToRemove(instBinlogSizeMB, diskPartSizeToFreeMB)
		logger.Info("diskPart %s maxDiskUsedAllowedMB:%d UsedTotalMB:%d expectFreeMB:%d",
			diskPartName, maxDiskUsedAllowedMB, diskPart.UsedTotal/1024/1024, diskPartSizeToFreeMB)
		logger.Info("plan to free spaceMB:%+v", portSizeToFreeMB)
		for _, inst := range diskPartInst[diskPartName] {
			if portSizeToFreeMB[inst.Port] > inst.rotate.sizeToFreeMB {
				inst.rotate.sizeToFreeMB = portSizeToFreeMB[inst.Port]
				logger.Info("plan to free space fixed: %+v", inst.rotate)
			}
		}
	}
	return nil
}

// setupCloseHandler 尽可能保证正常关闭 db
func setupCloseHandler() {
	c := make(chan os.Signal, 2)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		fmt.Println("\r- Ctrl+C pressed in Terminal")
		models.DB.Conn.Close()
		os.Exit(0)
	}()
}
