package domain

import (
	"bk-dnsapi/internal/domain/entity"
	"reflect"
	"testing"
)

func TestDiffInstances(t *testing.T) {
	existing := []entity.TbDnsBase{
		{Uid: 1, Ip: "1.1.1.1", Port: 3306},
		{Uid: 2, Ip: "1.1.1.2", Port: 3306},
		{Uid: 3, Ip: "1.1.1.3", Port: 0},
	}
	cases := []struct {
		name    string
		want    []DomainInstance
		wantAdd []DomainInstance
		wantDel []int64
	}{
		{"unchanged", []DomainInstance{{"1.1.1.1", 3306}, {"1.1.1.2", 3306}, {"1.1.1.3", 0}}, nil, nil},
		{"replace one", []DomainInstance{{"1.1.1.1", 3306}, {"1.1.1.9", 3306}, {"1.1.1.3", 0}},
			[]DomainInstance{{"1.1.1.9", 3306}}, []int64{2}},
		{"shrink", []DomainInstance{{"1.1.1.1", 3306}}, nil, []int64{2, 3}},
		{"grow", []DomainInstance{{"1.1.1.1", 3306}, {"1.1.1.2", 3306}, {"1.1.1.3", 0}, {"1.1.1.4", 3306}},
			[]DomainInstance{{"1.1.1.4", 3306}}, nil},
		{"same ip different port is new", []DomainInstance{{"1.1.1.1", 3307}, {"1.1.1.2", 3306}, {"1.1.1.3", 0}},
			[]DomainInstance{{"1.1.1.1", 3307}}, []int64{1}},
		{"duplicate want", []DomainInstance{{"1.1.1.1", 3306}, {"1.1.1.2", 3306}, {"1.1.1.3", 0}, {"1.1.1.4", 1},
			{"1.1.1.4", 1}}, []DomainInstance{{"1.1.1.4", 1}}, nil},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			add, del := diffInstances(existing, c.want)
			if !reflect.DeepEqual(add, c.wantAdd) {
				t.Fatalf("add got %v, want %v", add, c.wantAdd)
			}
			var uids []int64
			for _, d := range del {
				uids = append(uids, d.Uid)
			}
			if !reflect.DeepEqual(uids, c.wantDel) {
				t.Fatalf("del got %v, want %v", uids, c.wantDel)
			}
		})
	}
}

func TestAttachInstances(t *testing.T) {
	rs := []DomainSearchResult{{DomainName: "a.test.db."}, {DomainName: "b.test.db."}, {DomainName: "c.test.db."}}
	records := []entity.TbDnsBase{
		{DomainName: "a.test.db.", Ip: "1.1.1.2", Port: 3306},
		{DomainName: "b.test.db.", Ip: "2.2.2.2", Port: 0},
		{DomainName: "a.test.db.", Ip: "1.1.1.1", Port: 3307},
		{DomainName: "a.test.db.", Ip: "1.1.1.1", Port: 3306},
	}
	attachInstances(rs, records)
	if want := []string{"1.1.1.1#3306", "1.1.1.1#3307", "1.1.1.2#3306"}; !reflect.DeepEqual(rs[0].Instances, want) {
		t.Fatalf("a got %v, want %v", rs[0].Instances, want)
	}
	if want := []string{"2.2.2.2#0"}; !reflect.DeepEqual(rs[1].Instances, want) {
		t.Fatalf("b got %v, want %v", rs[1].Instances, want)
	}
	if rs[2].Instances == nil || len(rs[2].Instances) != 0 {
		t.Fatalf("c should be empty non-nil slice, got %#v", rs[2].Instances)
	}
}
