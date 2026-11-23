package entity

import "testing"

func TestDomainInfoColumnsContainRemark(t *testing.T) {
	found := false
	for _, c := range new(TbDnsDomainInfo).Columns() {
		if c == "remark" {
			found = true
		}
	}
	if !found {
		t.Fatal("tb_dns_domain_info columns should contain remark")
	}
}
