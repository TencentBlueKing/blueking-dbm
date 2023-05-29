package checker

import (
	"fmt"
	"slices"
)

type switchStrategy struct {
	Name  string
	Value bool
	// Enable      bool
	HasOpposite bool
}

type kvStrategy struct {
	Name   string
	Value  func(*Checker) interface{}
	Enable bool
}

func (r *Checker) applyForceSwitchStrategy(strategies []switchStrategy) {
	for _, st := range strategies {
		if idx := slices.Index(r.Config.PtChecksum.Switches, st.Name); idx > -1 {
			r.Config.PtChecksum.Switches = slices.Delete(r.Config.PtChecksum.Switches, idx, idx+1)
		}
		if idx := slices.Index(r.Config.PtChecksum.Switches, fmt.Sprintf("no-%s", st.Name)); idx > -1 {
			r.Config.PtChecksum.Switches = slices.Delete(r.Config.PtChecksum.Switches, idx, idx+1)
		}
		if st.Value {
			r.Config.PtChecksum.Switches = append(r.Config.PtChecksum.Switches, st.Name)
		} else {
			if st.HasOpposite {
				r.Config.PtChecksum.Switches = append(r.Config.PtChecksum.Switches, fmt.Sprintf("no-%s", st.Name))
			}
		}
	}
}

func (r *Checker) applyDefaultSwitchStrategy(strategies []switchStrategy) {
	for _, st := range strategies {
		if slices.Index(r.Config.PtChecksum.Switches, st.Name) == -1 &&
			slices.Index(r.Config.PtChecksum.Switches, fmt.Sprintf("no-%s", st.Name)) == -1 {
			if st.Value {
				r.Config.PtChecksum.Switches = append(r.Config.PtChecksum.Switches, st.Name)
			} else {
				if st.HasOpposite {
					r.Config.PtChecksum.Switches = append(r.Config.PtChecksum.Switches, fmt.Sprintf("no-%s", st.Name))
				}
			}
		}
	}
}

func (r *Checker) applyForceKVStrategy(strategies []kvStrategy) {
	for _, st := range strategies {
		idx := slices.IndexFunc(
			r.Config.PtChecksum.Args, func(kvArg map[string]interface{}) bool {
				return kvArg["name"] == st.Name
			},
		)
		if idx == -1 {
			if st.Enable {
				r.Config.PtChecksum.Args = append(
					r.Config.PtChecksum.Args, map[string]interface{}{
						"name":  st.Name,
						"value": st.Value(r),
					},
				)
			}
		} else {
			if st.Enable {
				r.Config.PtChecksum.Args[idx]["value"] = st.Value(r)
			} else {
				r.Config.PtChecksum.Args = slices.Delete(r.Config.PtChecksum.Args, idx, idx+1)
			}
		}
	}
}

func (r *Checker) applyDefaultKVStrategy(strategies []kvStrategy) {
	for _, st := range strategies {
		idx := slices.IndexFunc(
			r.Config.PtChecksum.Args, func(kvArg map[string]interface{}) bool {
				return kvArg["name"] == st.Name
			},
		)
		if idx == -1 {
			if st.Enable {
				r.Config.PtChecksum.Args = append(
					r.Config.PtChecksum.Args, map[string]interface{}{
						"name":  st.Name,
						"value": st.Value(r),
					},
				)
			}
		}
	}
}
