package common

import "testing"

func TestIsTlinux4Text(t *testing.T) {
	cases := []struct {
		name string
		text string
		want bool
	}{
		{name: "tlinux release 4", text: "TencentOS Server release 4.4", want: true},
		{name: "os-release version id", text: "NAME=\"TencentOS\"\nVERSION_ID=\"4\"\n", want: true},
		{name: "tlinux 2.6", text: "Tencent tlinux release 2.6 (Final)", want: false},
		{name: "centos", text: "CentOS Linux release 7.9", want: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := IsTlinux4Text(tc.text); got != tc.want {
				t.Fatalf("IsTlinux4Text()=%t, want %t", got, tc.want)
			}
		})
	}
}
