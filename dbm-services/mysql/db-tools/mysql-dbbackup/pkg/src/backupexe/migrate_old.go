package backupexe

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/mohae/deepcopy"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// MigrateInstanceBackupInfo convert into to index
// 保存index file
func MigrateInstanceBackupInfo(infoFilePath string, cnf *config.BackupConfig) (string, *dbareport.IndexContent, error) {
	var infoObj = InfoFileDetail{}
	if err := ParseBackupInfoFile(infoFilePath, &infoObj); err != nil {
		return "", nil, err
	}
	i, err := os.Stat(infoFilePath)
	if err != nil {
		return "", nil, err
	}
	endTime := cmutil.TimeToSecondPrecision(i.ModTime())
	beginTime, err := time.ParseInLocation(time.DateTime, infoObj.StartTime, time.Local)
	if err != nil {
		return "", nil, err
	}

	backupInfoDir := filepath.Dir(infoFilePath)
	targetName := strings.TrimSuffix(filepath.Base(infoFilePath), ".info")
	gztabBeginFile := filepath.Join(backupInfoDir, targetName+".DUMP.BEGIN.sql.gz")
	xtraInfoFile := filepath.Join(backupInfoDir, targetName+".xtrabackup_info")

	var backupTime time.Time
	if infoObj.BackupType == "gztab" {
		backupTime = beginTime
	} else {
		backupTime = endTime
	}
	var isFullBackup bool
	if infoObj.DataOrGrant == "ALL" {
		isFullBackup = true
	}
	// 生成 backup_id，考虑 spider 全局备份
	backupId := ""
	//backupRole := strings.ToLower(infoObj.BackupRole)
	// 认为凌晨的例行备份，是全备
	if beginTime.Hour() > 0 && beginTime.Hour() < 7 {
		backupId = fmt.Sprintf("mysql-%d-%d-%s-03", cnf.Public.BkBizId, cnf.Public.ClusterId,
			beginTime.Format("20060102"))
	} else {
		backupId = fmt.Sprintf("mysql-%d-%d-%s", cnf.Public.BkBizId, cnf.Public.ClusterId,
			beginTime.Format("20060102-150405"))
	}

	// 转换 file_list 格式，需要读取 backup task_id
	fileList := make([]*dbareport.TarFileItem, 0)
	for fName, _ := range infoObj.FileInfo {
		if uploadInfo, err := readIedBackupUploadInfo(fName); err != nil {
			fmt.Println(err)
			fileList = append(fileList, &dbareport.TarFileItem{FileName: fName})
		} else {
			fileList = append(fileList, &dbareport.TarFileItem{FileName: fName, TaskId: uploadInfo.TaskId})
		}
	}
	// add info file to file_list
	uploadInfo, err := readIedBackupUploadInfo(infoFilePath)
	if err != nil {
		return "", nil, errors.WithMessagef(err, "get infoFile %s upload info", infoFilePath)
	}
	fileList = append(fileList, &dbareport.TarFileItem{
		FileName: infoObj.GetMetafileBasename() + ".info",
		TaskId:   uploadInfo.TaskId,
		FileType: "index", // treat info as index
	})

	// 补齐 version , storage_engine 信息
	db, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return "", nil, errors.WithMessage(err, "get version")
	}
	defer func() {
		_ = db.Close()
	}()
	var serverVersion, storageEngine string
	row := db.QueryRow("select version() serverVersion, @@default_storage_engine storageEngine")
	if err = row.Scan(&serverVersion, &storageEngine); err != nil {
		return "", nil, err
	}

	indexObj := dbareport.IndexContent{
		BackupMetaFileBase: dbareport.BackupMetaFileBase{
			BackupId:             backupId,
			ClusterId:            cnf.Public.ClusterId,
			BkBizId:              cnf.Public.BkBizId,
			ClusterAddress:       cnf.Public.ClusterAddress,
			BackupType:           infoObj.BackupType,
			BackupHost:           infoObj.BackupHost,
			BackupPort:           infoObj.BackupPort,
			MysqlRole:            infoObj.BackupRole,
			DataSchemaGrant:      infoObj.DataOrGrant,
			IsFullBackup:         isFullBackup,
			BackupBeginTime:      beginTime,
			BackupEndTime:        endTime,
			BackupConsistentTime: backupTime,
			ShardValue:           infoObj.ShardValue,
			MysqlVersion:         serverVersion,
		},
		ExtraFields: dbareport.ExtraFields{
			BkCloudId:     0,
			BackupCharset: infoObj.Charset,
			StorageEngine: storageEngine,
		},
		BinlogInfo: dbareport.BinlogStatusInfo{
			ShowMasterStatus: nil,
			ShowSlaveStatus:  nil,
		},
		FileList: fileList,
	}

	// 补齐  show master status, show slave status 信息
	var masterStatus, slaveStatus *dbareport.StatusInfo
	if infoObj.BackupType == "gztab" {
		if masterStatus, slaveStatus, err = MLoadGetBackupSlaveStatus(gztabBeginFile); err != nil {
			return "", nil, err
		}
	}
	if infoObj.BackupType == "xtra" {
		if masterStatus, slaveStatus, err = XLoadGetBackupSlaveStatus(xtraInfoFile); err != nil {
			return "", nil, err
		}
	}
	masterStatus.MasterHost = infoObj.BackupHost
	masterStatus.MasterPort = infoObj.BackupPort
	masterPort := infoObj.BackupPort // master slave has same port
	var masterIp string
	if uploadInfo != nil {
		masterIp = uploadInfo.BindIp
	} else {
		fmt.Println("fail to get ied backup BINDIP for, ignore", infoFilePath)
	}
	//if masterIp == infoObj.BackupHost {} // local ip is master

	if slaveStatus != nil {
		slaveStatus.MasterHost = masterIp
		slaveStatus.MasterPort = masterPort
	}
	indexObj.BinlogInfo.ShowMasterStatus = masterStatus
	indexObj.BinlogInfo.ShowSlaveStatus = slaveStatus

	// 使用新的 index 名
	newTargetName := fmt.Sprintf("%d_%d_%s_%d_%s_%s",
		cnf.Public.BkBizId, cnf.Public.ClusterId, cnf.Public.MysqlHost, cnf.Public.MysqlPort,
		beginTime.Format("20060102150405"), infoObj.BackupType)
	cnf.Public.SetTargetName(newTargetName)
	indexFilePath, err := indexObj.SaveIndexContent(&cnf.Public)
	if err != nil {
		return "", nil, err
	}
	return indexFilePath, &indexObj, nil
}

// MLoadGetBackupSlaveStatus godoc
func MLoadGetBackupSlaveStatus(gztabBeginFile string) (*dbareport.StatusInfo,
	*dbareport.StatusInfo, error) {
	// -- CHANGE MASTER TO
	// -- CHANGE SLAVE TO
	cmd := fmt.Sprintf("zcat %s |grep 'CHANGE '", gztabBeginFile)
	out, err := cmutil.ExecShellCommand(false, cmd)
	if err != nil {
		return nil, nil, err
	}
	changeSqls := cmutil.SplitAnyRune(out, "\n")

	masterStatus := dbareport.StatusInfo{}
	var slaveStatus *dbareport.StatusInfo
	//slaveStatus := dbareport.StatusInfo{}
	// 在 slave 上备份，会同时有 CHANGE MASTER, CHANGE SLAVE
	// 在 master 上备份，只有 CHANGE MASTER
	// CHANGE MASTER 指向的是 master的位点，物理备份是在slave/master
	reChangeMaster := regexp.MustCompile(`(?i:CHANGE MASTER TO)`)
	reChangeSlave := regexp.MustCompile(`(?i:CHANGE SLAVE TO)`)
	for _, sql := range changeSqls {
		if reChangeMaster.MatchString(sql) {
			sql = strings.ReplaceAll(sql, "--", "")
			cm := &mysqlutil.ChangeMaster{ChangeSQL: sql}
			if err := cm.ParseChangeSQL(); err != nil {
				return nil, nil, errors.Wrap(err, sql)
			}
			masterStatus.BinlogFile = cm.MasterLogFile
			masterStatus.BinlogPos = cast.ToString(cm.MasterLogPos)
		} else if reChangeSlave.MatchString(sql) {
			sql = strings.ReplaceAll(sql, "--", "")
			cm := &mysqlutil.ChangeMaster{ChangeSQL: sql}
			if err := cm.ParseChangeSQL(); err != nil {
				return nil, nil, errors.Wrap(err, sql)
			}
			slaveStatus = &dbareport.StatusInfo{}
			slaveStatus.BinlogFile = cm.MasterLogFile
			slaveStatus.BinlogPos = cast.ToString(cm.MasterLogPos)
		}
	}
	if slaveStatus != nil {
		// masterStatus 表示的是本机show master status的输出
		// 当本机是slave的时候，gztab 输出的时候把show slave status作为了do Slave --CHANGE MASTER
		var tmpSlaveStatus = deepcopy.Copy(*slaveStatus).(dbareport.StatusInfo)
		slaveStatus = deepcopy.Copy(&masterStatus).(*dbareport.StatusInfo)
		masterStatus = deepcopy.Copy(tmpSlaveStatus).(dbareport.StatusInfo)
	}
	return &masterStatus, slaveStatus, nil
}

// BackupUploadInfo /data/IEOD_FILE_BACKUP/xxx.done
type BackupUploadInfo struct {
	Name   string
	Md5    string
	BindIp string
	Tag    string
	BuName string
	TaskId string // new added
}

// readIedBackupUploadInfo maybe master's ip
func readIedBackupUploadInfo(infoFilePath string) (*BackupUploadInfo, error) {
	filename := filepath.Base(infoFilePath)
	doneFile := filepath.Join("/data/IEOD_FILE_BACKUP/", filename+".Done")
	buf, err := os.ReadFile(doneFile)
	if err != nil {
		return nil, errors.WithMessagef(err, "read backup Done file")
	}
	uploadInfo := BackupUploadInfo{}
	lines := strings.Split(string(buf), "\n")
	var fileName, bindIp, fileTag, taskId string
	for _, l := range lines {
		if strings.HasPrefix(l, "BINDIP=") {
			bindIp = strings.TrimSpace(strings.TrimPrefix(l, "BINDIP="))
		} else if strings.HasPrefix(l, "NAME=") {
			fileName = strings.TrimSpace(strings.TrimPrefix(l, "NAME="))
		} else if strings.HasPrefix(l, "TAG=") {
			fileTag = strings.TrimSpace(strings.TrimPrefix(l, "TAG="))
		} else if strings.HasPrefix(l, "taskid:") {
			taskId = strings.TrimSpace(strings.TrimPrefix(l, "taskid:"))
		}
	}
	if fileName != "" && taskId != "" {
		//fileNameBase := filepath.Base(fileName)
		uploadInfo = BackupUploadInfo{Name: fileName, BindIp: bindIp, Tag: fileTag, TaskId: taskId}
		return &uploadInfo, nil
	}
	return nil, errors.Errorf("done file %s taskid:%s NAME=%s", doneFile, taskId, fileName)
}

// XLoadGetBackupSlaveStatus godoc
func XLoadGetBackupSlaveStatus(xtraInfoFile string) (*dbareport.StatusInfo, *dbareport.StatusInfo, error) {
	targetPrefix := strings.TrimSuffix(xtraInfoFile, ".xtrabackup_info")
	xtraSlaveInfoFile := targetPrefix + ".xtrabackup_slave_info" // 当前备份的对端 master 位点
	xtraBinlogInfo := targetPrefix + ".xtrabackup_binlog_info"   // 当前备份所在实例位点, 可能master可能slave

	binlogInfo, err := os.ReadFile(xtraBinlogInfo)
	if err != nil {
		return nil, nil, err
	}

	backupRole := ""
	if cmutil.FileExists(xtraSlaveInfoFile) {
		backupRole = "slave"
	} else {
		backupRole = "master"
	}
	masterStatus := dbareport.StatusInfo{}
	var slaveStatus *dbareport.StatusInfo
	if cm, err := mysqlutil.ParseXtraBinlogInfo(string(binlogInfo)); err != nil {
		return nil, nil, err
	} else {
		masterStatus.BinlogFile = cm.MasterLogFile
		masterStatus.BinlogPos = cast.ToString(cm.MasterLogPos)
	}
	if backupRole == "slave" {
		if slaveInfo, err := os.ReadFile(xtraSlaveInfoFile); err != nil {
			return nil, nil, err
		} else {
			cm := &mysqlutil.ChangeMaster{ChangeSQL: string(slaveInfo)}
			if err := cm.ParseChangeSQL(); err != nil {
				return nil, nil, errors.Wrap(err, string(slaveInfo))
			}
			slaveStatus = &dbareport.StatusInfo{}
			slaveStatus.BinlogFile = cm.MasterLogFile
			slaveStatus.BinlogPos = cast.ToString(cm.MasterLogPos)
		}
	}
	return &masterStatus, slaveStatus, nil
}

// BackupFile TODO
type BackupFile struct {
	Filename string    `json:"filename"`
	FileInfo *FileInfo `json:"file_info"`
}

// FileInfo TODO
type FileInfo struct {
	Md5           string `json:"md5"`
	Size          string `json:"size"`
	CreateTime    string `json:"createTime"`
	FileLastMtime string `json:"file_last_mtime"`
	SourceIp      string `json:"source_ip"`
	SourcePort    string `json:"source_port"`
}

// InfoFileDetail save info in the MYSQL_FULL_BACKUP .info file
type InfoFileDetail struct {
	App         string            `json:"app"`
	Charset     string            `json:"charset"`
	DbList      []string          `json:"dbList"`
	Cmd         string            `json:"cmd"`
	BackupType  string            `json:"backupType"`
	BackupRole  string            `json:"backupRole"`
	FileInfo    map[string]string `json:"fileInfo"` // {"somefile.tar":"md5_value", "file": "md5"}
	FullyStamp  string            `json:"fullyStamp"`
	FullName    string            `json:"fullName"`
	BackupHost  string
	BackupPort  int
	StartTime   string
	DataOrGrant string `json:"dataOrGrant"`
	ShardValue  int    `json:"shardValue"`

	flagTar        bool
	backupBasename string

	infoFilePath string // InfoFileDetail full path filename
	fileList     []BackupFile
	// backupFiles, full: [], info:[], priv:[]
	backupFiles map[string][]string

	backupDir string // 备份所在目录
	targetDir string
}

// ParseBackupInfoFile 读取 .info 文件
// infoFile 输入完整路径
func ParseBackupInfoFile(infoFilePath string, infoObj *InfoFileDetail) error {
	// func (i *InfoFileDetail) Load(infoFile string) error {
	fileDir, fileName := filepath.Split(infoFilePath)
	f, err := os.Open(infoFilePath)
	if err != nil {
		return errors.Wrap(err, infoFilePath) // os.IsNotExist(err) || os.IsPermission(err)
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	reg := regexp.MustCompile(`^(\w+)\s*=\s*(.*)$`)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		array := reg.FindStringSubmatch(line)
		if len(array) != 3 {
			continue
		}
		k, v := array[1], array[2]

		switch k {
		case "APP":
			infoObj.App = v
		case "CHARSET":
			infoObj.Charset = v
		case "DBLIST":
			dblist := cmutil.SplitAnyRune(v, " ")
			dblist = cmutil.RemoveEmpty(dblist)
			infoObj.DbList = dblist
		case "CMD":
			infoObj.Cmd = v
		case "BACKTYPE":
			infoObj.BackupType = common.LooseBackupTypeMap(v)
			if cmutil.StringsHasICase(common.LooseBackupTypeList(), v) {
				infoObj.flagTar = true
			}
		case "BACKROLE":
			infoObj.BackupRole = v
		case "DataOrGrant":
			infoObj.DataOrGrant = v
		case "ShardValue":
			infoObj.ShardValue = cast.ToInt(v)
		case "FILE_INFO":
			res := make([]map[string]string, 0)
			if err := json.Unmarshal([]byte(v), &res); err != nil {
				return fmt.Errorf("unmarshal file info failed, data:%s, err:%s", v, err.Error())
			}
			fileMap := make(map[string]string)
			for _, row := range res {
				for k, v := range row {
					fileMap[k] = v
				}
			}
			infoObj.FileInfo = fileMap
		case "FULLY_STAMP":
			infoObj.FullyStamp = v
		case "FULLY_NAME":
			infoObj.FullName = v
		default:
		}
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("scan file %s failed, err:%s", infoFilePath, err.Error())
	}
	infoObj.infoFilePath = infoFilePath
	if err := infoObj.parseBackupInstance(); err != nil {
		return err
	}
	infoObj.backupBasename = strings.TrimSuffix(fileName, ".info")
	infoObj.backupDir = fileDir
	// infoObj.targetDir = filepath.Join(fileDir, infoObj.backupIndexBasename)
	return nil
}

const (
	TypeGZTAB = "gztab"
	TypeXTRA  = "xtra"
)

// parseBackupInstance 从 cmd 中过去 backupHost, backupPort, startTime
func (i *InfoFileDetail) parseBackupInstance() error {
	var reg *regexp.Regexp
	if i.BackupType == TypeGZTAB {
		reg = regexp.MustCompile(`.*_(\d+\.\d+\.\d+\.\d+)_(\d+)_(\d+_\d+)\.info`)
	} else if i.BackupType == TypeXTRA {
		reg = regexp.MustCompile(`.*_(\d+\.\d+\.\d+\.\d+)_(\d+)_(\d+_\d+)_xtra\.info`)
	} else {
		return fmt.Errorf("uknown backup type %s", i.BackupType)
	}
	m := reg.FindStringSubmatch(filepath.Base(i.infoFilePath))
	if len(m) != 4 {
		return fmt.Errorf("failed to get host:port from %s", i.infoFilePath)
	}
	/*
		if i.BackupType == TypeGZTAB {
			// --gztab=/data1/dbbak/DBHA_host-1_127.0.0.1_20000_20220831_200425
			reg = regexp.MustCompile(`gztab=.*_(\d+\.\d+\.\d+\.\d+)_(\d+)_(\d+_\d+).*`)
		} else if i.BackupType == TypeXTRA {
			// --target-dir=/data1/dbbak/DBHA_host-1_127.0.0.1_20000_20220907_040332_xtra
			reg = regexp.MustCompile(`target-dir=.*_(\d+\.\d+\.\d+\.\d+)_(\d+)_(\d+_\d+).*`)
		} else {
			return fmt.Errorf("uknown backup type %s", i.BackupType)
		}
		m := reg.FindStringSubmatch(i.Cmd)
		if len(m) != 4 {
			return fmt.Errorf("failed to get host:port from %s", i.Cmd)
		}
	*/
	i.BackupHost = m[1]
	i.BackupPort, _ = strconv.Atoi(m[2])
	timeLayout := `20060102_150405`
	if t, e := time.Parse(timeLayout, m[3]); e != nil {
		return fmt.Errorf("backup start_time parse failed %s", m[3])
	} else {
		i.StartTime = t.Format(time.DateTime)
	}
	return nil
}

func (i *InfoFileDetail) GetMetafileBasename() string {
	return i.backupBasename
}
