package reverseapi

import (
	"dbm-services/common/reverseapi/internal/core"
	"reflect"
	"slices"
	"testing"
)

func TestNewCore(t *testing.T) {
	cases := []struct {
		Name      string
		BkCloudId int64
		MixAddrs  []string
		IsOK      func(core *core.Core, err error) bool
	}{
		{
			"with-bk-cloud-id",
			0,
			[]string{"99:1.1.1.1:80", "99:2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err != nil {
					return false
				}
				if core.BkCloudId() != 99 {
					return false
				}
				a := []string{"1.1.1.1:80", "2.2.2.2:80"}
				b := core.NginxAddrs()
				slices.Sort(a)
				slices.Sort(b)
				return reflect.DeepEqual(a, b)
			},
		},
		{
			"without-bk-cloud-id",
			0,
			[]string{"1.1.1.1:80", "2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err != nil {
					return false
				}
				if core.BkCloudId() != 0 {
					return false
				}
				a := []string{"1.1.1.1:80", "2.2.2.2:80"}
				b := core.NginxAddrs()
				slices.Sort(a)
				slices.Sort(b)
				return reflect.DeepEqual(a, b)
			},
		},
		{
			"different-bk-cloud-id",
			0,
			[]string{"99:1.1.1.1:80", "98:2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err == nil {
					return false
				}
				if core != nil {
					return false
				}
				return true
			},
		},
		{
			"partial-bk-cloud-id",
			0,
			[]string{"99:1.1.1.1:80", "2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err != nil {
					return false
				}
				if core.BkCloudId() != 99 {
					return false
				}
				a := []string{"1.1.1.1:80", "2.2.2.2:80"}
				b := core.NginxAddrs()
				slices.Sort(a)
				slices.Sort(b)
				return reflect.DeepEqual(a, b)
			},
		},
		{
			"missing-port",
			0,
			[]string{"99:1.1.1.1", "98:2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err == nil {
					return false
				}
				if core != nil {
					return false
				}
				return true
			},
		},
		{
			"bad-line-1",
			0,
			[]string{"99:1.1.1.1:", "98:2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err == nil {
					return false
				}
				if core != nil {
					return false
				}
				return true
			},
		},
		{
			"bad-line-2",
			0,
			[]string{"a:1.1.1.1:80", "98:2.2.2.2:80"},
			func(core *core.Core, err error) bool {
				if err == nil {
					return false
				}
				if core != nil {
					return false
				}
				return true
			},
		},
	}

	for _, c := range cases {
		t.Run(c.Name, func(t *testing.T) {
			rc, err := newCore(c.BkCloudId, c.MixAddrs...)
			if !c.IsOK(rc, err) {
				t.Fatalf("%s not pass", c.Name)
			}
		})
	}
}
