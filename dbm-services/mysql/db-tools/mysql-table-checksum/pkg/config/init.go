package config

// CheckMode 校验模式
type CheckMode string

const (
	// GeneralMode 常规校验
	GeneralMode CheckMode = "general"
	// DemandMode 单据校验
	DemandMode = "demand"
)

// String 用于打印
func (c CheckMode) String() string {
	return string(c)
}

func init() {

}
