package handler

import (
	"bk-dnsapi/internal/domain/repo/domain"
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func TestParseKeepInstances(t *testing.T) {
	var msg string
	got := parseKeepInstances([]string{" 1.1.1.1#3306 ", "1.1.1.2", "1.1.1.1#3306", ""}, &msg)
	want := []domain.DomainInstance{{Ip: "1.1.1.1", Port: 3306}, {Ip: "1.1.1.2", Port: 0}}
	if msg != "" || !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v msg[%s], want %v", got, msg, want)
	}

	msg = ""
	parseKeepInstances([]string{"bad#x"}, &msg)
	if msg == "" {
		t.Fatalf("expect error for invalid instance")
	}
}

func TestCheckRemark(t *testing.T) {
	if checkRemark(nil) != "" {
		t.Fatal("nil remark should pass")
	}
	empty := ""
	if checkRemark(&empty) != "" {
		t.Fatal("empty remark should pass")
	}
	ok := strings.Repeat("备", maxRemarkLen)
	if checkRemark(&ok) != "" {
		t.Fatal("128 chars should pass")
	}
	long := strings.Repeat("备", maxRemarkLen+1)
	if checkRemark(&long) == "" {
		t.Fatal("129 chars should fail")
	}
}

func TestRemarkPointerUnmarshal(t *testing.T) {
	var p DnsMgrPostReqParam
	if err := json.Unmarshal([]byte(`{"domain_name":"a.b.c."}`), &p); err != nil || p.Remark != nil {
		t.Fatalf("missing remark should be nil, got %v err %v", p.Remark, err)
	}
	if err := json.Unmarshal([]byte(`{"remark":""}`), &p); err != nil || p.Remark == nil || *p.Remark != "" {
		t.Fatalf("empty remark should be non-nil empty, got %v err %v", p.Remark, err)
	}
}
