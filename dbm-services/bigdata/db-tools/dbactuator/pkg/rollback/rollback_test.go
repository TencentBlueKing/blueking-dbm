package rollback

import (
	"testing"
)

// 将删除/data1/11.txt
func TestRollBackFile(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:    "/data1/11.txt",
		OriginOpera: OP_DEL,
	}
	if err := rf.RollBack(); err != nil {
		t.Error("rollback", err)
	}
}

// 将会把/data1/1.txt mv  /data1/2.txt
func TestMoveFile(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:       "/data1/1.txt",
		OriginFileName: "/data1/2.txt",
		OriginOpera:    OP_MOVE,
	}
	if err := rf.RollBack(); err != nil {
		t.Error("rollback", err)
	}
}

// 将会把/data1/d1 删除
func TestDelDir(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:    "/data1/d1/",
		OriginOpera: OP_DEL,
	}
	if err := rf.RollBack(); err != nil {
		t.Errorf("rollback %s", err.Error())
	}
}

// 将会把/data1/d1 删除
func TestMoveDir(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:       "/data1/d1",
		OriginFileName: "/data1/d",
		OriginOpera:    OP_MOVE,
	}
	if err := rf.RollBack(); err != nil {
		t.Errorf("rollback %s", err.Error())
	}
}

// 将会把/data1/f 软连接到 /data1/c 目录
func TestRmLink(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:    "/data1/f",
		OriginOpera: OP_DEL,
	}
	if err := rf.RollBack(); err != nil {
		t.Errorf("rollback %s", err.Error())
	}
}

// 将会把/data1/f 软连接到 /data1/c 目录
func TestMoveLink(t *testing.T) {
	t.Logf("start testing TestRollBackFile...")
	rf := RollBackFile{
		FileName:       "/data1/f",
		OriginFileName: "/data1/c",
		OriginOpera:    OP_MOVE,
	}
	if err := rf.RollBack(); err != nil {
		t.Errorf("rollback %s", err.Error())
	}
}

func TestIsSafeDir(t *testing.T) {
	t.Logf("start testing ...")
	t.Log(IsSafe("/usr/local"))
}
