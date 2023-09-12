// Package rollback TODO
package rollback

import (
	"fmt"
	"os"
	"path"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"
	"dbm-services/riak/db-tools/dbactuator/pkg/util/osutil"
)

const (
	// OP_DEL TODO
	OP_DEL = "DEL"
	// OP_MOVE TODO
	OP_MOVE = "MOVE"
)

// RollBackObjects TODO
type RollBackObjects struct {
	RollBackProcessList []RollBackProcess `json:"rollback_processlist"`
	RollBackFiles       []RollBackFile    `json:"rollback_files"`
}

// 这些目录无论如何都不能直接删除
// 我们原子任务主要操作相关目录
var safeDirs = map[string]struct{}{"/": {}, "/etc": {}, "/usr": {}, "/usr/local": {}, "/data": {}, "/data1": {}}

// RollBackFile 文件包括 常规文件 目录 软连接等
// 回滚操作不记录删除文件的操作
// 因为删除文件没有源文件无法恢复
type RollBackFile struct {
	// 文件必须是绝对路径
	FileName       string `json:"file_name"`        // DEL,MOVE 后的文件名称
	OriginFileName string `json:"origin_file_name"` // DEL,MOVE 前的文件名称
	OriginOpera    string `json:"origin_opera"`     // 原始操作 DEL:新增文件 MOVE:文件重命名
}

// RollBackProcess 暂定回滚由任务拉起的新进程
// 已经kill进程，暂不恢复
type RollBackProcess struct {
	StartOsUser string `json:"start_os_user"` // os启动用户
	ProcessId   int    `json:"process_id"`
}

// AddDelFile TODO
func (r *RollBackObjects) AddDelFile(fileName string) {
	r.RollBackFiles = append(
		r.RollBackFiles, RollBackFile{
			FileName:    fileName,
			OriginOpera: OP_DEL,
		},
	)
}

// AddMoveFile TODO
func (r *RollBackObjects) AddMoveFile(originFileName, fileName string) {
	r.RollBackFiles = append(
		r.RollBackFiles, RollBackFile{
			FileName:       fileName,
			OriginFileName: originFileName,
			OriginOpera:    OP_DEL,
		},
	)
}

// AddKillProcess TODO
func (r *RollBackObjects) AddKillProcess(pid int) {
	r.RollBackProcessList = append(
		r.RollBackProcessList, RollBackProcess{
			ProcessId: pid,
		},
	)
}

// RollBack TODO
func (r *RollBackObjects) RollBack() (err error) {
	if r.RollBackProcessList != nil {
		err = r.RollBack_Processlists()
	}
	if r.RollBackFiles != nil {
		err = r.RollBack_Files()
	}
	return err
}

// RollBack_Processlists TODO
func (r *RollBackObjects) RollBack_Processlists() (err error) {
	if len(r.RollBackProcessList) <= 0 {
		return nil
	}
	for _, rp := range r.RollBackProcessList {
		if err = rp.Rollback(); err != nil {
			return
		}
	}
	return err
}

// RollBack_Files TODO
func (r *RollBackObjects) RollBack_Files() (err error) {
	if len(r.RollBackFiles) <= 0 {
		return nil
	}
	for _, rfile := range r.RollBackFiles {
		if err = rfile.RollBack(); err != nil {
			return
		}
	}
	return err
}

// RollBack TODO
// os.Stat 和 os.Lstat 两个函数用来获取文件类型,但是os.Stat具有穿透连接能力,如果你去获取一个软链的 FileInfo,他会返回软链到的文件的信息,你既然想知道他的具体类型,就要使用 os.Lstat
func (r *RollBackFile) RollBack() (err error) {
	f, err := os.Lstat(r.FileName)
	if err != nil {
		// 如果是删除文件的话，文件不存在,那就忽略错误
		if os.IsNotExist(err) && r.OriginOpera == OP_DEL {
			return nil
		}
		return err
	}

	switch mode := f.Mode().Type(); {
	case mode.IsDir():
		return r.rollbackDir()
	case mode.IsRegular():
		return r.rollbackRegularFile()
	case mode&os.ModeSymlink != 0:
		return r.rollbackLink()
	default:
		logger.Error("Not Define mode.String(): %v\n", mode.String())
	}
	return nil
}

func (r *RollBackFile) rollbackRegularFile() (err error) {
	switch r.OriginOpera {
	case OP_DEL:
		return SafeRm(r.FileName)
	case OP_MOVE:
		return SafeMove(r.FileName, r.OriginFileName)
	}
	return fmt.Errorf("no define Operate %s", r.OriginOpera)
}

func (r *RollBackFile) rollbackDir() (err error) {
	switch r.OriginOpera {
	case OP_DEL:
		return SafeRmDir(r.FileName)
	case OP_MOVE:
		return SafeMove(r.FileName, r.OriginFileName)
	}
	return fmt.Errorf("no define Operate %s", r.OriginOpera)
}

func (r *RollBackFile) rollbackLink() (err error) {
	switch r.OriginOpera {
	case OP_DEL:
		return SafeUnlink(r.FileName)
	case OP_MOVE:
		return SafeRelink(r.FileName, r.OriginFileName)
	}
	return fmt.Errorf("no define Operate %s", r.OriginOpera)
}

// SafeMove TODO
func SafeMove(file, destfile string) (err error) {
	_, err = osutil.ExecShellCommand(false, fmt.Sprintf("mv %s %s", file, destfile))
	return
}

// SafeRelink TODO
func SafeRelink(linkfile, destfile string) (err error) {
	_, err = osutil.ExecShellCommand(false, fmt.Sprintf(" unlink %s && ln -s %s %s", linkfile, destfile, linkfile))
	return
}

// SafeUnlink TODO
func SafeUnlink(file string) (err error) {
	if IsSafe(file) {
		_, err = osutil.ExecShellCommand(false, fmt.Sprintf("unlink %s", file))
		return
	}
	return fmt.Errorf("%s 不允许删除", file)
}

// SafeRm TODO
func SafeRm(file string) (err error) {
	if IsSafe(file) {
		_, err = osutil.ExecShellCommand(false, fmt.Sprintf("rm %s", file))
		return
	}
	return fmt.Errorf("%s不允许删除", file)
}

// SafeRmDir TODO
func SafeRmDir(file string) (err error) {
	if IsSafe(file) {
		_, err = osutil.ExecShellCommand(false, fmt.Sprintf("rm  -rf %s", file))
		return
	}
	return fmt.Errorf("%s 不允许删除", file)
}

// IsSafe TODO
func IsSafe(file string) bool {
	// 如果存在 file  是不能直接删除的目录
	if _, ok := safeDirs[file]; ok {
		return !ok
	}
	// 如果存在 file  是不能直接删除的目录，判断下base dir
	if _, ok := safeDirs[path.Base(file)]; ok {
		return !ok
	}
	return !util.StrIsEmpty(file)
}

// Rollback TODO
func (r *RollBackProcess) Rollback() (err error) {
	if r.ProcessId <= 0 {
		return nil
	}
	p, err := os.FindProcess(r.ProcessId)
	if err != nil {
		// 找不到这个进程，可能吗没有 不需要回滚
		return nil
	}
	return p.Kill()
}
