package pitr

import (
	"bytes"
	"dbm-services/mongodb/db-tools/dbmon/pkg/consts"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

// Output 如果有别的程序调用mongo-recover，可以根据type == OUTPUT/SUCC/FAIL 过滤到有用的日志
func Output(format string, a ...interface{}) {
	//format = "OUTPUT "+ strings.TrimSuffix(format, "\n") + "\n"
	//return fmt.Printf(format, a...)
	log.WithField("type", "OUTPUT").Printf(format, a...)
}

// ExitSuccess print succ and exit
func ExitSuccess(format string, a ...interface{}) {
	log.WithField("type", "SUCC").Printf(format, a...)
}

// ExitFailed print error and exit
func ExitFailed(format string, a ...interface{}) {
	log.WithField("type", "FAIL").Printf(format, a...)
	os.Exit(1)

}

func appendLog(commandLine, restoreLogfile string, stdout, stderr string, err error) {
	buf1 := bytes.NewBufferString(stdout)
	buf2 := bytes.NewBufferString(stderr)
	SaveRestoreLog(commandLine, restoreLogfile, *buf1, *buf2, true, err)
}

// SaveRestoreLog 保存恢复日志
func SaveRestoreLog(commandLine, restoreLogfile string, outBuf, errBuf bytes.Buffer, appendFlag bool, err error) {
	flag := os.O_CREATE | os.O_WRONLY
	if appendFlag {
		flag = os.O_APPEND | os.O_WRONLY
	}

	if f, err2 := os.OpenFile(restoreLogfile, flag, 0644); err2 == nil {
		defer f.Close()
		f.WriteString("cmd: " + commandLine + "\n")
		f.WriteString("stdout begin:\n")
		f.Write(outBuf.Bytes())
		f.WriteString("\nstdout end\n")

		f.WriteString("stderr begin:\n")
		f.Write(errBuf.Bytes())
		f.WriteString("\nstderr end\n")

		f.WriteString("golang error begin\n")
		f.WriteString(fmt.Sprintf("%v\n", err))
		f.WriteString("golang error end\n")
		log.Printf("Write restoreLogfile: %s succ", restoreLogfile)
	} else {
		log.Warnf("Write restoreLogfile: %s error", restoreLogfile)
	}
}

// ProcessLog 进度日志
type ProcessLog struct {
	t     time.Time
	Msg   string
	IsErr bool
}

// NewProcessLog 创建进度日志
func NewProcessLog(msg string, isErr bool) *ProcessLog {
	return &ProcessLog{
		t:     time.Now(),
		Msg:   msg,
		IsErr: isErr,
	}
}

// SendProcessLog 发送进度日志
func SendProcessLog(logChan chan *ProcessLog, msg string) {
	if logChan == nil {
		return
	}
	logChan <- NewProcessLog(msg, false)
}

// SendErrorProcessLog 发送进度日志
func SendErrorProcessLog(logChan chan *ProcessLog, msg string) {
	if logChan == nil {
		return
	}
	logChan <- NewProcessLog(msg, true)
}

// UntarFull 解压全量备份到临时目录, 如果file是archive, 则直接返回, 不进行解压. 返回值: 临时目录, 子目录名, 是否gzip, 是否archive, 错误
func UntarFull(backupFileDir string, file *BackupFileName) (
	fullTmpDir, subDirName string, gzip bool, zstd bool, archive bool, err error) {
	if err = os.Chdir(backupFileDir); err != nil {
		err = errors.Wrap(err, "Cannot chdir to %s")
		return
	}

	archive = strings.HasSuffix(file.FileName, ".archive") ||
		strings.HasSuffix(file.FileName, ".archive.zstd") ||
		strings.HasSuffix(file.FileName, ".archive.zst")
	// 如果file是archive.zstd, 则zstd为true. 不存在没有archive的zstd文件.
	zstd = strings.HasSuffix(file.FileName, ".archive.zstd") || strings.HasSuffix(file.FileName, ".archive.zst")

	subDirName = file.FileName
	for _, suffix := range []string{".gz", ".tar", ".archive", ".archive.zstd", ".archive.zst"} {
		subDirName = strings.TrimSuffix(subDirName, suffix)
	}

	fullTmpDir = path.Join("tmp", subDirName, "full")

	if _, err = os.Stat(fullTmpDir); err == nil {
		err = fmt.Errorf("tmpDir:[%s] already exists, please delete it first", fullTmpDir)
		return
	}

	if err = os.MkdirAll(fullTmpDir, os.FileMode(0755)); err != nil {
		err = fmt.Errorf("mkdir %s err:%v", fullTmpDir, err)
		return
	}

	if archive {
		// if archive, just return. no need to untar.
		return fullTmpDir, subDirName, gzip, zstd, archive, nil
	}

	var tarArg string
	tarCmd := mycmd.New("tar")
	if strings.HasSuffix(file.FileName, ".gz") {
		gzip = false
		tarArg = "zxf"
	} else {
		gzip = true
		tarArg = "xf"
	}
	tarCmd.Append(tarArg, file.FileName, "-C", fullTmpDir)

	var ebuf string
	_, _, ebuf, err = tarCmd.RunByBash("", time.Hour*24)
	if err != nil {
		err = fmt.Errorf("%s return error %s, stdout:%s", tarCmd.GetCmdLine("", false), err, ebuf)
	}
	return
}

// DoMongoRestoreFULL 导入全量备份
func DoMongoRestoreFULL(bin string, conn *mymongo.MongoHost, file *BackupFileName,
	backupFileDir string, logChan chan *ProcessLog) (string, error) {
	// fmt.Printf("DoMongoRestore: %s %s to %s:%s\n", file.Type, file.FileName, conn.Host, conn.Port)

	SendProcessLog(logChan, fmt.Sprintf("start to untar %s ", file.FileName))

	fullTmpDir, subDirName, gzip, zstd, archive, err := UntarFull(backupFileDir, file)
	if err != nil {
		SendErrorProcessLog(logChan, fmt.Sprintf("UntarFull return %s", err.Error()))
		return "", errors.Wrap(err, "UntarFull")
	}
	SendProcessLog(logChan, fmt.Sprintf("untar %s end. dir:%s", file.FileName, path.Join(fullTmpDir, subDirName)))

	// 如果file是archive, 则不需要删除admin数据库.
	if !archive {
		adminDbDir := filepath.Join(fullTmpDir, subDirName, "dump", "admin")
		adminFileList, err := os.ReadDir(adminDbDir)
		if err != nil {
			return "", fmt.Errorf("no admin database:%s %v", adminDbDir, err)
		}
		var deletedFileNames []string
		for _, fi := range adminFileList {
			if !fi.IsDir() && strings.HasPrefix(fi.Name(), "system.") {
				fullName := filepath.Join(adminDbDir, fi.Name())
				if err2 := os.Remove(fullName); err2 != nil {
					return "", fmt.Errorf("rm %q faild: %w", fullName, err2)
				}
				deletedFileNames = append(deletedFileNames, fi.Name())
			}
		}
		SendProcessLog(logChan, fmt.Sprintf("rm system files at dump/admin/ %s", deletedFileNames))
		SendProcessLog(logChan, fmt.Sprintf("start to mongorestore %s", file.FileName))
	}

	dumpDir := path.Join(fullTmpDir, subDirName, "dump")
	restoreLogfile := path.Join(fullTmpDir, "restore.log")

	restoreCmd := mycmd.New(bin, "--host", conn.Host, "--port", conn.Port,
		"--authenticationDatabase", conn.AuthDb, "--oplogReplay")
	if len(conn.User) > 0 {
		restoreCmd.Append("-u", conn.User)
	}
	if len(conn.Pass) > 0 {
		restoreCmd.Append("-p", mycmd.Password(conn.Pass))
	}

	var zstdcatExec *mycmd.MyExec

	// 4种情况
	// 1. zstd && archive
	// 2. zstd && !archive -- 不存在
	// 3. !zstd && !archive --
	// 4. !zstd && archive
	if zstd && archive {
		// zstdcat file.archive.zstd | mongorestore --archive=-

		zstdcatExec, err = mycmd.NewMyExec(mycmd.New(
			MustFindBinPath("zstd", consts.GetDbTool("mongotools")),
			"-dcf", file.FileName), 7*24*time.Hour, nil, os.DevNull, false)
		if err != nil {
			return "", errors.Wrap(err, "NewMyExec")
		}
		defer zstdcatExec.CancelFunc()
		restoreCmd.Append("--archive=-")
	} else if zstd && !archive {
		// 现在不存在这种场景
		log.Fatalf("zstd && !archive is not supported")
	} else if !zstd && !archive {
		// mongorestore --dir dump
		restoreCmd.Append("--dir", mycmd.Val(dumpDir))
		if gzip {
			restoreCmd.Append("--gzip")
		}
	} else if !zstd && archive {
		// mongorestore --archive=file.archive
		restoreCmd.Append("--archive=" + file.FileName)
		if gzip {
			restoreCmd.Append("--gzip")
		}
	}

	exec2, err := mycmd.NewMyExec(restoreCmd, 7*24*time.Hour, os.DevNull, restoreLogfile, false)
	if err != nil {
		return "", errors.Wrap(err, "NewMyExec")
	}
	defer exec2.CancelFunc()

	// 如果zstdcatExec不为nil，则将zstdcatExec的输出作为mongorestore的输入
	if zstdcatExec != nil {
		out1, err := zstdcatExec.ExecHandle.StdoutPipe()
		if err != nil {
			return "", errors.Wrap(err, "StdoutPipe")
		}
		exec2.SetStdin(out1)
	}

	for _, cmd := range []*mycmd.MyExec{zstdcatExec, exec2} {
		if cmd != nil {
			SendProcessLog(logChan, fmt.Sprintf("DoMongoRestoreFULL cmd: %s", cmd.CmdBuilder.GetCmdLine("", true)))
		}
	}
	SendProcessLog(logChan, fmt.Sprintf("mongorestore logFile:%s", restoreLogfile))

	errorsList := runCmdList([]*mycmd.MyExec{zstdcatExec, exec2})
	if len(errorsList) > 0 {
		for _, err := range errorsList {
			log.Warnf("DoMongoRestoreFULL error: %v", err)
		}
		SendErrorProcessLog(logChan, fmt.Sprintf("DoMongoRestoreFULL return %s", errorsList[0].Error()))
		return "", errors.Wrap(errorsList[0], "DoMongoRestoreFULL")
	}

	return dumpDir, nil
}

// DoReplayOplog oplog dir/oplog.bson
func DoReplayOplog(bin string, conn *mymongo.MongoHost, backupFilePath string, tmpDirPath string, recoverTime uint32,
	gzip bool, archive bool, logChan chan *ProcessLog) error {
	fmt.Printf("DoReplayOplog: %s to %s:%s\n", backupFilePath, conn.Host, conn.Port)
	oplogDir := filepath.Dir(backupFilePath)

	args := []interface{}{"--host", conn.Host, "--port", conn.Port, "--authenticationDatabase", conn.AuthDb}
	if len(conn.User) > 0 {
		args = append(args, "-u", conn.User)
	}
	if len(conn.Pass) > 0 {
		args = append(args, "-p", conn.Pass)
	}
	//mongodump --oplog --gzip 产生的oplog.bson文件，虽然文件名为oplog.bson，但实际是gz压缩文件
	args = append(args, "--oplogReplay")

	//--oplogLimit $recovery_time_epoch:0
	if recoverTime > 0 {
		args = append(args, "--oplogLimit", fmt.Sprintf("%d:999", recoverTime))
	}

	var exec1, exec2 *mycmd.MyExec
	var err error

	if archive { // archive 场景
		panic("not supported")
		/*
			if gzip { // zstdcat file.archive.zstd | mongorestore --archive=-
				zstdBin, err := FindBinPath("zstd", consts.GetDbTool("mongotools"))
				if err != nil {
					return errors.Wrap(err, "zstdBin")
				}
				args = append(args, "--archive=-")
				exec1, err = mycmd.NewMyExec(mycmd.New(zstdBin, "--rm", "-d", backupFilePath), 7*24*time.Hour, nil, os.DevNull)
				if err != nil {
					return errors.Wrap(err, "NewMyExec zstdBin")
				}
				defer exec1.CancelFunc()
			} else { // mongorestore --archive=file.archive
				args = append(args, "--archive="+backupFilePath)
			}
		*/
	} else {
		if filepath.Base(backupFilePath) != "oplog.bson" {
			return fmt.Errorf("bad oplog name:%s", filepath.Base(backupFilePath))
		}
		// 这里的gzip是.gz
		if gzip {
			args = append(args, "--gzip")
		}
		//最后一个参数必须是
		args = append(args, "--dir", oplogDir)
	}

	restoreLogfile := path.Join(tmpDirPath, "restore.log")
	restoreCmd := mycmd.New(bin).Append(args...)
	exec2, err = mycmd.NewMyExec(restoreCmd, 7*24*time.Hour, os.DevNull, restoreLogfile, false)
	if err != nil {
		return errors.Wrap(err, "NewMyExec")
	}
	defer exec2.CancelFunc()

	currDir, _ := os.Getwd()

	defer os.Chdir(currDir)

	cmdList := []*mycmd.MyExec{exec1, exec2}
	for _, cmd := range cmdList {
		if cmd != nil {
			SendProcessLog(logChan, fmt.Sprintf("DoReplayOplog cwd: %s, cmd: %s",
				currDir, cmd.CmdBuilder.GetCmdLine("", true)))
		}
	}

	errorsList := runCmdList(cmdList)
	if len(errorsList) > 0 {
		for _, err := range errorsList {
			log.Warnf("DoReplayOplog error: %v", err)
		}
		return errors.Wrap(errorsList[0], "DoReplayOplog")
	}

	return nil
}

// DoMongoRestoreINCR 导入INCR. zstd 场景下，需要先解压，再导入.
func DoMongoRestoreINCR(bin string, conn *mymongo.MongoHost, full *BackupFileName, incrList []*BackupFileName,
	recoverTime uint32, backupFileDir string, idx int, logChan chan *ProcessLog) error {
	file := incrList[idx]
	// fmt.Printf("DoMongoRestoreINCR: %s [%d] %s to %s:%s\n", file.Type, idx, file.FileName, conn.Host, conn.Port)

	archive := strings.HasSuffix(file.FileName, ".archive") ||
		strings.HasSuffix(file.FileName, ".archive.zstd")

	subDirName := full.FileName
	for _, suffix := range []string{".gz", ".zst", ".tar", ".archive", ".archive.zstd"} {
		subDirName = strings.TrimSuffix(subDirName, suffix)
	}

	incrTmpDir := path.Join("tmp", subDirName, fmt.Sprintf("incr-%d", idx), "oplog")

	if err := os.Chdir(backupFileDir); err != nil {
		return fmt.Errorf("cannot chdir to %s", backupFileDir)
	}
	if stat, err := os.Stat(incrTmpDir); err != nil {
		if err := os.MkdirAll(incrTmpDir, os.FileMode(0755)); err != nil {
			return fmt.Errorf("cannot make dir %s", incrTmpDir)
		} else {
			log.Printf("[%s] mkdir [%s] succ", backupFileDir, incrTmpDir)
		}
	} else if !stat.IsDir() {
		return fmt.Errorf("cannot make dir %s, because a same-name-file exists", incrTmpDir)
	}
	gzip := false
	if archive {
		// 这种方式不存在
		zstd := strings.HasSuffix(file.FileName, ".zstd")
		return DoReplayOplog(bin, conn, file.FileName, incrTmpDir, recoverTime, zstd, archive, logChan)
	} else {
		oplogNewName := "oplog.bson"
		// oplog Relay
		if strings.HasSuffix(file.FileName, ".gz") {
			gzip = true
			DoCommand("cp", file.FileName, path.Join(incrTmpDir, oplogNewName))
		} else if strings.HasSuffix(file.FileName, ".zst") {
			gzip = false
			err := ZstdCmd("-k", "-d", file.FileName, "-o", path.Join(incrTmpDir, oplogNewName))
			if err != nil {
				log.Errorf("zstd decompress %s to %s failed, err: %v",
					file.FileName, path.Join(incrTmpDir, oplogNewName), err)
				SendErrorProcessLog(logChan,
					fmt.Sprintf("zstd decompress %s to %s failed, err: %v",
						file.FileName, path.Join(incrTmpDir, oplogNewName), err))
				return errors.Wrap(err, "zstdcat")
			}
		} else {
			gzip = false
			DoCommand("cp", file.FileName, path.Join(incrTmpDir, oplogNewName))
		}
		//DoCommand("gzip", "-d", path.Join(incrTmpDir,oplog_newname +".gz"))
		// V1版本:
		// 全量备份和增量备份是分别2个线程，全量只管做全量备份，增量备份只需要和它上一个增量备份衔接。
		// 这导致全量备份导入后，下一个增量备份文件里有和全量备份oplog重叠的部分
		// Deprecated: 已经没有v1版本了，所以这个功能已经废弃
		if idx == 0 && file.Version == BackupFileVersionV1 {
			minTs := fmt.Sprintf("%d", full.LastTs.Sec)
			// Output("This is the First oplog after FULL")
			// Output("Delete First oplog.bson where time < %s (full time)", minTs)
			///bsonfilter --bsonFile ./path/to/oplog.bson  --outFile x.bson.new --min-ts 1576990774:1
			oldPath := path.Join(incrTmpDir, oplogNewName)
			newPath := path.Join(incrTmpDir, oplogNewName) + ".new"
			result, err := DoCommandV2("bsonfilter", "--bsonFile", oldPath, "--outFile", newPath, "--min-ts", minTs)
			logFile := path.Join(path.Dir(incrTmpDir), "bsonfilter.log")
			os.Rename(newPath, oldPath)
			SaveRestoreLog(result.Cmdline, logFile, result.Stdout, result.Stderr, false, err)
			//gzip is false after bsonfilter ...
			gzip = false
		}
		return DoReplayOplog(bin, conn, path.Join(incrTmpDir, oplogNewName),
			incrTmpDir, recoverTime, gzip, archive, logChan)
	}

}

func ZstdCmd(args ...any) error {
	zstdBin, err := FindBinPath("zstd", consts.GetDbTool("mongotools"))
	if err != nil {
		return errors.Wrap(err, "GetDbToolsBin")
	}
	exec1, err := mycmd.NewMyExec(
		mycmd.New(zstdBin).Append(args...),
		7*24*time.Hour, nil, os.DevNull, false)
	if err != nil {
		return errors.Wrap(err, "NewMyExec zstdcat")
	}
	defer exec1.CancelFunc()
	return exec1.Run()
}

func receiveLogBg() (*sync.WaitGroup, chan *ProcessLog) {
	logChan := make(chan *ProcessLog, 1)
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			log, ok := <-logChan
			if !ok {
				return
			}
			if log.IsErr {
				ExitFailed("%s", log.Msg)
			} else {
				Output("%s", log.Msg)
			}
		}
	}()
	return wg, logChan
}

// DoRecover 从全量和增量文件中恢复到指定时间点.
func DoRecover(mongorestoreBin string, conn *mymongo.MongoHost, full *BackupFileName, incrList []*BackupFileName,
	recoverTime uint32, backupFileDir string) error {
	wd, _ := os.Getwd()
	log.Printf("WorkDir %s", wd)
	Output("WorkDir is %s", wd)

	// 处理日志 日志会通过logChan发送到主进程
	wg, logChan := receiveLogBg()

	var err error
	// 导入日志时间可能比较长.
	_, err = DoMongoRestoreFULL(mongorestoreBin, conn, full, backupFileDir, logChan)

	if err != nil {
		SendErrorProcessLog(logChan, fmt.Sprintf("DoMongoRestoreFULL return %s", err.Error()))
		goto End
	}

	for idx := range incrList {
		os.Chdir(wd)
		SendProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s start", incrList[idx].FileName))
		if err = DoMongoRestoreINCR(mongorestoreBin, conn, full, incrList,
			recoverTime, backupFileDir, idx, logChan); err != nil {
			SendErrorProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s return %s",
				incrList[idx].FileName, err.Error()))
			goto End
		}
		SendProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s end", incrList[idx].FileName))
	}
End:
	close(logChan)
	wg.Wait()
	if err == nil {
		ExitSuccess("done")
	}
	return err
}

// FindNeedFiles 找到需要的全量和增量文件
func FindNeedFiles(fileObjList []*BackupFileName, recoverTime uint32) (*BackupFileName, []*BackupFileName, error) {
	var fullList []*BackupFileName
	for _, file := range fileObjList {
		if file.Type != BackupTypeFull {
			continue
		}

		if file.LastTs.Sec <= recoverTime {
			fullList = append(fullList, file)
		}
	}

	if len(fullList) == 0 {
		return nil, nil, fmt.Errorf("no-full-file-found")
	}

	sort.Slice(fullList, func(i, j int) bool {
		return fullList[i].LastTs.Sec > fullList[j].LastTs.Sec
	})

	for _, file := range fullList {
		if incrList, err := FindIncrList(file, recoverTime, fileObjList); err == nil {
			return file, incrList, nil
		}
	}

	return nil, nil, fmt.Errorf("no-incr-file-found")
}

// FindIncrList 找到增量文件列表
func FindIncrList(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	if full.Version == BackupFileVersionV0 {
		return findIncrListV0(full, recoverTime, fileObjList)
	} else if full.Version == BackupFileVersionV1 {
		return findIncrListV1(full, recoverTime, fileObjList)
	} else {
		return nil, fmt.Errorf("backup version: %s", full.Version)
	}
}

// findIncrListV0 找到增量文件列表
func findIncrListV0(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	var incrList []*BackupFileName
	for _, file := range fileObjList {
		if file.Type != BackupTypeIncr {
			continue
		}
		if file.Version != BackupFileVersionV0 {
			continue
		}
		if file.V0FullStr == full.V0FullStr {
			incrList = append(incrList, file)
		}
	}

	//刚好回到全备的时间，不需要再导入INCR
	if full.LastTs.Sec == recoverTime {
		return nil, nil
	}

	if len(incrList) == 0 {
		// Ok
		if full.LastTs.Sec == recoverTime {
			return nil, nil
		} else {
			return nil, fmt.Errorf("INCR_NOT_FOUND")
		}
	}

	sort.Slice(incrList, func(i, j int) bool {
		return incrList[i].LastTs.Sec < incrList[j].LastTs.Sec
	})

	//回档目标时间 在 opLog文件中
	checkTsOk := false
	//回档Oplog列表正确
	checkSeqOk := true

	lastIncr := incrList[len(incrList)-1]
	checkTsOk = lastIncr.LastTs.Sec >= recoverTime
	log.Debugf("Check Max LastTs %d is gte recoverTime %d ? %v\n", lastIncr.LastTs.Sec, recoverTime, checkTsOk)

	if lastIncr.V0IncrSeq != uint32(len(incrList)) {
		checkSeqOk = false
		log.Debugf("Debug Bad Seq for INCR %s idx:%d seq:%d\n", lastIncr.FileName, len(incrList), lastIncr.V0IncrSeq)
	}

	for i := 0; i < len(incrList); i++ {
		if incrList[i].V0IncrSeq != uint32(i+1) {
			checkSeqOk = false
			log.Debugf("Debug Bad Seq for INCR %s idx:%d seq:%d\n", incrList[i].FileName, i, incrList[i].V0IncrSeq)
		}
	}

	if !checkSeqOk {
		return nil, fmt.Errorf("bad oplog file list")
	}

	if !checkTsOk {
		return nil, fmt.Errorf("recoverTime gt lastIncr.LastTs")
	}

	// Delete Not Need INCR
	// PREV < recoverTime < NEXT ; drop NEXT + 1
	last := len(incrList) - 1
	for i := 0; i < len(incrList)-1; i++ {
		prev := incrList[i]
		if prev.LastTs.Sec >= recoverTime {
			last = i
			break
		}
	}

	last = last + 1
	return incrList[:last], nil
}

// findIncrListV1 找到增量文件列表
func findIncrListV1(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	var incrList []*BackupFileName

	for _, file := range fileObjList {
		if file.Type != BackupTypeIncr {
			continue
		}
		if file.Version != BackupFileVersionV1 {
			continue
		}

		// INCR LastTs 小于全备一致性时间 抛弃
		if file.LastTs.Sec < full.LastTs.Sec {
			continue
		}

		// INCR FirstTs 大于回档时间 抛弃
		if file.FirstTs.Sec > recoverTime {
			continue
		}

		incrList = append(incrList, file)
		fmt.Printf("append INCR %s %+v %+v\n", file.FileName, file.FirstTs, file.LastTs)

	}

	if len(incrList) == 0 {
		// Ok
		if full.LastTs.Sec == recoverTime {
			return nil, nil
		} else {
			return nil, fmt.Errorf("INCR_NOT_FOUND")
		}
	}

	sort.Slice(incrList, func(i, j int) bool {
		return incrList[i].LastTs.Sec < incrList[j].LastTs.Sec
	})

	checkFirstTsOk := false
	checkLastTsOk := false
	checkSeqOk := true

	firstIncr := incrList[0]
	lastIncr := incrList[len(incrList)-1]

	checkFirstTsOk = firstIncr.FirstTs.Sec <= full.LastTs.Sec && firstIncr.LastTs.Sec >= full.LastTs.Sec
	checkLastTsOk = lastIncr.FirstTs.Sec <= recoverTime && lastIncr.LastTs.Sec >= recoverTime

	log.Debugf("check_first_ts_ok  %d>=%d && %d<=%d  ? %v\n",
		firstIncr.FirstTs.Sec, full.LastTs.Sec, firstIncr.LastTs.Sec, full.LastTs.Sec, checkLastTsOk)
	for i := 0; i < len(incrList)-1; i++ {
		prev := incrList[i]
		next := incrList[i+1]

		if !(prev.LastTs.Sec == next.FirstTs.Sec && prev.LastTs.I == next.FirstTs.I) {
			checkSeqOk = false
		}
	}

	if !checkFirstTsOk {
		return nil, fmt.Errorf("BadFirstTs")

	}
	if !checkLastTsOk {
		return nil, fmt.Errorf("BadLastTs")
	}

	if !checkSeqOk {
		return nil, fmt.Errorf("BadOplogList")
	}

	return incrList, nil

}
