package domain

import (
	"bk-dnsapi/internal/domain/entity"
	"strings"
	"testing"
	"time"
)

func opTypes(logs []*entity.TbDnsOpLog) []string {
	var rs []string
	for _, l := range logs {
		rs = append(rs, l.OpType+":"+l.DomainName)
	}
	return rs
}

func TestBuildInsertLogs(t *testing.T) {
	list := []*entity.TbDnsBase{
		{DomainName: "a.test.db.", Ip: "1.1.1.1", Port: 3306, Manager: "zs, ls,zs", App: "app"},
		{DomainName: "a.test.db.", Ip: "1.1.1.2", Port: 3306, Manager: "zs"},
		{DomainName: "b.test.db.", Ip: "2.2.2.2", Port: 0, Manager: "ww"},
	}
	op := OpContext{ClientIp: "192.168.0.1"}
	logs := buildInsertLogs(list, map[string]bool{"a.test.db.": true}, op, time.Now())
	if got := strings.Join(opTypes(logs), ","); got != "CREATE_DOMAIN:a.test.db.,UPDATE_IP:b.test.db." {
		t.Fatalf("got %s", got)
	}
	// 操作人没传时取管理人（规范化后），客户端IP透传
	if logs[0].Operator != "zs,ls" || logs[0].ClientIp != "192.168.0.1" {
		t.Fatalf("unexpected operator/clientIp: %+v", logs[0])
	}
	if !strings.Contains(logs[0].Content, "[1.1.1.1#3306,1.1.1.2#3306]") {
		t.Fatalf("content missing instances: %s", logs[0].Content)
	}
	// 传了操作人以操作人为准
	logs = buildInsertLogs(list, map[string]bool{}, OpContext{Operator: "admin"}, time.Now())
	if logs[0].Operator != "admin" {
		t.Fatalf("operator should be admin, got %s", logs[0].Operator)
	}
}

func TestBuildDeleteLogs(t *testing.T) {
	recs := []entity.TbDnsBase{
		{DomainName: "a.test.db.", Ip: "1.1.1.1", Port: 3306},
		{DomainName: "a.test.db.", Ip: "1.1.1.2", Port: 3306},
		{DomainName: "b.test.db.", Ip: "2.2.2.2", Port: 0},
	}
	// a 还剩 1 条记录 -> UPDATE_IP；b 不在剩余里 -> DELETE_DOMAIN
	logs := buildDeleteLogs(recs, map[string]int64{"a.test.db.": 1}, OpContext{Operator: "zs"}, time.Now())
	if got := strings.Join(opTypes(logs), ","); got != "UPDATE_IP:a.test.db.,DELETE_DOMAIN:b.test.db." {
		t.Fatalf("got %s", got)
	}
	if logs[0].Operator != "zs" {
		t.Fatalf("operator got %s", logs[0].Operator)
	}
	// 没传操作人记 system
	logs = buildDeleteLogs(recs, nil, OpContext{}, time.Now())
	if logs[0].Operator != "system" || logs[0].OpType != "DELETE_DOMAIN" {
		t.Fatalf("unexpected: %+v", logs[0])
	}
}

func TestBuildManagerLog(t *testing.T) {
	now := time.Now()
	if buildManagerLog("a.", "zs", "", OpContext{}, now) != nil {
		t.Fatal("empty new manager should not log")
	}
	if buildManagerLog("a.", "zs", "zs", OpContext{}, now) != nil {
		t.Fatal("unchanged manager should not log")
	}
	l := buildManagerLog("a.", "zs", "zs,ls", OpContext{Operator: "admin"}, now)
	if l == nil || l.OpType != entity.OpTypeUpdateManager || l.Content != "manager: zs -> zs,ls" {
		t.Fatalf("unexpected: %+v", l)
	}
}

func TestBuildSyncLogs(t *testing.T) {
	now := time.Now()
	op := OpContext{Operator: "admin"}
	// 实例和管理人都变化 -> 两条
	logs := buildSyncLogs("a.", []string{"1.1.1.9#3306"}, []string{"1.1.1.2#3306"}, "zs", "ls", op, now)
	if got := strings.Join(opTypes(logs), ","); got != "UPDATE_IP:a.,UPDATE_MANAGER:a." {
		t.Fatalf("got %s", got)
	}
	if logs[0].Content != "add instances: [1.1.1.9#3306]; remove instances: [1.1.1.2#3306]" {
		t.Fatalf("content: %s", logs[0].Content)
	}
	// 只改管理人
	logs = buildSyncLogs("a.", nil, nil, "zs", "ls", op, now)
	if len(logs) != 1 || logs[0].OpType != entity.OpTypeUpdateManager {
		t.Fatalf("unexpected: %v", opTypes(logs))
	}
	// 什么都没变
	if logs = buildSyncLogs("a.", nil, nil, "zs", "zs", op, now); len(logs) != 0 {
		t.Fatalf("expect no log, got %v", opTypes(logs))
	}
}

func TestBuildRemarkLog(t *testing.T) {
	now := time.Now()
	if buildRemarkLog("a.", "x", "x", OpContext{}, now) != nil {
		t.Fatal("unchanged remark should not log")
	}
	l := buildRemarkLog("a.", "old", "new", OpContext{Operator: "admin"}, now)
	if l == nil || l.OpType != entity.OpTypeUpdateRemark || l.Content != "remark: old -> new" || l.Operator != "admin" {
		t.Fatalf("unexpected: %+v", l)
	}
	// 清空备注也要记录
	if l = buildRemarkLog("a.", "old", "", OpContext{}, now); l == nil || l.Content != "remark: old -> " {
		t.Fatalf("unexpected: %+v", l)
	}
}
