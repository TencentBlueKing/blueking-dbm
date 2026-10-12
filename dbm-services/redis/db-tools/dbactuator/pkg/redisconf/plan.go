package redisconf

import (
	"fmt"
	"os"
	"os/user"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// Plan 渲染并校验通过、但还没落盘的一次配置重建
type Plan struct {
	Port     int
	ConfFile string
	// OldConf 展开 include 之后的旧配置, 用于差异比对; RawOldConf 是磁盘原文, 用于备份
	OldConf    string
	RawOldConf string
	Includes   []string
	NewConf    string
	// NodesMove 旧配置用 cluster-config-file 指向了非默认节点文件时, 停机后要把它带到 nodes.conf
	NodesMove *NodesFileMove
}

// HasInclude 原文是否靠 include 引入了别的文件
func (p *Plan) HasInclude() bool {
	return len(p.Includes) > 0
}

func (p *Plan) backupData() string {
	if p.RawOldConf != "" {
		return p.RawOldConf
	}
	return p.OldConf
}

// Changes 落盘要做的动作, 按执行顺序排列. 每次调用返回一组新的、尚未执行的动作
func (p *Plan) Changes() []Change {
	changes := []Change{&confWrite{plan: p}}
	seen := make(map[string]bool, len(p.Includes))
	for _, file := range p.Includes {
		if seen[file] {
			continue
		}
		seen[file] = true
		changes = append(changes, &includeRetire{instDir: filepath.Dir(p.ConfFile), file: file})
	}
	if p.NodesMove != nil {
		move := *p.NodesMove
		changes = append(changes, &move)
	}
	return changes
}

// NeedsStopped 是否有动作只能在进程停着时做
func (p *Plan) NeedsStopped() bool {
	for _, c := range p.Changes() {
		if c.NeedsStopped() {
			return true
		}
	}
	return false
}

// Change 一个落盘动作. Apply 失败时自己不留半截; Undo 撤销一次成功的 Apply.
//
// 停机后的副作用(写配置、退役 include、迁移节点文件、挪走数据)都实现成 Change, 由调用方
// 用 ApplyChanges 一起执行: 中途失败自动逆序撤销, 起不来时调用方再整体 Undo.
type Change interface {
	String() string
	// NeedsStopped 只能在进程停着时做
	NeedsStopped() bool
	Apply(log *logger.Logger) error
	Undo(log *logger.Logger) error
}

// finalizer 进程确认起好之后才做的收尾, 如删掉挪走的旧数据、迁移前的节点文件
type finalizer interface {
	Finalize(log *logger.Logger)
}

// Applied 一组已经成功执行的 Change
type Applied struct {
	done []Change
}

// ApplyChanges 按顺序执行. 任一步失败时把已完成的逆序撤销, 磁盘回到执行前的样子
func ApplyChanges(changes []Change, log *logger.Logger) (*Applied, error) {
	applied := &Applied{}
	for _, c := range changes {
		if err := c.Apply(log); err != nil {
			err = fmt.Errorf("%s failed: %w", c, err)
			if undoErr := applied.Undo(log); undoErr != nil {
				return nil, fmt.Errorf("%v; rollback failed,err:%v", err, undoErr)
			}
			return nil, err
		}
		applied.done = append(applied.done, c)
	}
	return applied, nil
}

// Empty 是否什么都没做
func (a *Applied) Empty() bool {
	return a == nil || len(a.done) == 0
}

// Undo 逆序撤销. 某一步撤销失败时停下, 没撤销的留在 Applied 里, 可以再试
func (a *Applied) Undo(log *logger.Logger) error {
	if a == nil {
		return nil
	}
	for len(a.done) > 0 {
		last := a.done[len(a.done)-1]
		if err := last.Undo(log); err != nil {
			return fmt.Errorf("undo %s failed,err:%v", last, err)
		}
		a.done = a.done[:len(a.done)-1]
	}
	return nil
}

// Finalize 进程起好之后的收尾. 收尾失败不影响结果, 各动作自己打日志
func (a *Applied) Finalize(log *logger.Logger) {
	if a == nil {
		return
	}
	for _, c := range a.done {
		if f, ok := c.(finalizer); ok {
			f.Finalize(log)
		}
	}
}

// ConfBackup 本次写配置前留下的备份文件, 没写过配置时为空
func (a *Applied) ConfBackup() string {
	if a == nil {
		return ""
	}
	for _, c := range a.done {
		if w, ok := c.(*confWrite); ok {
			return w.backupFile
		}
	}
	return ""
}

// confWrite 写入渲染结果, 先备份磁盘原文
type confWrite struct {
	plan       *Plan
	backupFile string
}

func (w *confWrite) String() string { return "write conf " + w.plan.ConfFile }

// NeedsStopped 进程只在启动时读配置, 运行中改文件不影响它
func (w *confWrite) NeedsStopped() bool { return false }

func (w *confWrite) Apply(log *logger.Logger) error {
	p := w.plan
	log.Info("port(%d) conf regenerate diff:\n%s", p.Port, DiffDirectives(p.OldConf, p.NewConf))
	backupFile, err := BackupConfFile(p.ConfFile, []byte(p.backupData()))
	if err != nil {
		return err
	}
	if err = WriteConfFile(p.ConfFile, []byte(p.NewConf)); err != nil {
		return err
	}
	w.backupFile = backupFile
	log.Info("port(%d) conf regenerated,conf:%s,backup:%s", p.Port, p.ConfFile, backupFile)
	return nil
}

func (w *confWrite) Undo(log *logger.Logger) error {
	if err := WriteConfFile(w.plan.ConfFile, []byte(w.plan.backupData())); err != nil {
		return fmt.Errorf("restore conf(%s) from %s failed,err:%v", w.plan.ConfFile, w.backupFile, err)
	}
	log.Info("port(%d) conf restored from %s", w.plan.Port, w.backupFile)
	return nil
}

// renameIncludedConfFile 退役/挪回 include 文件用的改名, 单测里替换它来模拟改名失败
var renameIncludedConfFile = os.Rename

// includeRetire 把实例目录内被 include 过的文件改名为 <name>.<时间戳>.bak.
//
// 新文件不再带 include, 不挪走的话 GetRedisLoccalConfFile 之类优先认 instance.conf 的工具
// 会继续读写一个已经没有进程加载的文件. 实例目录外的文件(可能被多个实例共用)只参与展开, 不动.
type includeRetire struct {
	instDir string
	file    string
	moved   string
}

func (r *includeRetire) String() string { return "retire include " + r.file }

// NeedsStopped 进程只在启动时读 include, 运行中挪走不影响它
func (r *includeRetire) NeedsStopped() bool { return false }

func (r *includeRetire) Apply(log *logger.Logger) error {
	instDir := resolvePathSymlinks(r.instDir)
	rel, relErr := filepath.Rel(instDir, resolvePathSymlinks(r.file))
	if relErr != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		log.Info("include %s is outside inst dir %s,left in place", r.file, instDir)
		return nil
	}
	moved := r.file + "." + time.Now().Format(consts.FilenameTimeLayout) + ".bak"
	if err := renameIncludedConfFile(r.file, moved); err != nil {
		return fmt.Errorf("retire include %s to %s failed,err:%v", r.file, moved, err)
	}
	r.moved = moved
	log.Info("include %s retired to %s,regenerated conf no longer loads it", r.file, moved)
	return nil
}

func (r *includeRetire) Undo(log *logger.Logger) error {
	if r.moved == "" {
		return nil
	}
	if err := renameIncludedConfFile(r.moved, r.file); err != nil {
		return fmt.Errorf("restore include %s from %s failed,err:%v", r.file, r.moved, err)
	}
	log.Info("include %s restored from %s", r.file, r.moved)
	r.moved = ""
	return nil
}

// WriteConfFile 先写临时文件再 rename, 避免截断后写一半.
// 权限沿用原文件, 避免升级把线上已有的 mode 改掉.
func WriteConfFile(confFile string, confData []byte) error {
	perm := os.FileMode(0644)
	if info, err := os.Stat(confFile); err == nil {
		perm = info.Mode().Perm()
	}
	tmpFile := confFile + ".tmp"
	if err := os.WriteFile(tmpFile, confData, perm); err != nil {
		return fmt.Errorf("write redis conf tmp(%s) failed,err:%v", tmpFile, err)
	}
	if err := os.Chmod(tmpFile, perm); err != nil {
		_ = os.Remove(tmpFile)
		return fmt.Errorf("chmod redis conf tmp(%s) to %v failed,err:%v", tmpFile, perm, err)
	}
	if err := os.Rename(tmpFile, confFile); err != nil {
		_ = os.Remove(tmpFile)
		return fmt.Errorf("rename redis conf tmp(%s) to %s failed,err:%v", tmpFile, confFile, err)
	}
	return ChownMysql(confFile)
}

// BackupConfFile 备份旧配置文件, 返回备份路径
func BackupConfFile(confFile string, confBytes []byte) (string, error) {
	fileInfo, err := os.Stat(confFile)
	if err != nil {
		return "", fmt.Errorf("stat conf(%s) failed,err:%v", confFile, err)
	}
	backupFile := confFile + "." + time.Now().Format(consts.FilenameTimeLayout) + ".bak"
	if err = os.WriteFile(backupFile, confBytes, fileInfo.Mode().Perm()); err != nil {
		return "", fmt.Errorf("backup conf(%s) to %s failed,err:%v", confFile, backupFile, err)
	}
	if err = ChownMysql(backupFile); err != nil {
		return "", err
	}
	return backupFile, nil
}

// ChownMysql 把文件属主改成 mysql.
// 本机没有 mysql 用户, 或当前不是 root(改不了属主, 单测常见), 跳过.
func ChownMysql(path string) error {
	if _, err := user.Lookup(consts.MysqlAaccount); err != nil {
		return nil
	}
	if os.Geteuid() != 0 {
		return nil
	}
	if err := util.LocalDirChownMysql(path); err != nil {
		return fmt.Errorf("chown %s to %s failed,err:%v", path, consts.MysqlAaccount, err)
	}
	return nil
}
