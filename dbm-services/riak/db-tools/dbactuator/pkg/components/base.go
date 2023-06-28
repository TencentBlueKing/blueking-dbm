package components

// BaseInputParam TODO
type BaseInputParam struct {
	GeneralParam *GeneralParam `json:"general"`
	ExtendParam  interface{}   `json:"extend"`
}

// GeneralParam TODO
type GeneralParam struct {
	RuntimeAccountParam RuntimeAccountParam `json:"runtime_account"`
	RuntimeExtend       RuntimeExtend       `json:"runtime_extend"`
}

// RuntimeExtend TODO
type RuntimeExtend struct {
}

// RuntimeAccountParam TODO
type RuntimeAccountParam struct {
}
